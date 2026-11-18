
import os
import mysql.connector
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder="../frontend", static_url_path="")

@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/student/<int:student_id>")
def get_student(student_id):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user=os.getenv("DB_USER", "root"),
            password=os.environ["DB_PASSWORD"],
            database="Higher_education"
        )

        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM Student WHERE STU_ID = %s",
                (student_id,)
            )
            student = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

        if student:
            return jsonify(student)

        return jsonify({"error": "Student not found"}), 404

    except mysql.connector.Error:
        return jsonify({"error": "Database connection or query failed"}), 500

if __name__ == "__main__":
    app.run(debug=True)
