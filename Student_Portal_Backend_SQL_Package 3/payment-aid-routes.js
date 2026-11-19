// payment-aid-routes.js
// Node.js / Express + mysql2 + Stripe integration for the existing Higher_Education DB.
// Mount these routes in the existing Railway API; do not create a second API server
// unless that is how your team currently deploys its project.

const express = require("express");

module.exports = function registerPaymentAidRoutes(app, db, stripe) {
  if (!app || !db || !stripe) {
    throw new Error("registerPaymentAidRoutes requires app, db, and stripe.");
  }

  // IMPORTANT: Mount the Stripe webhook BEFORE app.use(express.json()) in your main
  // server file, because Stripe signature verification needs the untouched raw body.
  app.post(
    "/api/stripe/webhook",
    express.raw({ type: "application/json" }),
    async (req, res) => {
      let event;
      try {
        event = stripe.webhooks.constructEvent(
          req.body,
          req.headers["stripe-signature"],
          process.env.STRIPE_WEBHOOK_SECRET
        );
      } catch (err) {
        return res.status(400).send(`Webhook signature verification failed: ${err.message}`);
      }

      try {
        if (event.type === "checkout.session.completed") {
          const session = event.data.object;
          const paymentId = Number(session.metadata && session.metadata.paymentId);
          const studentId = Number(session.metadata && session.metadata.studentId);

          if (paymentId && studentId && session.payment_status === "paid") {
            await db.execute(
              `UPDATE Payments
               SET PAYMENT_STATUS = 'Completed',
                   PAYMENT_DATE = NOW(),
                   TRANSACTION_ID = ?,
                   PAYMENT_METHOD = 'Card'
               WHERE PAYMENT_ID = ? AND STU_ID = ?
                 AND (STRIPE_SESSION_ID = ? OR STRIPE_SESSION_ID IS NULL)`,
              [session.payment_intent || session.id, paymentId, studentId, session.id]
            );
          }
        } else if (event.type === "checkout.session.expired") {
          const session = event.data.object;
          const paymentId = Number(session.metadata && session.metadata.paymentId);
          const studentId = Number(session.metadata && session.metadata.studentId);
          if (paymentId && studentId) {
            await db.execute(
              `UPDATE Payments SET PAYMENT_STATUS = 'Failed'
               WHERE PAYMENT_ID = ? AND STU_ID = ? AND PAYMENT_STATUS = 'Pending'`,
              [paymentId, studentId]
            );
          }
        }
        return res.json({ received: true });
      } catch (err) {
        console.error("Stripe webhook database error:", err);
        return res.status(500).json({ error: "Could not update payment record." });
      }
    }
  );

  // This route expects express.json() to be enabled by the main app.
  app.post("/api/payments/create-checkout-session", async (req, res) => {
    const studentId = Number(req.body && req.body.studentId);
    const amount = Number(req.body && req.body.amount);

    if (!Number.isInteger(studentId) || studentId < 1) {
      return res.status(400).json({ error: "A valid student ID is required." });
    }
    if (!Number.isFinite(amount) || amount < 0.5 || amount > 100000) {
      return res.status(400).json({ error: "Enter a payment between $0.50 and $100,000." });
    }
    if (!process.env.FRONTEND_URL) {
      return res.status(500).json({ error: "FRONTEND_URL is not configured on the server." });
    }

    let paymentId;
    try {
      const [students] = await db.execute(
        "SELECT STU_ID FROM Student WHERE STU_ID = ? LIMIT 1",
        [studentId]
      );
      if (!students.length) return res.status(404).json({ error: "Student account not found." });

      const [insert] = await db.execute(
        `INSERT INTO Payments (STU_ID, PAYMENT_AMOUNT, PAYMENT_STATUS, PAYMENT_METHOD, PAYMENT_DATE)
         VALUES (?, ?, 'Pending', 'Card', NOW())`,
        [studentId, amount.toFixed(2)]
      );
      paymentId = insert.insertId;

      const base = process.env.FRONTEND_URL.replace(/\/$/, "");
      const session = await stripe.checkout.sessions.create({
        mode: "payment",
        payment_method_types: ["card"],
        line_items: [{
          quantity: 1,
          price_data: {
            currency: "usd",
            unit_amount: Math.round(amount * 100),
            product_data: { name: "Student Account Payment" }
          }
        }],
        metadata: { paymentId: String(paymentId), studentId: String(studentId) },
        success_url: `${base}/?payment=success`,
        cancel_url: `${base}/?payment=cancelled`
      });

      await db.execute(
        "UPDATE Payments SET STRIPE_SESSION_ID = ? WHERE PAYMENT_ID = ? AND STU_ID = ?",
        [session.id, paymentId, studentId]
      );
      return res.json({ checkoutUrl: session.url });
    } catch (err) {
      console.error("Create checkout session error:", err);
      if (paymentId) {
        try {
          await db.execute(
            "UPDATE Payments SET PAYMENT_STATUS = 'Failed' WHERE PAYMENT_ID = ? AND PAYMENT_STATUS = 'Pending'",
            [paymentId]
          );
        } catch (_) {}
      }
      return res.status(500).json({ error: "Unable to start secure checkout." });
    }
  });

  app.get("/api/payments/:studentId", async (req, res) => {
    const studentId = Number(req.params.studentId);
    if (!Number.isInteger(studentId) || studentId < 1) {
      return res.status(400).json({ error: "Invalid student ID." });
    }
    try {
      const [rows] = await db.execute(
        `SELECT PAYMENT_ID, PAYMENT_AMOUNT, PAYMENT_STATUS, PAYMENT_DATE,
                PAYMENT_METHOD, TRANSACTION_ID
         FROM Payments WHERE STU_ID = ? ORDER BY PAYMENT_ID DESC`,
        [studentId]
      );
      return res.json({ payments: rows });
    } catch (err) {
      console.error("Payment history error:", err);
      return res.status(500).json({ error: "Unable to load payment history." });
    }
  });

  app.post("/api/financial-aid/:aidId/decision", async (req, res) => {
    const aidId = Number(req.params.aidId);
    const studentId = Number(req.body && req.body.studentId);
    const decision = String(req.body && req.body.decision || "");

    if (!Number.isInteger(aidId) || aidId < 1 ||
        !Number.isInteger(studentId) || studentId < 1 ||
        !["Accepted", "Declined"].includes(decision)) {
      return res.status(400).json({ error: "Invalid award, student, or decision." });
    }

    const connection = await db.getConnection();
    try {
      await connection.beginTransaction();

      const [awards] = await connection.execute(
        `SELECT AID_ID, AID_STATUS FROM Financial_Aid
         WHERE AID_ID = ? AND STU_ID = ? FOR UPDATE`,
        [aidId, studentId]
      );
      if (!awards.length) {
        await connection.rollback();
        return res.status(404).json({ error: "Financial-aid award not found for this student." });
      }

      const currentStatus = String(awards[0].AID_STATUS || "").toLowerCase();
      if (currentStatus === "disbursed") {
        await connection.rollback();
        return res.status(409).json({ error: "A disbursed award cannot be changed here." });
      }

      await connection.execute(
        "UPDATE Financial_Aid SET AID_STATUS = ? WHERE AID_ID = ? AND STU_ID = ?",
        [decision, aidId, studentId]
      );
      await connection.execute(
        `INSERT INTO Financial_Aid_Decisions (AID_ID, STU_ID, DECISION)
         VALUES (?, ?, ?)`,
        [aidId, studentId, decision]
      );

      await connection.commit();
      return res.json({ success: true, aidId, studentId, status: decision });
    } catch (err) {
      await connection.rollback();
      console.error("Financial-aid decision error:", err);
      return res.status(500).json({ error: "Unable to save financial-aid decision." });
    } finally {
      connection.release();
    }
  });
};
