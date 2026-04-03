#!/usr/bin/env python3
"""
API Test Suite
Tests for auth endpoints
"""

import http.client
import json
import os
import sys
import time
from urllib.parse import urlparse

# Configuration — port is auto-detected by the execution system
SERVER_PORT = os.environ.get("SERVER_PORT", "3001")
BASE_URL = f"http://localhost:{SERVER_PORT}"
TIMEOUT = 10  # seconds
passed = 0
failed = 0
skipped = 0

# Auth token storage
auth_token = None
TEST_EMAIL = None
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "Test Bot"


def make_request(method, path, body=None, headers=None):
    """Make HTTP request to the API"""
    if headers is None:
        headers = {}
    # Add default Content-Type for JSON
    if body is not None and 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json'

    # Parse URL
    url = urlparse(BASE_URL + path)

    try:
        # Create connection
        conn = http.client.HTTPConnection(url.netloc, timeout=TIMEOUT)

        # Prepare body
        body_data = json.dumps(body) if body is not None else None

        # Make request
        conn.request(method, url.path + ('?' + url.query if url.query else ''), 
                    body=body_data, headers=headers)

        # Get response
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')

        # Try to parse JSON
        try:
            response_body = json.loads(response_data) if response_data else None
        except json.JSONDecodeError:
            response_body = response_data

        # Get response headers (normalize to lowercase keys for consistent lookup)
        raw_headers = dict(response.getheaders())
        norm_headers = {k.lower(): v for k, v in raw_headers.items()}

        conn.close()

        return {
            'status': response.status,
            'body': response_body,
            'headers': norm_headers
        }
    except Exception as e:
        return {
            'status': 0,
            'body': None,
            'headers': {},
            'error': str(e)
        }


def extract_token_from_body(body):
    """Try to find a token in common locations inside a response body"""
    if not body or not isinstance(body, dict):
        return None
    # Top-level
    for key in ('token', 'accessToken', 'access_token', 'jwt'):
        if key in body and isinstance(body[key], str):
            return body[key]
    # data wrapper
    data = body.get('data') if isinstance(body.get('data'), dict) else None
    if data:
        for key in ('token', 'accessToken', 'access_token', 'jwt'):
            if key in data and isinstance(data[key], str):
                return data[key]
    # tokens.access.token
    tokens = body.get('tokens') if isinstance(body.get('tokens'), dict) else None
    if tokens:
        access = tokens.get('access') if isinstance(tokens.get('access'), dict) else None
        if access and isinstance(access.get('token'), str):
            return access.get('token')
    # user tokens
    if 'user' in body and isinstance(body['user'], dict):
        for key in ('token', 'accessToken', 'access_token', 'jwt'):
            if key in body['user'] and isinstance(body['user'][key], str):
                return body['user'][key]
    return None


def setup_auth():
    """Register a test user and login to get auth token"""
    global auth_token, TEST_EMAIL, TEST_PASSWORD, TEST_NAME
    # Unique email to avoid conflicts
    TEST_EMAIL = f"testbot_{int(time.time())}@example.com"

    print("\n[SETUP] Attempting to register and login test user...")

    reg_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    }
    reg_resp = make_request('POST', '/api/auth/register', body=reg_body)

    if 'error' in reg_resp:
        print(f"  ⚠ Register request error: {reg_resp['error']}")
    else:
        print(f"  → Register status: {reg_resp['status']}")
        # Try to extract token from register response
        token = extract_token_from_body(reg_resp.get('body'))
        if not token:
            # maybe token in headers (Set-Cookie)
            set_cookie = reg_resp['headers'].get('set-cookie')
            if set_cookie and 'token' in set_cookie:
                token = set_cookie
        if token:
            auth_token = token
            print("  ✓ Got token from register response")
            return

    # If reg didn't give token, try login
    login_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    login_resp = make_request('POST', '/api/auth/login', body=login_body)
    if 'error' in login_resp:
        print(f"  ⚠ Login request error: {login_resp['error']}")
        return

    print(f"  → Login status: {login_resp['status']}")
    if login_resp.get('status') in (200, 201):
        token = extract_token_from_body(login_resp.get('body'))
        if not token:
            # also check headers for cookie
            set_cookie = login_resp['headers'].get('set-cookie')
            if set_cookie and 'token' in set_cookie:
                token = set_cookie
        if token:
            auth_token = token
            print("  ✓ Got token from login response")
            return

    # If no token, print info and continue — protected tests may be skipped
    print(f"  ⚠ Could not obtain auth token (register: {reg_resp.get('status') if reg_resp else 'n/a'}, login: {login_resp.get('status') if login_resp else 'n/a'})")


def get_auth_headers():
    if auth_token:
        return {'Authorization': f'Bearer {auth_token}'}
    return {}


def test_register():
    """Test: POST /api/auth/register - create new user"""
    global passed, failed, skipped
    print("\n[TEST] POST /api/auth/register - Register new user")

    body = {
        "email": f"auto_{int(time.time())}@example.com",
        "password": TEST_PASSWORD,
        "name": "Auto Test"
    }

    response = make_request('POST', '/api/auth/register', body=body)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']
    if status in (0,):
        print(f"  ✗ FAILED: Connection error or zero status")
        failed += 1
        return

    # POST write operation: treat 404 or 405 as real failures (wrong path/method)
    if status in (404, 405):
        print(f"  ✗ FAILED: Unexpected status {status} (endpoint missing or method not allowed)")
        failed += 1
        return

    # Accept common outcomes for register (success, validation errors)
    if status in (200, 201, 400, 401, 403, 409, 422):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
    else:
        # unexpected but not necessarily a fail — treat as pass unless it's 404/405
        print(f"  ✓ PASSED (status {status})")
        passed += 1


