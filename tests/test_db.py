import os
from pathlib import Path

import pytest
import psycopg

from psycopg import errors
from smart_attendance.db.postgres import get_connection


# DATABASE CONFIG

TEST_DB_URL = "postgresql://postgres:password@localhost:5432/smart_attendance_test"

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "db-schema-seeding" / "schema.sql"


@pytest.fixture(scope="session", autouse=True)
def setup_test_schema():
    """
    Ensure the test database has the required schema before any tests run.
    """
    with get_connection() as conn, conn.cursor() as cur:
        schema_sql = SCHEMA_PATH.read_text()
        for statement in [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]:
            cur.execute(statement)


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    """
    Ensure all tests use the test database.
    """
    os.environ["DATABASE_URL"] = TEST_DB_URL


# CLEAN DATABASE BETWEEN TESTS

@pytest.fixture(autouse=True)
def clean_db():
    """
    Reset database tables before each test so each test runs in isolation.
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE attendance_records RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE class_sessions RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE enrollments RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE courses RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")


# TEST 1: TABLES EXIST (DDL CHECK)

def test_tables_created():
    expected_tables = [
        "users",
        "courses",
        "enrollments",
        "class_sessions",
        "attendance_records",
    ]

    with get_connection() as conn, conn.cursor() as cur:
        for table in expected_tables:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                ) AS table_exists
                """,
                (table,),
            )
            assert cur.fetchone()["table_exists"] is True


# TEST 2: VALID INSERT
def test_valid_insert_user():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (netid, name, email, password_hash, is_instructor, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            ("ab1234", "John Doe", "john@example.com", "hash", False),
        )

        cur.execute("SELECT * FROM users WHERE netid = %s", ("ab1234",))
        result = cur.fetchone()

        assert result is not None


# TEST 3: DUPLICATE PRIMARY KEY

def test_duplicate_primary_key():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (netid, name, email, password_hash, is_instructor, created_at)
            VALUES ('ab1234', 'John', 'a@a.com', 'hash', FALSE, NOW())
            """
        )

        with pytest.raises(errors.UniqueViolation):
            cur.execute(
                """
                INSERT INTO users (netid, name, email, password_hash, is_instructor, created_at)
                VALUES ('ab1234', 'Jane', 'b@b.com', 'hash', FALSE, NOW())
                """
            )


# TEST 4: NOT NULL VIOLATION

def test_not_null_violation():
    with get_connection() as conn, conn.cursor() as cur:
        with pytest.raises(errors.NotNullViolation):
            cur.execute(
                """
                INSERT INTO users (netid, name, email, password_hash, is_instructor, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                ("cd5678", None, "test@test.com", "hash", False),
            )


# TEST 5: UNIQUE EMAIL CONSTRAINT

def test_unique_email():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (netid, name, email, password_hash, is_instructor, created_at)
            VALUES ('ab1234', 'John', 'dup@email.com', 'hash', FALSE, NOW())
            """
        )

        with pytest.raises(errors.UniqueViolation):
            cur.execute(
                """
                INSERT INTO users (netid, name, email, password_hash, is_instructor, created_at)
                VALUES ('cd5678', 'Jane', 'dup@email.com', 'hash', FALSE, NOW())
                """
            )


# TEST 6: FOREIGN KEY VIOLATION

def test_foreign_key_violation():
    with get_connection() as conn, conn.cursor() as cur:
        with pytest.raises(errors.ForeignKeyViolation):
            cur.execute(
                """
                INSERT INTO courses (course_id, course_name, instructor_netid, enrollment_code, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                ("CS101", "Intro to CS", "nonexist", "ABCDEFGH"),
            )


# TEST 7: CHECK CONSTRAINT

import datetime


def test_check_constraint():
    now = datetime.datetime.now()

    with get_connection() as conn, conn.cursor() as cur:
        # Insert instructor
        cur.execute(
            """
            INSERT INTO users (netid, name, email, password_hash, is_instructor, created_at)
            VALUES ('inst1', 'Instructor', 'inst@test.com', 'hash', TRUE, NOW())
            """
        )

        # Insert course
        cur.execute(
            """
            INSERT INTO courses (course_id, course_name, instructor_netid, enrollment_code, created_at)
            VALUES ('CS101', 'Intro', 'inst1', 'ABCDEFGH', NOW())
            """
        )

        # Invalid session: end_time < start_time
        with pytest.raises(errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO class_sessions
                (course_id, class_date, start_time, end_time, attendance_window_end)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    "CS101",
                    now.date(),
                    now,
                    now - datetime.timedelta(hours=1),
                    now,
                ),
            )