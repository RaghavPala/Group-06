import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def login_student(client):
    response = client.post('/login', data={
        "netid": "dal123456",
        "password": "password1234*"
    }, follow_redirects=True)
    assert b"Student Dashboard" in response.data

def login_instructor(client):
    response = client.post('/login', data={
        "netid": "proftest",
        "password": "profpass1*"
    }, follow_redirects=True)
    assert b"Instructor Dashboard" in response.data

# Test Case #1: Valid instructor session, valid course ID, valid action
def test_generate_code_valid(client):
    login_instructor(client)
    response = client.get('/enroll/qr?course_id=CS3354.001')
    assert response.status_code == 200
    data = response.get_json()
    assert "enrollment_code" in data
    assert len(data["enrollment_code"]) == 8

# Test Case #2: Invalid instructor session (student), valid course ID, valid action
def test_generate_code_student_access_denied(client):
    login_student(client)
    response = client.get('/enroll/qr?course_id=CS3354.001')
    assert response.status_code == 403
    assert response.get_json()["error"] == "access denied"

# Test Case #3: Exceptional session (not logged in), valid course ID, valid action
def test_generate_code_not_authenticated(client):
    response = client.get('/enroll/qr?course_id=CS3354.001')
    assert response.status_code == 401
    assert response.get_json()["error"] == "not authenticated"

# Test Case #4: Valid instructor session, invalid course ID, valid action
def test_generate_code_invalid_course(client, monkeypatch):
    import views

    def fake_db_get_course(course_id):
        return None

    monkeypatch.setattr(views, "db_get_course", fake_db_get_course)

    login_instructor(client)
    response = client.get('/enroll/qr?course_id=BAD999')
    assert response.status_code == 404
    assert response.get_json()["error"] == "course not found"

# Test Case #5: Valid instructor session, exceptional course ID (missing), valid action
def test_generate_code_missing_course_id(client, monkeypatch):
    import views

    def fake_db_get_course(course_id):
        return None

    monkeypatch.setattr(views, "db_get_course", fake_db_get_course)

    login_instructor(client)
    response = client.get('/enroll/qr')
    assert response.status_code == 404
    assert response.get_json()["error"] == "course not found"

# Test Case #6: Valid instructor session, valid course ID, invalid/cancel action
def test_generate_code_no_action(client):
    login_instructor(client)
    response = client.get('/instructor_dashboard')
    assert response.status_code == 200
    assert b"Instructor Dashboard" in response.data