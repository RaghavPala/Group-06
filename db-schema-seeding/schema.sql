CREATE TABLE IF NOT EXISTS users (
    netid VARCHAR(9) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_instructor BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    course_id VARCHAR(20) PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    instructor_netid VARCHAR(9) NOT NULL REFERENCES users(netid),
    enrollment_code CHAR(8) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_netid VARCHAR(9) NOT NULL REFERENCES users(netid) ON DELETE CASCADE,
    course_id VARCHAR(20) NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_netid, course_id)
);

CREATE TABLE IF NOT EXISTS class_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    course_id VARCHAR(20) NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    class_date DATE NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    attendance_window_end TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_time >= start_time),
    CHECK (attendance_window_end >= start_time)
);

CREATE TABLE IF NOT EXISTS attendance_records (
    attendance_id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES class_sessions(session_id) ON DELETE CASCADE,
    student_netid VARCHAR(9) NOT NULL REFERENCES users(netid) ON DELETE CASCADE,
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    token_epoch BIGINT,
    UNIQUE (session_id, student_netid)
);

CREATE INDEX IF NOT EXISTS idx_courses_enrollment_code
    ON courses (enrollment_code);

CREATE INDEX IF NOT EXISTS idx_enrollments_student_netid
    ON enrollments (student_netid);

CREATE INDEX IF NOT EXISTS idx_class_sessions_course_active
    ON class_sessions (course_id, is_active, class_date);

CREATE INDEX IF NOT EXISTS idx_attendance_records_student_netid
    ON attendance_records (student_netid);
