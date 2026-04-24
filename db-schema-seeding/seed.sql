INSERT INTO users (netid, name, email, password_hash, is_instructor)
VALUES
    ('proftest', 'Professor Test', 'proftest@utdallas.edu', '$2b$12$.ZpB.whYrKovfuOP8TKuxuwfCg4A.jSwJ/Ddzaas.aTF9oDavKOrS', TRUE),
    ('dal123456', 'Dallas Student', 'dal123456@utdallas.edu', '$2b$12$.MR2xD92F.QL0wkX0p64r.kKB0gQO/E9ET6Ui8PBFtZxuykA7RMoW', FALSE),
    ('abc123456', 'Alex Student', 'abc123456@utdallas.edu', '$2b$12$.MR2xD92F.QL0wkX0p64r.kKB0gQO/E9ET6Ui8PBFtZxuykA7RMoW', FALSE)
ON CONFLICT (netid) DO UPDATE
SET
    name = EXCLUDED.name,
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    is_instructor = EXCLUDED.is_instructor;

INSERT INTO courses (course_id, course_name, instructor_netid, enrollment_code)
VALUES
    ('CS3354.001', 'Smart Attendance Tracker', 'proftest', 'ABCD1234'),
    ('CS3345.601', 'Data Structures and Introduction to Algorithmic Analysis', 'proftest', 'WXYZ5678')
ON CONFLICT (course_id) DO UPDATE
SET
    course_name = EXCLUDED.course_name,
    instructor_netid = EXCLUDED.instructor_netid,
    enrollment_code = EXCLUDED.enrollment_code;

INSERT INTO enrollments (student_netid, course_id)
VALUES
    ('dal123456', 'CS3354.001'),
    ('dal123456', 'CS3345.601')
ON CONFLICT (student_netid, course_id) DO NOTHING;

INSERT INTO class_sessions (course_id, class_date, start_time, end_time, attendance_window_end, is_active)
SELECT
    'CS3354.001',
    CURRENT_DATE,
    CURRENT_TIMESTAMP - INTERVAL '5 minutes',
    CURRENT_TIMESTAMP + INTERVAL '55 minutes',
    CURRENT_TIMESTAMP + INTERVAL '5 minutes',
    TRUE
WHERE NOT EXISTS (
    SELECT 1
    FROM class_sessions
    WHERE course_id = 'CS3354.001' AND class_date = CURRENT_DATE
);

INSERT INTO class_sessions (course_id, class_date, start_time, end_time, attendance_window_end, is_active)
SELECT
    'CS3345.601',
    CURRENT_DATE,
    CURRENT_TIMESTAMP - INTERVAL '2 hours',
    CURRENT_TIMESTAMP - INTERVAL '1 hour',
    CURRENT_TIMESTAMP - INTERVAL '110 minutes',
    FALSE
WHERE NOT EXISTS (
    SELECT 1
    FROM class_sessions
    WHERE course_id = 'CS3345.601' AND class_date = CURRENT_DATE
);