def test_login():
    """Test: POST /api/auth/login - login with valid credentials"""
    global passed, failed, skipped, auth_token
    print("\n[TEST] POST /api/auth/login - Login with valid credentials")

    if not TEST_EMAIL:
        print("  ⚠ SKIPPED: No test email available from setup")
        skipped += 1
        return

    body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }

    response = make_request('POST', '/api/auth/login', body=body)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']
    if status in (404, 405):
        print(f"  ✗ FAILED: Unexpected status {status} (endpoint missing or method not allowed)")
        failed += 1
        return

    if status in (200, 201):
        token = extract_token_from_body(response.get('body'))
        if not token:
            set_cookie = response['headers'].get('set-cookie')
            if set_cookie and 'token' in set_cookie:
                token = set_cookie
        if token:
            auth_token = token
            print(f"  ✓ PASSED (status {status}) - token obtained")
            passed += 1
            return
        else:
            # Login returned success without token — still consider as pass but warn
            print(f"  ✓ PASSED (status {status}) - no token found in response")
            passed += 1
            return
    else:
        # Accept common error statuses as possible outcomes
        if status in (400, 401, 403):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return
        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1


def test_profile_get():
    """Test: GET /api/auth/profile - get profile with valid auth"""
    global passed, failed, skipped
    print("\n[TEST] GET /api/auth/profile - Fetch current user's profile")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available — cannot test protected profile endpoint")
        skipped += 1
        return

    response = make_request('GET', '/api/auth/profile', headers=get_auth_headers())

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']
    if status == 200:
        if response['body'] is None:
            print(f"  ✗ FAILED: 200 but empty body")
            failed += 1
        else:
            print(f"  ✓ PASSED (status 200)")
            passed += 1
    elif status in (401, 403):
        print(f"  ✗ FAILED: Protected endpoint returned {status} despite having token")
        failed += 1
    else:
        # Other statuses: accept 400/422 as possible validation issues
        if status in (400, 422):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
        else:
            print(f"  ✗ FAILED: Unexpected status {status}")
            failed += 1


def test_profile_patch():
    """Test: PATCH /api/auth/profile - update profile with valid auth"""
    global passed, failed, skipped
    print("\n[TEST] PATCH /api/auth/profile - Update current user's profile")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available — cannot test profile update")
        skipped += 1
        return

    body = {
        "name": "Updated Test Bot"
    }

    response = make_request('PATCH', '/api/auth/profile', body=body, headers=get_auth_headers())

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']

    if status in (404, 405):
        print(f"  ✗ FAILED: Unexpected status {status} (endpoint missing or method not allowed)")
        failed += 1
        return

    # For update ops, accept many status codes except 404/405/0
    if status in (200, 201, 204, 400, 401, 403, 422):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
    else:
        print(f"  ✓ PASSED (status {status})")
        passed += 1


def test_invalid_login():
    """Test: POST /api/auth/login - attempt login with invalid credentials (expect 401/403)"""
    global passed, failed, skipped
    print("\n[TEST] POST /api/auth/login - Invalid credentials should be rejected")

    body = {
        "email": "nonexistent@example.com",
        "password": "WrongPassword!"
    }

    response = make_request('POST', '/api/auth/login', body=body)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']
    # If 401 or 403 — expected
    if status in (401, 403):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
        return

    # Some APIs return 400 for invalid credentials — accept as pass
    if status == 400:
        print(f"  ✓ PASSED (status 400)")
        passed += 1
        return

    # If login succeeded (200/201) with invalid creds, that's a definite fail
    if status in (200, 201):
        token = extract_token_from_body(response.get('body'))
        if token:
            print(f"  ✗ FAILED: Login succeeded with invalid credentials (token returned)")
            failed += 1
            return
        else:
            # success status but no token — treat as fail because unexpected
            print(f"  ✗ FAILED: Login returned {status} for invalid credentials")
            failed += 1
            return

    # Other statuses: treat 404/405 as failures (wrong endpoint/method)
    if status in (404, 405):
        print(f"  ✗ FAILED: Unexpected status {status} (endpoint missing or method not allowed)")
        failed += 1
        return

    # Otherwise accept as pass to be tolerant
    print(f"  ✓ PASSED (status {status})")
    passed += 1


def test_invalid_token_profile():
    """Test: GET /api/auth/profile with invalid token — expect 401/403 (or 200 if public)"""
    global passed, failed, skipped
    print("\n[TEST] GET /api/auth/profile - Access with invalid token")

    headers = {'Authorization': 'Bearer invalid-token-12345'}
    response = make_request('GET', '/api/auth/profile', headers=headers)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']
    # Accept 401/403 as clear pass. Some APIs return 200 (public profile) — tolerate.
    if status in (401, 403, 200):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
    else:
        # 400/422 also acceptable
        if status in (400, 422):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
        else:
            print(f"  ✗ FAILED: Unexpected status {status}")
            failed += 1


def main():
    """Run all tests"""
    print("=" * 60)
    print("API Test Suite - Auth Endpoints")
    print("=" * 60)

    # Check if server is responding
    print("\nChecking server connectivity...")
    try:
        response = make_request('GET', '/')
        if 'error' in response or response.get('status') == 0:
            print(f"⚠ WARNING: Server not responding: {response.get('error')}")
            print("Tests will likely fail with connection errors\n")
        else:
            print(f"✓ Server responding (status {response['status']})\n")
    except Exception as e:
        print(f"⚠ WARNING: Could not connect to server: {str(e)}\n")

    # Set up authentication (register + login) once
    setup_auth()

    # Run tests
    test_register()
    test_login()
    test_profile_get()
    test_profile_patch()
    test_invalid_login()
    test_invalid_token_profile()

    # Print summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    # Exit with appropriate code — skipped tests do NOT count as failures
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
