import os
from decimal import Decimal, InvalidOperation

import mysql.connector
import stripe
from flask import Flask, jsonify, request
from mysql.connector import Error

app = Flask(__name__)


def database_config():
    return {
        "host": os.getenv("MYSQLHOST", os.getenv("DB_HOST", "localhost")),
        "port": int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", "3306"))),
        "user": os.getenv("MYSQLUSER", os.getenv("DB_USER", "root")),
        "password": os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", "")),
        "database": os.getenv("MYSQLDATABASE", os.getenv("DB_NAME", "Higher_education")),
    }


def connect():
    return mysql.connector.connect(**database_config())


def related_records(cursor, table_name, key_column, ids):
    # Table/column names below are fixed in this application; values remain parameterized.
    ids = list(dict.fromkeys(value for value in ids if value is not None))
    if not ids:
        return []
    placeholders = ", ".join(["%s"] * len(ids))
    cursor.execute(
        f"SELECT * FROM `{table_name}` WHERE `{key_column}` IN ({placeholders})",
        tuple(ids),
    )
    return cursor.fetchall()


def load_student_account(cursor, student_id):
    cursor.execute("SELECT * FROM Student WHERE STU_ID = %s", (student_id,))
    student = cursor.fetchone()
    if not student:
        return None

    cursor.execute("SELECT * FROM CHARGES WHERE STU_ID = %s", (student_id,))
    charges = cursor.fetchall()
    cursor.execute("SELECT * FROM Payments WHERE STU_ID = %s ORDER BY PAYMENT_ID DESC", (student_id,))
    payments = cursor.fetchall()

    related = {
        "CHARGES": charges,
        "Payments": payments,
        "Housing": related_records(cursor, "Housing", "HOUSE_ID", [r.get("HOUSE_ID") for r in charges]),
        "Meal_Plan": related_records(cursor, "Meal_Plan", "MEALPLAN_ID", [r.get("MEALPLAN_ID") for r in charges]),
        "TUTION_AND_FEES": related_records(cursor, "TUTION_AND_FEES", "TUTION_ID", [r.get("TUTION_ID") for r in charges]),
        "Financial_Aid": related_records(cursor, "Financial_Aid", "AID_ID", [r.get("AID_ID") for r in charges]),
    }

    # Decisions are student-specific. Do not change the shared Financial_Aid row,
    # because the same award record can be linked to more than one student.
    cursor.execute(
        "SELECT AID_ID, DECISION FROM Financial_Aid_Decisions WHERE STU_ID = %s",
        (student_id,),
    )
    decisions = {row["AID_ID"]: row["DECISION"] for row in cursor.fetchall()}
    for aid in related["Financial_Aid"]:
        if aid.get("AID_ID") in decisions:
            aid["AID_STATUS"] = decisions[aid["AID_ID"]]

    return {"student": student, "records": related}


def calculate_balance(account):
    records = account["records"]
    charges = records.get("CHARGES", [])
    housing = records.get("Housing", [])
    meals = records.get("Meal_Plan", [])
    payments = records.get("Payments", [])
    aid = records.get("Financial_Aid", [])

    total_charges = sum(Decimal(str(row.get("CHARGE_AMOUNT") or 0)) for row in charges)
    total_charges += sum(Decimal(str(row.get("HOUSING_RATE") or 0)) for row in housing)
    total_charges += sum(Decimal(str(row.get("PLAN_COST") or 0)) for row in meals)

    completed_payments = sum(
        Decimal(str(row.get("PAYMENT_AMOUNT") or 0))
        for row in payments
        if str(row.get("PAYMENT_STATUS") or "").lower() == "completed"
    )
    disbursed_aid = sum(
        Decimal(str(row.get("AID_AMOUNT") or 0))
        for row in aid
        if str(row.get("AID_STATUS") or "").lower() == "disbursed"
    )
    return max(Decimal("0.00"), total_charges - completed_payments - disbursed_aid)


@app.after_request
def cors(response):
    allowed = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    origin = request.headers.get("Origin", "").rstrip("/")
    if origin and (not allowed or origin == allowed or origin.endswith(".github.io")):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Stripe-Signature"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/health")
