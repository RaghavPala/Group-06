# Group-06

Group project for CS 3354 - Smart Attendance Tracker.

## Local Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Install PostgreSQL

Install PostgreSQL for Windows from the official download page:

https://www.postgresql.org/download/windows/

During installation:

- install the PostgreSQL server
- keep the default port `5432`
- remember the password you set for the `postgres` user
- `Stack Builder` is optional and can be skipped

### 4. Create the project database

Open `pgAdmin 4` or `SQL Shell (psql)` and create a database named `smart_attendance`.

```sql
CREATE DATABASE smart_attendance;
```

### 5. Create tables and load starter data

From the project root, run:

```powershell
psql -U postgres -d smart_attendance -f db\schema.sql
psql -U postgres -d smart_attendance -f db\seed.sql
```

If your PostgreSQL username is not `postgres`, replace it with your own username.

### 6. Set the database connection string

In PowerShell, set `DATABASE_URL` before running the app:

```powershell
$env:DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/smart_attendance"
```

Replace `YOUR_PASSWORD` with the password you chose during PostgreSQL installation.

### 7. Run the Flask app

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000/
```

### 8. Run the test suite

```powershell
pytest -q
```

## Notes

- `db/schema.sql` creates the database tables.
- `db/seed.sql` inserts starter data for demo users, courses, enrollments, and class sessions.
- Attendance and enrollment DB functions use PostgreSQL when `DATABASE_URL` is set.
- Login still uses the temporary in-memory user store for now.
