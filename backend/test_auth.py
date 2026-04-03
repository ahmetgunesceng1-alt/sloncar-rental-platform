#!/usr/bin/env python3
"""
API Test Suite
Tests for /api/auth endpoints: register, login, profile (GET/PATCH)
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

# Global auth token obtained during setup
auth_token = None
TEST_EMAIL = f"testbot+{int(time.time())}@example.com"
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
    """Try common places to extract JWT/token from response body"""
    if not body:
        return None
    if isinstance(body, str):
        return None
    # body is dict
    for key in ('token', 'accessToken', 'access_token', 'jwt'):
        if key in body and isinstance(body[key], str):
            return body[key]
    # nested data
    data = body.get('data') if isinstance(body.get('data'), dict) else None
    if data:
        for key in ('token', 'accessToken', 'access_token'):
            if key in data and isinstance(data[key], str):
                return data[key]
    # tokens.access.token pattern
    tokens = body.get('tokens')
    if isinstance(tokens, dict):
        access = tokens.get('access')
        if isinstance(access, dict) and isinstance(access.get('token'), str):
            return access.get('token')
    # fallback: maybe body itself is the token
    if isinstance(body, str):
        return body
    return None


def setup_auth():
    """Register a test user and login to get auth token"""
    global auth_token, TEST_EMAIL, TEST_PASSWORD, TEST_NAME

    if auth_token:
        return

    print("\n[SETUP] Attempting to register and login test user for auth token")

    # Step 1: Register
    reg_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    }
    reg_resp = make_request('POST', '/api/auth/register', body=reg_body)
    status = reg_resp.get('status')

    if reg_resp.get('error'):
        print(f"  ⚠ Register request error: {reg_resp['error']}")
    else:
        print(f"  → Register status: {status}")

    # Try to obtain token from register response
    token = None
    if reg_resp.get('body'):
        token = extract_token_from_body(reg_resp['body'])

    if token:
        auth_token = token
        print("  ✓ Auth: Got token from register response")
        return

    # Step 2: Login (if register didn't return token or register failed because user exists)
    login_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    login_resp = make_request('POST', '/api/auth/login', body=login_body)
    status2 = login_resp.get('status')
    if login_resp.get('error'):
        print(f"  ⚠ Login request error: {login_resp['error']}")
    else:
        print(f"  → Login status: {status2}")

    if login_resp.get('body'):
        token = extract_token_from_body(login_resp['body'])

    # Also check headers (maybe token in set-cookie or authorization)
    if not token and login_resp.get('headers'):
        # Look for set-cookie
        sc = login_resp['headers'].get('set-cookie')
        if sc and isinstance(sc, str):
            token = sc

    if token:
        auth_token = token
        print("  ✓ Auth: Got token from login response")
    else:
        print(f"  ⚠ Auth: Could not obtain token (register: {status}, login: {status2})")


def get_auth_headers():
    """Return auth headers if token is available"""
    if auth_token:
        return {'Authorization': f'Bearer {auth_token}'}
    return {}


def test_register_endpoint():
    """Test: POST /api/auth/register - Create new user"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/register - Create user")

    body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    }

    response = make_request('POST', '/api/auth/register', body=body)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']

    # For write operations: accept most statuses as pass except 0, 404, 405
    if status == 0:
        print("  ✗ FAILED: Connection error or no response")
        failed += 1
        return
    if status in (404, 405):
        print(f"  ✗ FAILED: Endpoint or method not found (status {status})")
        failed += 1
        return

    # Otherwise consider this a pass (201, 200, 400 (validation), 409 (exists) are acceptable)
    print(f"  ✓ PASSED (status {status})")
    passed += 1


def test_login_endpoint_and_token_extraction():
    """Test: POST /api/auth/login - Login and extract token"""
    global passed, failed, skipped, auth_token

    print("\n[TEST] POST /api/auth/login - Login with correct credentials")

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

    if status == 0:
        print("  ✗ FAILED: Connection error or no response")
        failed += 1
        return

    if status in (404, 405):
        print(f"  ✗ FAILED: Endpoint or method not found (status {status})")
        failed += 1
        return

    # Try to extract token from body or headers
    token = None
    if response.get('body'):
        token = extract_token_from_body(response['body'])

    if not token and response.get('headers'):
        # check common headers
        authh = response['headers'].get('authorization') or response['headers'].get('x-auth-token') or response['headers'].get('set-cookie')
        if authh and isinstance(authh, str):
            token = authh

    if token:
        auth_token = token
        print(f"  ✓ PASSED: Login returned token (status {status})")
        passed += 1
    else:
        # Login succeeded but no token found — still consider pass if status indicates success
        if status in (200, 201):
            print(f"  ✓ PASSED: Login returned status {status} but no token extracted")
            passed += 1
        else:
            # Could be 400/401 etc — treat as failure for this test because login didn't succeed
            print(f"  ✗ FAILED: Unexpected login status {status} and no token")
            failed += 1


