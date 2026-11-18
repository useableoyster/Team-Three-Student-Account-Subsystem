import os

import mysql.connector
from flask import Flask, jsonify, request
from mysql.connector import Error


app = Flask(__name__)


def database_config():
    return {
        "host": os.getenv("MYSQLHOST", os.getenv("DB_HOST", "localhost")),
        "port": int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", "3306"))),
        "user": os.getenv("MYSQLUSER", os.getenv("DB_USER", "root")),
        "password": os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", "")),
        "database": os.getenv(
            "MYSQLDATABASE", os.getenv("DB_NAME", "Higher_education")
        ),
    }


def connect():
    return mysql.connector.connect(**database_config())


def related_records(cursor, table_name, key_column, ids):
    if not ids:
        return []
    placeholders = ", ".join(["%s"] * len(ids))
    cursor.execute(
        f"SELECT * FROM `{table_name}` WHERE `{key_column}` IN ({placeholders})",
        tuple(ids),
    )
    return cursor.fetchall()


@app.after_request
def cors(response):
    allowed = os.getenv("FRONTEND_URL", "").strip()
    origin = request.headers.get("Origin")
    if origin and (not allowed or origin == allowed or origin.endswith(".github.io")):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


@app.route("/health")
@app.route("/api/health")
def health():
    connection = None
    try:
        connection = connect()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        connection.close()
        return jsonify({"status": "ok", "database": "connected"})
    except Error:
        if connection:
            connection.close()
        return jsonify({"status": "error", "database": "unavailable"}), 503


@app.route("/api/student/<int:student_id>", methods=["GET", "OPTIONS"])
def get_student(student_id):
    if request.method == "OPTIONS":
        return ("", 204)
    if student_id < 1:
        return jsonify({"error": "Student ID must be a positive number"}), 400

    connection = None
    try:
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM `Student` WHERE `STU_ID` = %s",
            (student_id,),
        )
        student = cursor.fetchone()
        if not student:
            cursor.close()
            connection.close()
            return jsonify({"error": "Student not found"}), 404

        cursor.execute("SELECT * FROM `CHARGES` WHERE `STU_ID` = %s", (student_id,))
        charges = cursor.fetchall()
        cursor.execute("SELECT * FROM `Payments` WHERE `STU_ID` = %s", (student_id,))
        payments = cursor.fetchall()

        related = {
            "CHARGES": charges,
            "Payments": payments,
            "Housing": related_records(
                cursor, "Housing", "HOUSE_ID", [row["HOUSE_ID"] for row in charges]
            ),
            "Meal_Plan": related_records(
                cursor, "Meal_Plan", "MEALPLAN_ID",
                [row["MEALPLAN_ID"] for row in charges],
            ),
            "TUTION_AND_FEES": related_records(
                cursor, "TUTION_AND_FEES", "TUTION_ID",
                [row["TUTION_ID"] for row in charges],
            ),
            "Financial_Aid": related_records(
                cursor, "Financial_Aid", "AID_ID",
                [row["AID_ID"] for row in charges],
            ),
        }

        cursor.close()
        connection.close()
        return jsonify({"student": student, "records": related})
    except Error:
        if connection:
            connection.close()
        return jsonify({"error": "Database connection or query failed"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
