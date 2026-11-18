# Team Three Student Account Subsystem

A simple Flask and MySQL student account portal. The existing HTML, CSS, and JavaScript
in the repository root are the GitHub Pages frontend.

## Database status

`database/schema.sql` contains the team's seven original tables and sample records for
students 1001–1008. It preserves the supplied table and column names, including the
`CHARGES` foreign-key relationships. Do not use SQLite.

When the original `schema.sql` is available, initialize a Railway MySQL database by using
the Railway MySQL console or a SQL client:

1. Create or select the Railway MySQL database.
2. Run `database/schema.sql` once.
3. Verify that `Higher_education` and the seven original tables exist.

Do not run the schema again against a deployed database unless you intend to reset or
replace existing data.

## Railway backend

1. Create a Railway project and add a MySQL database.
2. Create a second service from this GitHub repository.
3. Set the service variables from the Railway MySQL service:
   - `MYSQLHOST`
   - `MYSQLPORT`
   - `MYSQLUSER`
   - `MYSQLPASSWORD`
   - `MYSQLDATABASE`
4. Set `FRONTEND_URL` to the exact GitHub Pages origin, for example
   `https://useableoyster.github.io`.
5. Deploy. Railway will use `Procfile` and `requirements.txt`.

The API has a database health check at `/health` or `/api/health`.

## GitHub Pages frontend

The frontend is located at the repository root (`index.html`, `script.js`, and `style.css`)
and is already suitable for GitHub Pages.

Set the backend URL once in `index.html`:

```html
<meta name="api-base" content="https://your-railway-service.up.railway.app">
```

For local testing, leave the value empty and run the Flask API on port 5000.

## Local development

```bash
python -m pip install -r requirements.txt
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your-password
export DB_NAME=Higher_education
python backend/app.py
```