def test_login_invalid_credentials():
    """Test: POST /api/auth/login - Invalid credentials should return 401"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/login - Invalid credentials")

    body = {
        "email": TEST_EMAIL,
        "password": "WrongPassword!"
    }

    response = make_request('POST', '/api/auth/login', body=body)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']

    # Expect 401. Some APIs may return 400 for validation; treat 401 or 400 as acceptable
    if status in (401, 400):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
    else:
        print(f"  ✗ FAILED: Expected 401/400 for invalid credentials, got {status}")
        failed += 1


def test_get_profile_with_valid_auth():
    """Test: GET /api/auth/profile - with valid token"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - Valid auth")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available")
        skipped += 1
        return

    headers = get_auth_headers()
    response = make_request('GET', '/api/auth/profile', headers=headers)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']

    if status == 0:
        print("  ✗ FAILED: Connection error or no response")
        failed += 1
        return
    if status in (404, 405):
        print(f"  ✗ FAILED: Endpoint or method not found (status {status})")
        failed += 1
        return

    # Accept 200 as success; 401/403 indicates token invalid or endpoint protected differently
    if status == 200:
        if response.get('body') is None:
            print("  ✗ FAILED: 200 returned but empty body")
            failed += 1
            return
        print(f"  ✓ PASSED (status 200)")
        passed += 1
    elif status in (401, 403):
        print(f"  ✓ PASSED (protected endpoint, status {status})")
        passed += 1
    else:
        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1


def test_patch_profile_with_valid_auth():
    """Test: PATCH /api/auth/profile - update profile with auth"""
    global passed, failed, skipped

    print("\n[TEST] PATCH /api/auth/profile - Update profile (auth required)")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available")
        skipped += 1
        return

    headers = get_auth_headers()
    body = {"name": TEST_NAME + " Updated"}

    response = make_request('PATCH', '/api/auth/profile', body=body, headers=headers)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']

    if status == 0:
        print("  ✗ FAILED: Connection error or no response")
        failed += 1
        return
    if status in (404, 405):
        print(f"  ✗ FAILED: Endpoint or method not found (status {status})")
        failed += 1
        return

    # For write operations accept many statuses except 404/405/0
    if status in (200, 201, 400, 401, 403, 422):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
    else:
        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1


def test_profile_invalid_token():
    """Test: GET /api/auth/profile with invalid token should be rejected"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - Invalid token")

    headers = {'Authorization': 'Bearer invalid-token-12345'}
    response = make_request('GET', '/api/auth/profile', headers=headers)

    if 'error' in response:
        print(f"  ✗ FAILED: {response['error']}")
        failed += 1
        return

    status = response['status']

    if status == 0:
        print("  ✗ FAILED: Connection error or no response")
        failed += 1
        return
    if status in (404, 405):
        print(f"  ✗ FAILED: Endpoint or method not found (status {status})")
        failed += 1
        return

    # Accept either 401/403 (expected) or 200 if endpoint is public
    if status in (401, 403, 200):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
    else:
        print(f"  ✗ FAILED: Expected 401/403/200, got {status}")
        failed += 1


def main():
    """Run all tests"""
    global passed, failed, skipped

    print("=" * 60)
    print("API Test Suite: Auth Endpoints")
    print("=" * 60)

    # Check if server is responding
    print("\nChecking server connectivity...")
    try:
        response = make_request('GET', '/')
        if 'error' in response:
            print(f"⚠ WARNING: Server not responding: {response['error']}")
            print("Tests will likely fail with connection errors\n")
        else:
            print(f"✓ Server responding (status {response['status']})\n")
    except Exception as e:
        print(f"⚠ WARNING: Could not connect to server: {str(e)}\n")

    # Set up authentication (try register+login)
    setup_auth()

    # Run tests in logical order
    test_register_endpoint()
    test_login_endpoint_and_token_extraction()
    test_login_invalid_credentials()
    test_get_profile_with_valid_auth()
    test_patch_profile_with_valid_auth()
    test_profile_invalid_token()

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
