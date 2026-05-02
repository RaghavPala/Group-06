import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Test Case #1: Valid login (Student)
def test_valid_login(client):
    response = client.post('/login', data={"netid": "dal123456", "password": "password1234*"}, follow_redirects=True)
    assert b"Student Dashboard" in response.data

# Test Case #2: Invalid password
def test_invalid_password(client):
    response = client.post('/login', data={"netid": "dal123456", "password": "wrongpassword"})
    assert b"Incorrect password" in response.data

# Test Case #3: Invalid NetID start number
def test_invalid_netid_start_number(client):
    response = client.post('/login', data={"netid": "1abc", "password": "password1234*"})
    assert b"Invalid NetID format" in response.data

# Test Case #4: NetID contains special character
def test_netid_special_character(client):
    response = client.post('/login', data={"netid": "dal@123", "password": "password1234*"})
    assert b"Invalid NetID format" in response.data

# Test Case #5: Password contains space
def test_password_with_space(client):
    response = client.post('/login', data={"netid": "dal123456", "password": "pass 1234*"})
    assert b"Incorrect password" in response.data

# Test Case #6: No input provided
def test_no_input(client):
    response = client.post('/login', data={"netid": "", "password": ""})
    assert b"Invalid NetID format" in response.data

# Test Case #7: Valid login (Instructor)
def test_instructor_login(client):
    response = client.post('/login', data={"netid": "proftest", "password": "profpass1*"}, follow_redirects=True)
    assert b"Instructor Dashboard" in response.data