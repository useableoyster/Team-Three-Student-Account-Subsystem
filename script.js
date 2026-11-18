
async function searchStudent() {
    const id = document.getElementById("studentId").value;
    const result = document.getElementById("result");

    if (!id) {
        result.textContent = "Please enter a student ID.";
        return;
    }

    try {
        const response = await fetch(`/api/student/${id}`);
        const student = await response.json();

        if (!response.ok) {
            result.textContent = student.error || "Search failed.";
            return;
        }

        result.innerHTML = `
            <h2>${student.STU_FNAME} ${student.STU_LNAME}</h2>
            <p>Student ID: ${student.STU_ID}</p>
            <p>Email: ${student.STU_EMAIL}</p>
            <p>Major: ${student.STU_MAJOR}</p>
            <p>Class: ${student.STU_CLASS}</p>
            <p>Enrolled: ${student.STU_ENROLL}</p>
        `;
    } catch (error) {
        result.textContent = "Could not connect to the backend.";
    }
}
