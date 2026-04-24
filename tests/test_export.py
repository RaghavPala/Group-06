# Fake DB for tests
import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['PROPAGATE_EXCEPTIONS'] = False

    with app.test_client() as client:
        yield client

def login_student(client):
    with client.session_transaction() as sess:
        sess['netid'] = 'dal123456'
        sess["is_instructor"] = False
        sess['password'] = 'password1234*'

def login_instructor(client):
    with client.session_transaction() as sess:
        sess['netid'] = 'proftest'
        sess["is_instructor"] = True
        sess['password'] = 'profpass1*'

# Case 1: Valid instructor session, valid course, valid data
def test_export_attendance_valid(client, monkeypatch):

    import smart_attendance.attendance.routes as routes

    def fake_get_course(course_id):
        return {"id": course_id}

    def fake_get_attendance(course_id):
        return [
            {
                "netid": "dal123456",
                "name": "Test Student",
                "email": "test@example.com",
                "class_date": "2026-1-1",
                "session_id": 1,
                "scanned_at": "10:00"
            }
        ]

    monkeypatch.setattr(routes.repository, 'get_course', fake_get_course)
    monkeypatch.setattr(routes.repository, 'get_course_attendance', fake_get_attendance)

    login_instructor(client)
    resp = client.get('/attendance/export?course_id=CS3354.001')

    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert 'attachment; filename="attendance_CS3354.001.csv"' in resp.headers["Content-Disposition"]

    data = resp.data.decode()
    assert "netid,name,email,class_date,session_id,scanned_at" in data
    assert "dal123456,Test Student,test@example.com,2026-1-1,1,10:00" in data

# Case 2: Not authenticated
def test_export_attendance_not_authenticated(client):
    resp = client.get('/attendance/export?course_id=CS3354.001')
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "not authenticated"

# Case 3: Student access denied
def test_export_attendance_student_access_denied(client):
    login_student(client)
    resp = client.get('/attendance/export?course_id=CS3354.001')
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "access denied"

# Case 4: Missing course_id
def test_export_attendance_instructor_access_denied(client):
    login_instructor(client)
    resp = client.get('/attendance/export')
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "missing course_id"

# Case 5: Course not found
def test_export_attendance_course_not_found(client, monkeypatch):
    import smart_attendance.attendance.routes as routes

    def fake_get_course(course_id):
        return None

    monkeypatch.setattr(routes.repository, 'get_course', fake_get_course)

    login_instructor(client)
    resp = client.get('/attendance/export?course_id=CS3354.001')

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "course not found"

# Case 6: Valid request, no attendance data
def test_export_attendance_empty(client, monkeypatch):
    import smart_attendance.attendance.routes as routes
    def fake_get_course(course_id):
        return {"id": course_id}

    def fake_get_attendance(course_id):
        return []

    monkeypatch.setattr(routes.repository, 'get_course', fake_get_course)
    monkeypatch.setattr(routes.repository, 'get_course_attendance', fake_get_attendance)

    login_instructor(client)
    resp = client.get('/attendance/export?course_id=CS3354.001')

    assert resp.status_code == 200
    data = resp.data.decode()

    assert "netid,name,email,class_date,session_id,scanned_at" in data
    assert data.strip().count("\n") == 0

# Case 7: Repository exception (DB failure)
def test_export_attendance_repository_exception(client, monkeypatch):
    import smart_attendance.attendance.routes as routes
    def fake_get_course(course_id):
        raise Exception("DB failure")

    monkeypatch.setattr(routes.repository, 'get_course', fake_get_course)

    login_instructor(client)
    resp = client.get('/attendance/export?course_id=CS3354.001')
    assert resp.status_code == 500

# Case 8: Malformed row
def test_export_attendance_malformed_row(client, monkeypatch):
    import smart_attendance.attendance.routes as routes
    def fake_get_course(course_id):
        return {"id": course_id}

    def fake_get_attendance(course_id):
        return [
            {
                "netid": "dal123456",
                # Name is missing
                "email": "test@example.com",
                "class_date": "2026-1-1",
                "session_id": 1,
                "scanned_at": "10:00"
            }
        ]

    monkeypatch.setattr(routes.repository, 'get_course', fake_get_course)
    monkeypatch.setattr(routes.repository, 'get_course_attendance', fake_get_attendance)
    login_instructor(client)
    resp = client.get('/attendance/export?course_id=CS3354.001')
    assert resp.status_code == 500