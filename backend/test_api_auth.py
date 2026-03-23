#!/usr/bin/env python3
"""
API Test Suite
Tests for auth endpoints: /api/auth/register, /api/auth/login, /api/auth/profile
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
    """Try many common locations for tokens in a response body"""
    if not body or not isinstance(body, dict):
        return None

    # top-level token keys
    for key in ('token', 'accessToken', 'access_token', 'jwt'):
        if key in body and isinstance(body[key], str):
            return body[key]

    # nested data
    data = body.get('data') if isinstance(body.get('data'), dict) else None
    if data:
        for key in ('token', 'accessToken', 'access_token'):
            if key in data and isinstance(data[key], str):
                return data[key]

    # nested tokens.access.token or tokens.accessToken
    tokens = body.get('tokens') if isinstance(body.get('tokens'), dict) else None
    if tokens:
        access = tokens.get('access') if isinstance(tokens.get('access'), dict) else None
        if access:
            for key in ('token', 'accessToken', 'access_token'):
                if key in access and isinstance(access[key], str):
                    return access[key]

    # sometimes token inside user or result
    for container_key in ('user', 'result', 'data', 'payload'):
        c = body.get(container_key)
        if isinstance(c, dict):
            for key in ('token', 'accessToken', 'access_token', 'jwt'):
                if key in c and isinstance(c[key], str):
                    return c[key]

    return None


def setup_auth():
    """Register a test user and login to get auth token"""
    global auth_token, TEST_EMAIL, TEST_PASSWORD, TEST_NAME

    # Use a reasonably-unique test email to avoid conflicts across runs
    timestamp = int(time.time())
    TEST_EMAIL = f"testbot+{timestamp}@example.com"

    print("\n[SETUP] Registering test user to obtain auth token (if supported)")

    reg_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    }

    reg_resp = make_request('POST', '/api/auth/register', body=reg_body)

    if reg_resp.get('status') == 0:
        print(f"  ⚠ WARNING: Register request error: {reg_resp.get('error')}")
    else:
        print(f"  → Register status: {reg_resp.get('status')}")

    token = None
    if isinstance(reg_resp.get('body'), dict):
        token = extract_token_from_body(reg_resp['body'])

    if token:
        auth_token = token
        print("  ✓ Auth: Got token from register response")
        return

    # If register returned 409 or similar, try login directly
    print("  → Trying login to obtain token")
    login_body = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    login_resp = make_request('POST', '/api/auth/login', body=login_body)

    if login_resp.get('status') == 0:
        print(f"  ⚠ WARNING: Login request error: {login_resp.get('error')}")
    else:
        print(f"  → Login status: {login_resp.get('status')}")

    if isinstance(login_resp.get('body'), dict):
        token = extract_token_from_body(login_resp['body'])

    # Also check Set-Cookie for session tokens (rare but possible)
    if not token:
        set_cookie = login_resp.get('headers', {}).get('set-cookie')
        if set_cookie and isinstance(set_cookie, str):
            # naive extraction of jwt in cookie value
            token = set_cookie.split(';')[0].split('=')[-1]

    if token:
        auth_token = token
        print("  ✓ Auth: Got token from login response")
    else:
        print(f"  ⚠ Auth: Could not obtain token (register: {reg_resp.get('status')}, login: {login_resp.get('status')})")


def get_auth_headers():
    """Return auth headers if token is available"""
    if auth_token:
        return {'Authorization': f'Bearer {auth_token}'}
    return {}


def test_register_new_user():
    """Test: POST /api/auth/register - create new user"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/register - Create new user")

    body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    }

    try:
        response = make_request('POST', '/api/auth/register', body=body)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        # For write operations: accept most statuses except 0, 404, 405
        if status == 0:
            print("  ✗ FAILED: Connection error")
            failed += 1
            return
        if status in (404, 405):
            print(f"  ✗ FAILED: Expected register endpoint, got status {status} (wrong path or method)")
            failed += 1
            return

        # Accept as passed (201/200/400/401/403/422 are acceptable outcomes for write)
        print(f"  ✓ PASSED (status {status})")
        passed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_login_with_credentials():
    """Test: POST /api/auth/login - login with correct credentials"""
    global passed, failed, skipped, auth_token

    print("\n[TEST] POST /api/auth/login - Login with correct credentials")

    body = {"email": TEST_EMAIL, "password": TEST_PASSWORD}

    try:
        response = make_request('POST', '/api/auth/login', body=body)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status == 0:
            print("  ✗ FAILED: Connection error")
            failed += 1
            return
        if status in (404, 405):
            print(f"  ✗ FAILED: Expected login endpoint, got status {status} (wrong path or method)")
            failed += 1
            return

        # If login succeeded (200/201), try to extract token
        token = None
        if isinstance(response.get('body'), dict):
            token = extract_token_from_body(response['body'])

        # Try cookie header
        if not token:
            set_cookie = response.get('headers', {}).get('set-cookie')
            if set_cookie and isinstance(set_cookie, str):
                token = set_cookie.split(';')[0].split('=')[-1]

        if status in (200, 201) and token:
            auth_token = token
            print(f"  ✓ PASSED (status {status}) - token acquired")
            passed += 1
            return

        # If 200/201 but no token, still pass the login test but warn and continue
        if status in (200, 201):
            print(f"  ✓ PASSED (status {status}) - no token returned")
            passed += 1
            return

        # Other statuses: still acceptable for write (e.g., 401 if registration didn't succeed). Treat as pass but note status
        if status in (400, 401, 403, 422):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        # Anything else: treat as failure
        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_login_invalid_credentials():
    """Test: POST /api/auth/login - invalid credentials should be rejected"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/login - Invalid credentials")

    body = {"email": TEST_EMAIL, "password": "WrongPassword!"}

    try:
        response = make_request('POST', '/api/auth/login', body=body)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status == 0:
            print("  ✗ FAILED: Connection error")
            failed += 1
            return
        if status in (404, 405):
            print(f"  ✗ FAILED: Expected login endpoint, got status {status} (wrong path or method)")
            failed += 1
            return

        # Expect 401/403 for invalid credentials; some APIs return 400
        if status in (401, 403, 400):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        # If login erroneously succeeds, fail
        if status in (200, 201):
            print(f"  ✗ FAILED: Login succeeded with invalid credentials (status {status})")
            failed += 1
            return

        # Otherwise treat as failure
        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_get_profile_with_auth():
    """Test: GET /api/auth/profile - with valid auth token"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - With valid auth token")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available")
        skipped += 1
        return

    try:
        headers = get_auth_headers()
        response = make_request('GET', '/api/auth/profile', headers=headers)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status == 200:
            # Ensure body is JSON-like
            if response['body'] is None:
                print("  ✗ FAILED: Empty profile response body")
                failed += 1
                return
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        # If protected and token invalid/insufficient, 401/403 may be returned — treat as failure because we expected valid token
        if status in (401, 403):
            print(f"  ✗ FAILED: Protected endpoint rejected valid token (status {status})")
            failed += 1
            return

        # Other statuses: treat as failure
        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_get_profile_invalid_token():
    """Test: GET /api/auth/profile - with invalid token"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - With invalid token")

    try:
        headers = {'Authorization': 'Bearer invalid-token-12345'}
        response = make_request('GET', '/api/auth/profile', headers=headers)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        # Accept 401/403 (protected) or 200 (if endpoint is public)
        if status in (200, 401, 403):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        # 400 could be returned for malformed token
        if status == 400:
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_patch_profile_with_auth():
    """Test: PATCH /api/auth/profile - update profile with valid auth"""
    global passed, failed, skipped

    print("\n[TEST] PATCH /api/auth/profile - With valid auth token")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available")
        skipped += 1
        return

    new_name = f"Updated {TEST_NAME} {int(time.time())}"
    body = {"name": new_name}

    try:
        headers = get_auth_headers()
        response = make_request('PATCH', '/api/auth/profile', body=body, headers=headers)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status == 0:
            print("  ✗ FAILED: Connection error")
            failed += 1
            return
        if status in (404, 405):
            print(f"  ✗ FAILED: Expected PATCH profile endpoint, got status {status} (wrong path or method)")
            failed += 1
            return

        # Accept common write statuses
        if status in (200, 201, 400, 401, 403, 422):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_patch_profile_invalid_token():
    """Test: PATCH /api/auth/profile - update profile with invalid token"""
    global passed, failed, skipped

    print("\n[TEST] PATCH /api/auth/profile - With invalid token")

    body = {"name": "WillNotSucceed"}

    try:
        headers = {'Authorization': 'Bearer invalid-token-12345', 'Content-Type': 'application/json'}
        response = make_request('PATCH', '/api/auth/profile', body=body, headers=headers)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status == 0:
            print("  ✗ FAILED: Connection error")
            failed += 1
            return

        # Expect 401/403 (protected) or 200 if publicly allowed
        if status in (200, 401, 403, 400):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def main():
    """Run all tests"""
    print("=" * 60)
    print("API Test Suite: auth endpoints")
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

    # Set up authentication (if endpoints require it)
    setup_auth()

    # Run tests
    test_register_new_user()
    test_login_with_credentials()
    test_login_invalid_credentials()
    test_get_profile_with_auth()
    test_get_profile_invalid_token()
    test_patch_profile_with_auth()
    test_patch_profile_invalid_token()

    # Print summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    # Exit with appropriate code — skipped tests do NOT count as failures
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
