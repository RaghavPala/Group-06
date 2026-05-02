# Changes

## Summary
- Removed the in-memory stub/user layer. Auth and attendance now read/write Postgres exclusively.
- Added routes: `POST /course`, `POST /session/start`, `GET /attendance/export`.
- Added Docker-based Postgres setup with auto-seeding.

## New endpoints

### `POST /course` (instructor)
Creates a course owned by the logged-in instructor. Server generates the enrollment code.

Request body:
```json
{"course_id": "CS1337.002", "course_name": "Computer Science I"}
```

Responses:
- `201` — `{"course_id", "course_name", "enrollment_code"}`
- `400` — missing `course_id` or `course_name`
- `401` — not authenticated
- `403` — not an instructor
- `409` — `course_id` already exists

### `POST /session/start` (instructor)
Opens a class session (`is_active=TRUE`) for today. Required before `/attendance/scan` accepts tokens.

Request body:
```json
{"course_id": "CS3354.001", "window_minutes": 15, "duration_minutes": 75}
```
`window_minutes` (default 15) = how long scans are accepted.
`duration_minutes` (default 75) = nominal class length (sets `end_time`).

Responses:
- `201` — `{"session_id", "course_id", "window_minutes", "duration_minutes"}`
- `400` — missing `course_id`
- `401` — not authenticated
- `403` — not an instructor, or not the course owner
- `404` — course not found

### `GET /attendance/export?course_id=<id>` (instructor)
Downloads a CSV of every attendance record for a course.

CSV columns: `netid, name, email, class_date, session_id, scanned_at`
Response headers: `Content-Type: text/csv`, `Content-Disposition: attachment; filename="attendance_<course_id>.csv"`

Responses:
- `200` — CSV body
- `400` — missing `course_id`
- `401` — not authenticated
- `403` — not an instructor
- `404` — course not found

## Breaking changes

### `DATABASE_URL` is now required
`create_app()` raises `RuntimeError` at startup if `DATABASE_URL` is unset. Previously the app booted against in-memory stubs.

### Auth reads from the `users` table
- Deleted `USER_SEEDS`, `users_db`, `initialize_users()` from `smart_attendance/auth/routes.py`.
- `login()` now calls `repository.get_user_by_netid(netid)` and verifies `password_hash` from the DB.
- Seeded passwords come from `db-schema-seeding/seed.sql` (hashes already present for `proftest`, `dal123456`, `abc123456`).

### Stub layer removed
- Deleted `smart_attendance/db/stubs.py`.
- Deleted `smart_attendance/routes/` (orphaned duplicate blueprint — not referenced anywhere).
- All route call sites now use `repository.*` directly.

### Existing tests will fail until updated
Tests in `tests/` were written against the stub fakes and the in-memory `users_db`. They need:
1. `DATABASE_URL` set.
2. The seeded DB available (via `docker compose up -d` or manual `psql`).
3. An autouse fixture to reset `attendance_records` between tests so write-path tests are repeatable, e.g.:
   ```python
   @pytest.fixture(autouse=True)
   def reset_attendance():
       from smart_attendance.db.postgres import get_connection
       with get_connection() as conn, conn.cursor() as cur:
           cur.execute("DELETE FROM attendance_records")
   ```

## New files
- `docker-compose.yml` — Postgres 16, port 5432, user/password `postgres`, db `smart_attendance`. Mounts `db-schema-seeding/` to `/docker-entrypoint-initdb.d` so schema + seed run automatically on first boot.
- `CHANGES.md` — this file.

## Modified files
- `requirements.txt` — bumped `psycopg[binary]==3.2.9` → `>=3.2.10` (3.2.9 has no wheel for Python 3.14).
- `smart_attendance/__init__.py` — dropped `initialize_users()`, added `DATABASE_URL` guard.
- `smart_attendance/auth/routes.py` — login reads from DB.
- `smart_attendance/auth/__init__.py` — removed stale `initialize_users` re-export.
- `smart_attendance/attendance/routes.py` — uses `repository.*`; adds `/course`, `/session/start`, `/attendance/export`.
- `smart_attendance/db/repository.py` — adds `get_user_by_netid`, `create_course`, `start_session`, `get_course_attendance`.
- `README.md` — Docker-first setup instructions; seeded credentials table.

## Removed files
- `smart_attendance/db/stubs.py`
- `smart_attendance/routes/` (entire directory)

## Setup (new)

Requires Docker + Docker Compose v2. Install steps for macOS / Windows / Linux are in `README.md` § "Install Docker". Quick check: `docker --version && docker compose version`.

```bash
docker compose up -d
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smart_attendance
python app.py
```

Reset to clean seeded state:
```bash
docker compose down -v && docker compose up -d
```

## Known state / caveats
- `app.secret_key` is regenerated via `secrets.token_hex(32)` on every startup — all sessions drop on server restart. Pre-existing, not introduced here.
- `SECRET_KEY` for token HMAC is still hardcoded in `smart_attendance/services/tokens.py`.
- Seed session for `CS3354.001` has a 5-minute `attendance_window_end`; re-seed if it expires during testing.
- No signup route; users still come from seed only.
- Session end route not implemented (sessions expire implicitly via `attendance_window_end`).

## Out of scope (not done here)
- Signup / user creation endpoint.
- `POST /session/end` route.
- Reading `SECRET_KEY` / `app.secret_key` from env.
- Instructor UI for listing their courses / active sessions.
- Test file updates.
