from smart_attendance.db.postgres import get_connection
from smart_attendance.services.tokens import get_current_epoch


# Used by the login flow — returns the full user row (incl. password_hash)
# so auth can verify the bcrypt hash stored in the DB.
def get_user_by_netid(netid):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT netid, name, email, password_hash, is_instructor
            FROM users
            WHERE netid = %s
            """,
            (netid,),
        )
        return cur.fetchone()


def get_student(netid):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT netid, name, email
            FROM users
            WHERE netid = %s AND is_instructor = FALSE
            """,
            (netid,),
        )
        return cur.fetchone()


def get_course(course_id):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                course_id,
                course_name AS name,
                instructor_netid AS instructor,
                enrollment_code
            FROM courses
            WHERE course_id = %s
            """,
            (course_id,),
        )
        return cur.fetchone()


def get_course_by_enrollment_code(code):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                course_id,
                course_name AS name,
                instructor_netid AS instructor,
                enrollment_code
            FROM courses
            WHERE enrollment_code = %s
            """,
            (code,),
        )
        return cur.fetchone()


def is_enrolled(netid, course_id):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM enrollments
            WHERE student_netid = %s AND course_id = %s
            """,
            (netid, course_id),
        )
        return cur.fetchone() is not None


def enroll_student(netid, course_id):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO enrollments (student_netid, course_id)
            VALUES (%s, %s)
            ON CONFLICT (student_netid, course_id) DO NOTHING
            RETURNING student_netid
            """,
            (netid, course_id),
        )
        return cur.fetchone() is not None


def is_session_active(course_id):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM class_sessions
            WHERE course_id = %s
              AND is_active = TRUE
              AND CURRENT_TIMESTAMP <= attendance_window_end
            ORDER BY start_time DESC
            LIMIT 1
            """,
            (course_id,),
        )
        return cur.fetchone() is not None


def is_already_marked(netid, course_id):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM attendance_records ar
            JOIN class_sessions cs ON cs.session_id = ar.session_id
            WHERE ar.student_netid = %s
              AND cs.course_id = %s
              AND cs.class_date = CURRENT_DATE
            LIMIT 1
            """,
            (netid, course_id),
        )
        return cur.fetchone() is not None


def mark_attendance(netid, course_id):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            WITH active_session AS (
                SELECT session_id
                FROM class_sessions
                WHERE course_id = %s
                  AND is_active = TRUE
                  AND CURRENT_TIMESTAMP <= attendance_window_end
                ORDER BY start_time DESC
                LIMIT 1
            )
            INSERT INTO attendance_records (session_id, student_netid, token_epoch)
            SELECT session_id, %s, %s
            FROM active_session
            ON CONFLICT (session_id, student_netid) DO NOTHING
            RETURNING attendance_id
            """,
            (course_id, netid, get_current_epoch()),
        )
        return cur.fetchone() is not None


def get_student_courses(netid):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT course_id
            FROM enrollments
            WHERE student_netid = %s
            ORDER BY course_id
            """,
            (netid,),
        )
        return [row["course_id"] for row in cur.fetchall()]


def get_instructor_courses(instructor_netid):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT course_id, course_name AS name, enrollment_code
            FROM courses
            WHERE instructor_netid = %s
            ORDER BY course_id
            """,
            (instructor_netid,),
        )
        return cur.fetchall()


# Inserts a new course owned by instructor_netid with a pre-generated
# enrollment_code. Returns True on insert, False if course_id already exists.
# Enrollment_code collisions bubble up as IntegrityError (caller retries).
def create_course(course_id, course_name, instructor_netid, enrollment_code):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO courses (course_id, course_name, instructor_netid, enrollment_code)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (course_id) DO NOTHING
            RETURNING course_id
            """,
            (course_id, course_name, instructor_netid, enrollment_code),
        )
        return cur.fetchone() is not None


# Opens a new class_sessions row for today, active immediately. window_minutes
# controls how long scans are accepted; duration_minutes is the nominal class
# length (end_time, informational). Returns the new session_id.
def start_session(course_id, window_minutes, duration_minutes):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO class_sessions
                (course_id, class_date, start_time, end_time,
                 attendance_window_end, is_active)
            VALUES (
                %s,
                CURRENT_DATE,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP + (%s * INTERVAL '1 minute'),
                CURRENT_TIMESTAMP + (%s * INTERVAL '1 minute'),
                TRUE
            )
            RETURNING session_id
            """,
            (course_id, duration_minutes, window_minutes),
        )
        return cur.fetchone()["session_id"]


# Feeds the CSV export. One row per (student, session they attended).
# Absent students are implicit (no row) — the schema only stores presence.
def get_course_attendance(course_id):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.netid, u.name, u.email,
                   cs.class_date, cs.session_id,
                   ar.scanned_at
            FROM attendance_records ar
            JOIN class_sessions cs ON cs.session_id = ar.session_id
            JOIN users          u  ON u.netid      = ar.student_netid
            WHERE cs.course_id = %s
            ORDER BY cs.class_date, u.netid
            """,
            (course_id,),
        )
        return cur.fetchall()
