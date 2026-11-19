// Example integration snippet for your existing Railway Express server.
// Adapt variable names to your current server. Keep your existing GET /api/student/:id route.

const express = require("express");
const mysql = require("mysql2/promise");
const Stripe = require("stripe");
const registerPaymentAidRoutes = require("./payment-aid-routes");

const app = express();
const db = mysql.createPool({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT || 3306),
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME || "Higher_Education",
  waitForConnections: true,
  connectionLimit: 10
});
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

// Register the raw Stripe webhook route before express.json().
registerPaymentAidRoutes(app, db, stripe);
app.use(express.json());

// Keep your existing routes below this line, including GET /api/student/:id.
// app.get("/api/student/:id", existingStudentLookupHandler);

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Student API listening on ${port}`));