@app.route("/api/health")
def health():
    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return jsonify({"status": "ok", "database": "connected"})
    except Error:
        return jsonify({"status": "error", "database": "unavailable"}), 503
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/student/<int:student_id>", methods=["GET", "OPTIONS"])
def get_student(student_id):
    if request.method == "OPTIONS":
        return ("", 204)
    if student_id < 1:
        return jsonify({"error": "Student ID must be a positive number"}), 400

    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        account = load_student_account(cursor, student_id)
        if not account:
            return jsonify({"error": "Student not found"}), 404
        return jsonify(account)
    except Error:
        app.logger.exception("Student lookup failed")
        return jsonify({"error": "Database connection or query failed"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/payments/create-checkout-session", methods=["POST", "OPTIONS"])
def create_checkout_session():
    if request.method == "OPTIONS":
        return ("", 204)

    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        return jsonify({"error": "Payments are not configured yet. Add STRIPE_SECRET_KEY in Railway."}), 503

    data = request.get_json(silent=True) or {}
    try:
        student_id = int(data.get("studentId"))
        amount = Decimal(str(data.get("amount"))).quantize(Decimal("0.01"))
    except (TypeError, ValueError, InvalidOperation):
        return jsonify({"error": "A valid student ID and payment amount are required."}), 400

    if student_id < 1 or amount < Decimal("0.50"):
        return jsonify({"error": "Student ID must be positive and payment must be at least $0.50."}), 400

    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        account = load_student_account(cursor, student_id)
        if not account:
            return jsonify({"error": "Student not found."}), 404

        balance = calculate_balance(account)
        if balance <= 0:
            return jsonify({"error": "There is no outstanding balance to pay."}), 400
        if amount > balance:
            return jsonify({"error": f"Payment cannot exceed the current balance of ${balance:.2f}."}), 400

        stripe.api_key = secret_key
        frontend_return = os.getenv("FRONTEND_RETURN_URL", os.getenv("FRONTEND_URL", "")).strip()
        if not frontend_return:
            return jsonify({"error": "Set FRONTEND_RETURN_URL in Railway before enabling checkout."}), 503
        frontend_return = frontend_return.rstrip("/")

        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Student account payment - student {student_id}"},
                    "unit_amount": int(amount * 100),
                },
                "quantity": 1,
            }],
            client_reference_id=str(student_id),
            metadata={"student_id": str(student_id)},
            success_url=f"{frontend_return}?payment=success&student_id={student_id}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_return}?payment=cancelled&student_id={student_id}",
        )
        return jsonify({"checkoutUrl": session.url})
    except stripe.error.StripeError:
        app.logger.exception("Stripe checkout creation failed")
        return jsonify({"error": "Stripe could not create the checkout session."}), 502
    except Error:
        app.logger.exception("Database lookup for checkout failed")
        return jsonify({"error": "Unable to verify the student balance."}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/stripe/webhook", methods=["POST"])
def stripe_webhook():
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        return jsonify({"error": "Stripe webhook is not configured."}), 503

    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
    except ValueError:
        return jsonify({"error": "Invalid webhook payload."}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid Stripe signature."}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("payment_status") == "paid":
            metadata = session.get("metadata") or {}
            try:
                student_id = int(metadata.get("student_id") or session.get("client_reference_id"))
                amount = Decimal(session.get("amount_total", 0)) / Decimal(100)
                if student_id < 1 or amount <= 0:
                    raise ValueError("Invalid payment details")
            except (TypeError, ValueError, InvalidOperation):
                return jsonify({"error": "Payment metadata is incomplete."}), 400

            connection = None
            cursor = None
            try:
                connection = connect()
                cursor = connection.cursor()
                cursor.execute(
                    """INSERT INTO Payments
                       (STU_ID, PAYMENT_AMOUNT, PAYMENT_STATUS, PAYMENT_DATE,
                        PAYMENT_METHOD, TRANSACTION_ID, STRIPE_SESSION_ID)
                       VALUES (%s, %s, 'Completed', NOW(), 'Stripe Checkout', %s, %s)
                       ON DUPLICATE KEY UPDATE
                         PAYMENT_AMOUNT = VALUES(PAYMENT_AMOUNT),
                         PAYMENT_STATUS = 'Completed',
                         PAYMENT_DATE = COALESCE(PAYMENT_DATE, NOW()),
                         PAYMENT_METHOD = 'Stripe Checkout',
                         TRANSACTION_ID = VALUES(TRANSACTION_ID)""",
                    (
                        student_id,
                        str(amount),
                        str(session.get("payment_intent") or ""),
                        session.get("id"),
                    ),
                )
                connection.commit()
            except Error:
                if connection:
                    connection.rollback()
                app.logger.exception("Could not record confirmed Stripe payment")
                return jsonify({"error": "Could not record payment."}), 500
            finally:
                if cursor:
                    cursor.close()
                if connection and connection.is_connected():
                    connection.close()

    return jsonify({"received": True})


@app.route("/api/financial-aid/<int:aid_id>/decision", methods=["POST", "OPTIONS"])
def financial_aid_decision(aid_id):
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    try:
        student_id = int(data.get("studentId"))
    except (TypeError, ValueError):
        return jsonify({"error": "A valid student ID is required."}), 400

    decision = str(data.get("decision", "")).strip().title()
    if decision not in ("Accepted", "Declined"):
        return jsonify({"error": "Decision must be Accepted or Declined."}), 400
    if aid_id < 1 or student_id < 1:
        return jsonify({"error": "Student ID and aid ID must be positive numbers."}), 400

    connection = None
    cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT 1 FROM CHARGES
               WHERE STU_ID = %s AND AID_ID = %s LIMIT 1""",
            (student_id, aid_id),
        )
        if not cursor.fetchone():
            return jsonify({"error": "This financial-aid award is not linked to this student."}), 404

        cursor.execute(
            """INSERT INTO Financial_Aid_Decisions (AID_ID, STU_ID, DECISION)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE DECISION = VALUES(DECISION), DECISION_DATE = CURRENT_TIMESTAMP""",
            (aid_id, student_id, decision),
        )
        connection.commit()
        return jsonify({"success": True, "status": decision})
    except Error:
        if connection:
            connection.rollback()
        app.logger.exception("Financial-aid decision failed")
        return jsonify({"error": "Unable to save the financial-aid decision."}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
