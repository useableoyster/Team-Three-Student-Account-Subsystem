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

    def test_database_error_returns_500(self):
        with patch("app.connect", side_effect=Error()):
            response = self.client.get("/api/student/1001")

        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
