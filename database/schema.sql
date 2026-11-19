
-- Run this file while connected to the provisioned Higher_education database.
-- It is safe to rerun and does not drop or replace an existing database.

CREATE TABLE IF NOT EXISTS Student (
    STU_ID INTEGER NOT NULL,
    STU_FNAME VARCHAR(11) NOT NULL,
    STU_LNAME VARCHAR(15) NOT NULL,
    STU_EMAIL VARCHAR(30) NOT NULL,
    STU_MAJOR VARCHAR(25) NOT NULL,
    STU_CLASS VARCHAR(9) NOT NULL,
    STU_ENROLL ENUM('TRUE','FALSE') NOT NULL,
    PRIMARY KEY (STU_ID)
);

INSERT IGNORE INTO Student VALUES
(1001,'Jordan','Willams','jwilliams@email.com','Computer Science','Sophomore','TRUE'),
(1002,'Maya','Johnson','mjohnson@email.com','Biology','Junior','TRUE'),
(1003,'David','Thompson','dthompson@email.com','Finance','Freshman','TRUE'),
(1004,'Alexis','Brown','abrown@email.com','Psychology','Senior','TRUE'),
(1005,'Christopher','Davis','cdavis@email.com','Cybersecurity','Sophomore','TRUE'),
(1006,'Taylor','Wilson','twilson@email.com','Marketing','Junior','TRUE'),
(1007,'Morgan','Harris','mharris@email.com','Accounting','Freshman','TRUE'),
(1008,'Cameron','Lewis','clewis@email.com','Information Systems','Senior','TRUE');

CREATE TABLE IF NOT EXISTS Housing (
    HOUSE_ID INTEGER NOT NULL,
    DORM_NAME VARCHAR(15) NOT NULL,
    ROOM_TYPE ENUM('Single','Double') NOT NULL,
    SEMESTER INTEGER NOT NULL,
    ACADEMIC_YEAR INTEGER NOT NULL,
    HOUSING_RATE INTEGER NOT NULL,
    PRIMARY KEY (HOUSE_ID)
);

INSERT IGNORE INTO Housing VALUES
(101,'Bethune Annex','Double',1,2026,6500),
(102,'Drew Hall','Double',1,2026,6200),
(103,'College Hall','Single',1,2026,7800),
(104,'Cook Hall','Double',1,2026,6000),
(105,'Quad Hall','Single',1,2026,7500);

CREATE TABLE IF NOT EXISTS Meal_Plan (
    MEALPLAN_ID INTEGER NOT NULL,
    PLAN_NAME VARCHAR(30) NOT NULL,
    MEALPLAN_SWIPES INTEGER NOT NULL,
    BISON_BUCKS DECIMAL(9,2) NOT NULL,
    SEMESTER INTEGER NOT NULL,
    ACADEMIC_YEAR INTEGER NOT NULL,
    PLAN_COST INTEGER NOT NULL,
    PRIMARY KEY (MEALPLAN_ID)
);

INSERT IGNORE INTO Meal_Plan VALUES
(201,'Unlimited',999,300,1,2026,3200),
(202,'Standard',14,200,1,2026,2800),
(203,'Basic',10,150,1,2026,2400),
(204,'Flex',7,250,1,2026,2100),
(205,'Commuter',5,100,1,2026,1200);

CREATE TABLE IF NOT EXISTS TUTION_AND_FEES (
    TUTION_ID INTEGER NOT NULL,
    ITEM_NAME VARCHAR(40),
    RATE_AMOUNT INTEGER NOT NULL,
    PRIMARY KEY (TUTION_ID)
);

INSERT IGNORE INTO TUTION_AND_FEES VALUES
(301,'Undergraduate Tution',18998),
(302,'Technology Fee',200),
(303,'Student Activity Fee',75),
(304,'Transportation Fee',175),
(305,'Laundry Fee',50),
(306,'Orientation Fee',200),
(307,'Endowment Fee',15),
(308,'Student Self-Help Fund Fee',5);

CREATE TABLE IF NOT EXISTS Financial_Aid (
    AID_ID INTEGER NOT NULL,
    AID_NAME VARCHAR(20),
    AID_AMOUNT INTEGER NOT NULL,
    AID_STATUS VARCHAR(15),
    PRIMARY KEY (AID_ID)
);

INSERT IGNORE INTO Financial_Aid VALUES
(401,'Pell Grant',3500,'Approved'),
(402,'Academic Scholarship',2500,'Disbursed'),
(403,'STEM Sholarahip',1500,'Approved'),
(404,'Federal Work Study',2000,'Pending'),
(405,'University Grant',3000,'Disbursed'),
(406,'Merit Scholarship',4000,'Approved');

CREATE TABLE IF NOT EXISTS CHARGES (
    CHARGE_ID INTEGER NOT NULL,
    STU_ID INTEGER NOT NULL,
    HOUSE_ID INTEGER NOT NULL,
    MEALPLAN_ID INTEGER NOT NULL,
    TUTION_ID INTEGER NOT NULL,
    AID_ID INTEGER NOT NULL,
    CHARGE_AMOUNT INTEGER NOT NULL,
    CHARGE_DESCRIPTION VARCHAR(30),
    PRIMARY KEY (CHARGE_ID),
    FOREIGN KEY (STU_ID) REFERENCES Student(STU_ID),
    FOREIGN KEY (HOUSE_ID) REFERENCES Housing(HOUSE_ID),
    FOREIGN KEY (MEALPLAN_ID) REFERENCES Meal_Plan(MEALPLAN_ID),
    FOREIGN KEY (TUTION_ID) REFERENCES TUTION_AND_FEES(TUTION_ID),
    FOREIGN KEY (AID_ID) REFERENCES Financial_Aid(AID_ID)
);

INSERT IGNORE INTO CHARGES VALUES
(501,1001,101,201,301,401,18998,'Undergraduate Tution'),
(502,1002,102,202,301,402,18998,'Undergraduate Tution'),
(503,1003,103,203,301,403,18998,'Undergraduate Tution'),
(504,1004,104,204,301,404,18998,'Undergraduate Tution'),
(505,1005,105,205,301,405,18998,'Undergraduate Tution');

CREATE TABLE IF NOT EXISTS Payments (
    PAYMENT_ID INTEGER NOT NULL,
    STU_ID INTEGER NOT NULL,
    PAYMENT_AMOUNT INTEGER NOT NULL,
    PAYMENT_STATUS VARCHAR(15),
    PRIMARY KEY (PAYMENT_ID),
    FOREIGN KEY (STU_ID) REFERENCES Student(STU_ID)
);

INSERT IGNORE INTO Payments VALUES
(601,1001,5000,'Completed'),
(602,1002,3500,'Completed'),
(603,1003,2000,'Pending'),
(604,1004,4500,'Completed'),
(605,1005,1500,'Failed'),
(606,1006,3000,'Completed'),
(607,1007,2500,'Pending'),
(608,1008,6000,'Completed');





ALTER TABLE Payments
    ADD COLUMN PAYMENT_DATE DATETIME NULL,
    ADD COLUMN PAYMENT_METHOD VARCHAR(30) NULL,
    ADD COLUMN TRANSACTION_ID VARCHAR(255) NULL,
    ADD COLUMN STRIPE_SESSION_ID VARCHAR(255) NULL;


CREATE UNIQUE INDEX uq_payments_stripe_session
    ON Payments (STRIPE_SESSION_ID);


UPDATE Financial_Aid
SET AID_STATUS = 'Pending'
WHERE AID_STATUS IS NULL OR TRIM(AID_STATUS) = '';


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
