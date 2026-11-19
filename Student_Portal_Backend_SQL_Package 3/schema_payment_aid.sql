-- Higher_Education payment + financial-aid upgrade
-- Run this against the existing Higher_Education database.
USE Higher_Education;

-- Your existing Payments table is preserved. These columns add the information
-- needed to track a hosted Stripe Checkout payment.
ALTER TABLE Payments
    ADD COLUMN PAYMENT_DATE DATETIME NULL,
    ADD COLUMN PAYMENT_METHOD VARCHAR(30) NULL,
    ADD COLUMN TRANSACTION_ID VARCHAR(255) NULL,
    ADD COLUMN STRIPE_SESSION_ID VARCHAR(255) NULL;

-- Prevent the same Stripe Checkout Session from being attached to two payments.
CREATE UNIQUE INDEX uq_payments_stripe_session
    ON Payments (STRIPE_SESSION_ID);

-- Financial_Aid already contains AID_STATUS. The app uses:
-- Pending = decision not yet made; Accepted; Declined; Disbursed.
-- Normalize existing blank statuses without changing existing awards.
UPDATE Financial_Aid
SET AID_STATUS = 'Pending'
WHERE AID_STATUS IS NULL OR TRIM(AID_STATUS) = '';

-- Optional audit trail for student award decisions.
CREATE TABLE IF NOT EXISTS Financial_Aid_Decisions (
    DECISION_ID BIGINT NOT NULL AUTO_INCREMENT,
    AID_ID INT NOT NULL,
    STU_ID INT NOT NULL,
    DECISION VARCHAR(20) NOT NULL,
    DECISION_DATE DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (DECISION_ID),
    CONSTRAINT fk_aid_decision_award
        FOREIGN KEY (AID_ID) REFERENCES Financial_Aid(AID_ID),
    CONSTRAINT fk_aid_decision_student
        FOREIGN KEY (STU_ID) REFERENCES Student(STU_ID),
    CONSTRAINT chk_aid_decision
        CHECK (DECISION IN ('Accepted', 'Declined')),
    INDEX idx_aid_decisions_student (STU_ID, DECISION_DATE)
);
