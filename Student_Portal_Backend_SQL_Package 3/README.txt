# Student Account Portal: Payments + Financial Aid

## Included files
- `Student_Account_Portal_Payments_Aid.html`: updated student portal UI (separate download).
- `schema_payment_aid.sql`: migration for the existing Higher_Education database.
- `payment-aid-routes.js`: Express routes for Stripe Checkout, payment history, and award decisions.
- `server-integration-example.js`: example of mounting the routes in an Express API.
- `.env.example`: Railway variables required by the backend.

## 1. Database
Back up your database, then run `schema_payment_aid.sql` against the existing `Higher_Education` database. The migration assumes the existing `Payments.PAYMENT_ID` is an auto-increment primary key and `Financial_Aid.AID_ID` / `Student.STU_ID` are integer keys, consistent with the team's original schema.

## 2. Backend dependencies
From your existing Node/Express API project, install:
```bash
npm install stripe mysql2 express
```
Copy `payment-aid-routes.js` into the backend project. Mount it as shown in `server-integration-example.js`. Keep the existing `/api/student/:id` endpoint. Do not run a second server if Railway already runs your API.

The webhook route must be registered before `express.json()` so Stripe signature verification receives the raw request body. If your app already has a global JSON parser above this route, move the webhook route above it.

## 3. Stripe test mode
Create a Stripe account and use TEST keys only for the class demo. Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and `FRONTEND_URL` to Railway Variables. Configure a Stripe webhook endpoint:
`https://YOUR-RAILWAY-DOMAIN/api/stripe/webhook`
Subscribe to:
- `checkout.session.completed`
- `checkout.session.expired`

Copy the webhook signing secret into `STRIPE_WEBHOOK_SECRET`. Never put the Stripe secret key in the HTML or GitHub repository.

Use Stripe's published test card numbers in test mode only. No real card data should be entered into this demonstration site.

## 4. Frontend
Upload `Student_Account_Portal_Payments_Aid.html` to the same approved web host as your current page. Its API base is currently set to:
`https://team-three-student-account-subsystem-production.up.railway.app`

The frontend expects:
- `POST /api/payments/create-checkout-session` -> `{ "checkoutUrl": "https://checkout.stripe.com/..." }`
- `POST /api/financial-aid/:aidId/decision` -> `{ "success": true, "status": "Accepted" }`
- existing `GET /api/student/:id`

## 5. Financial aid statuses
Use `Pending` for an undecided award, `Accepted` or `Declined` for student choices, and `Disbursed` only after the institution actually applies the aid. The balance calculation should subtract only `Disbursed` aid, not merely `Accepted` aid.

## Important security note
The current portal signs in using only a student ID lookup. That is acceptable only for a classroom prototype with sample data. Before real student use, add proper login/session authentication and enforce that the authenticated student—not a browser-supplied student ID—owns each payment and award. Real financial-aid acceptance may also require additional institutional rules and an audit process.
