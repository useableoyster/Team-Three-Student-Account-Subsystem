
async function searchStudent() {
    const id = document.getElementById("studentId").value;
    const result = document.getElementById("result");

    if (!id) {
        result.textContent = "Please enter a student ID.";
        return;
    }

    try {
        const configuredBase = document
            .querySelector('meta[name="api-base"]')
            .getAttribute("content")
            .replace(/\/$/, "");
        const apiBase = configuredBase ||
            (window.location.hostname === "localhost" ? "http://localhost:5000" : "");
        const response = await fetch(`${apiBase}/api/student/${encodeURIComponent(id)}`);
        const payload = await response.json();

        if (!response.ok) {
            result.textContent = payload.error || "Search failed.";
            return;
        }
        renderStudent(payload);
    } catch (error) {
        result.textContent = "Could not connect to the backend.";
    }
}

function escapeHtml(value) {
    const element = document.createElement("span");
    element.textContent = value == null ? "" : value;
    return element.innerHTML;
}

function renderTable(title, records) {
    if (!records || records.length === 0) {
        return `<h3>${escapeHtml(title)}</h3><p>No records found.</p>`;
    }

    const headers = Object.keys(records[0]);
    const rows = records.map((record) => {
        const cells = headers
            .map((header) => `<td>${escapeHtml(record[header])}</td>`)
            .join("");
        return `<tr>${cells}</tr>`;
    }).join("");

    return `
        <h3>${escapeHtml(title)}</h3>
        <table>
            <thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

function renderStudent(payload) {
    const student = payload.student;
    const result = document.getElementById("result");
    result.innerHTML = `
        <h2>${escapeHtml(student.STU_FNAME)} ${escapeHtml(student.STU_LNAME)}</h2>
        <p>Student ID: ${escapeHtml(student.STU_ID)}</p>
        <p>Email: ${escapeHtml(student.STU_EMAIL)}</p>
        <p>Major: ${escapeHtml(student.STU_MAJOR)}</p>
        <p>Class: ${escapeHtml(student.STU_CLASS)}</p>
        <p>Enrolled: ${escapeHtml(student.STU_ENROLL)}</p>
        ${renderTable("Housing", payload.records.Housing)}
        ${renderTable("Meal Plan", payload.records.Meal_Plan)}
        ${renderTable("Tuition and Fees", payload.records.TUTION_AND_FEES)}
        ${renderTable("Financial Aid", payload.records.Financial_Aid)}
        ${renderTable("Charges", payload.records.CHARGES)}
        ${renderTable("Payments", payload.records.Payments)}
    `;
}
