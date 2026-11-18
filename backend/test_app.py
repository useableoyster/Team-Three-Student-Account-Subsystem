import unittest
from unittest.mock import Mock, patch

from app import app
from mysql.connector import Error


class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_health_reports_database_connection(self):
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor

        with patch("app.connect", return_value=connection):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_missing_student_returns_404(self):
        connection = Mock()
        cursor = Mock()
        cursor.fetchone.return_value = None
        connection.cursor.return_value = cursor

        with patch("app.connect", return_value=connection):
            response = self.client.get("/api/student/9999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Student not found")

    def test_student_returns_relationship_records(self):
        connection = Mock()
        cursor = Mock()
        cursor.fetchone.return_value = {
            "STU_ID": 1001,
            "STU_FNAME": "Jordan",
            "STU_LNAME": "Willams",
            "STU_EMAIL": "jwilliams@email.com",
            "STU_MAJOR": "Computer Science",
            "STU_CLASS": "Sophomore",
            "STU_ENROLL": "TRUE",
        }
        charge = {
            "CHARGE_ID": 501,
            "STU_ID": 1001,
            "HOUSE_ID": 101,
            "MEALPLAN_ID": 201,
            "TUTION_ID": 301,
            "AID_ID": 401,
        }
        cursor.fetchall.side_effect = [
            [charge],
            [{"PAYMENT_ID": 601, "STU_ID": 1001}],
            [{"HOUSE_ID": 101}],
            [{"MEALPLAN_ID": 201}],
            [{"TUTION_ID": 301}],
            [{"AID_ID": 401}],
        ]
        connection.cursor.return_value = cursor

        with patch("app.connect", return_value=connection):
            response = self.client.get("/api/student/1001")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["records"]["CHARGES"], [charge])
        self.assertEqual(response.get_json()["records"]["Housing"], [{"HOUSE_ID": 101}])

    def test_database_error_returns_500(self):
        with patch("app.connect", side_effect=Error()):
            response = self.client.get("/api/student/1001")

        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
