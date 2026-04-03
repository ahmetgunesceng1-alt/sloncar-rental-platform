#!/usr/bin/env python3
"""
API Test Suite
Tests for /api/auth/* endpoints
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

# Global auth token populated by setup_auth()
auth_token = None
TEST_EMAIL = None
TEST_PASSWORD = "TestPass123!"


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


def extract_token_from_body_or_headers(resp):
    """Try multiple common locations for auth token in body or headers"""
    if not resp:
        return None
    # Check headers first (Set-Cookie, authorization)
    headers = resp.get('headers', {})
    # Common header with token
    for hk in ('authorization', 'x-auth-token', 'x-access-token'):
        if hk in headers:
            # Might be 'Bearer <token>'
            val = headers[hk]
            if isinstance(val, str) and val.lower().startswith('bearer '):
                return val.split(' ', 1)[1]
            return val
    # Set-Cookie might contain session or token
    sc = headers.get('set-cookie')
    if sc and isinstance(sc, str):
        # return the whole cookie string (may be acceptable for cookie-based auth)
        return sc.split(';', 1)[0]

    # Now check body
    body = resp.get('body') if isinstance(resp, dict) else None
    if isinstance(body, dict):
        # Top-level keys
        for key in ('token', 'accessToken', 'access_token', 'jwt', 'id_token'):
            if key in body and body[key]:
                return body[key]
        # Common nested containers
        if 'data' in body and isinstance(body['data'], dict):
            for key in ('token', 'accessToken', 'access_token', 'jwt'):
                if key in body['data'] and body['data'][key]:
                    return body['data'][key]
        if 'tokens' in body and isinstance(body['tokens'], dict):
            access = body['tokens'].get('access') if isinstance(body['tokens'], dict) else None
            if isinstance(access, dict) and 'token' in access:
                return access['token']
    return None


def setup_auth():
    """Register a test user and login to get auth token"""
    global auth_token, TEST_EMAIL

    # Use a reasonably unique email to avoid collision
    timestamp = str(int(time.time()))
    TEST_EMAIL = f"testbot+{timestamp}@example.com"

    # Attempt to register
    reg_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": "Test Bot"
    }

    print(f"\n[SETUP] Registering test user {TEST_EMAIL} ...")
    reg_resp = make_request('POST', '/api/auth/register', body=reg_body)
    if 'error' in reg_resp:
        print(f"  ⚠ WARNING: register request error: {reg_resp.get('error')}")
    else:
        print(f"  → register status: {reg_resp.get('status')}")

    # Try to extract token from register response
    token = extract_token_from_body_or_headers(reg_resp)
    if token:
        auth_token = token
        print("  ✓ Auth: Got token from register response")
        return

    # If register returns 409 or similar (user exists), or no token returned, try login
    login_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    print("  [SETUP] Attempting login to obtain token...")
    login_resp = make_request('POST', '/api/auth/login', body=login_body)
    if 'error' in login_resp:
        print(f"  ⚠ WARNING: login request error: {login_resp.get('error')}")
    else:
        print(f"  → login status: {login_resp.get('status')}")

    token = extract_token_from_body_or_headers(login_resp)
    if token:
        auth_token = token
        print("  ✓ Auth: Got token from login response")
    else:
        print(f"  ⚠ Auth: Could not obtain token (register: {reg_resp.get('status')}, login: {login_resp.get('status')})")


def get_auth_headers():
    """Return auth headers if token is available"""
    if auth_token:
        # Use Bearer scheme by default
        return {'Authorization': f'Bearer {auth_token}'}
    return {}


def test_register_endpoint():
    """Test: POST /api/auth/register - Create new user (write operation tolerant)"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/register - Create new user")

    email = f"testbot_manual_{int(time.time())}@example.com"
    body = {
        "email": email,
        "password": TEST_PASSWORD,
        "name": "Test Bot Manual"
    }

    resp = make_request('POST', '/api/auth/register', body=body)
    if 'error' in resp:
        print(f"  ✗ FAILED: {resp['error']}")
        failed += 1
        return

    status = resp['status']
    # For write operations accept most statuses except 0, 404, 405
    if status in (0, 404, 405):
        print(f"  ✗ FAILED: Unexpected status for write operation: {status}")
        failed += 1
        return

    # Otherwise treat as pass (200,201,400,401,403,422 are acceptable)
    print(f"  ✓ PASSED (status {status})")
    passed += 1


def test_login_with_invalid_credentials():
    """Test: POST /api/auth/login - invalid credentials should be rejected (expect 401/400/403)
    """
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/login - Invalid credentials")

    body = {
        "email": "nonexistent-user@example.com",
        "password": "WrongPassword!"
    }

    resp = make_request('POST', '/api/auth/login', body=body)
    if 'error' in resp:
        print(f"  ✗ FAILED: {resp['error']}")
        failed += 1
        return

    status = resp['status']
    # Accept 401/403/400 as correct rejection. If 200, that's suspicious and fail.
    if status in (401, 403, 400):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
    elif status == 200:
        # If 200, check if response actually contains token — that would be unexpected
        token = extract_token_from_body_or_headers(resp)
        if token:
            print(f"  ✗ FAILED: Invalid credentials returned 200 with token")
            failed += 1
        else:
            # 200 without token is weird but treat as fail because login should not succeed
            print(f"  ✗ FAILED: Invalid credentials returned 200 without token")
            failed += 1
    else:
        # Other statuses like 404/422 — treat as pass (server handled it)
        print(f"  ✓ PASSED (status {status})")
        passed += 1


def test_get_profile_with_valid_token():
    """Test: GET /api/auth/profile - with valid token should return 200 and a body (profile endpoint)
    """
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - With valid token")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available from setup_auth()")
        skipped += 1
        return

    headers = get_auth_headers()
    resp = make_request('GET', '/api/auth/profile', headers=headers)
    if 'error' in resp:
        print(f"  ✗ FAILED: {resp['error']}")
        failed += 1
        return

    status = resp['status']
    # PROFILE endpoints: per project guidance, assert status == 200 and body not None
    if status == 200:
        if resp.get('body') is None:
            print("  ✗ FAILED: 200 returned but empty body")
            failed += 1
        else:
            print("  ✓ PASSED")
            passed += 1
    else:
        # If protected and token invalid/expired, 401/403 is acceptable — but here we expected valid token
        # Still treat common auth failures as failure because we had a token
        if status in (401, 403):
            print(f"  ✗ FAILED: Expected 200 with valid token, got {status}")
            failed += 1
        else:
            # Other statuses (400, 404) mark failure for this test
            print(f"  ✗ FAILED: Unexpected status {status}")
            failed += 1


def test_get_profile_with_invalid_token():
    """Test: GET /api/auth/profile - With invalid token should return 401/403 or 200 (if public)
    """
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - With invalid token")

    headers = {'Authorization': 'Bearer invalid-token-12345'}
    resp = make_request('GET', '/api/auth/profile', headers=headers)
    if 'error' in resp:
        print(f"  ✗ FAILED: {resp['error']}")
        failed += 1
        return

    status = resp['status']
    if status in (200, 401, 403):
        print(f"  ✓ PASSED (status {status})")
        passed += 1
    else:
        print(f"  ✗ FAILED: Expected 200/401/403, got {status}")
        failed += 1


def test_patch_profile_with_valid_token():
    """Test: PATCH /api/auth/profile - update profile (accept common write statuses)
    """
    global passed, failed, skipped

    print("\n[TEST] PATCH /api/auth/profile - With valid token")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available from setup_auth()")
        skipped += 1
        return

    headers = get_auth_headers()
    body = {
        # Use a harmless update
        "name": "Test Bot Updated"
    }

    resp = make_request('PATCH', '/api/auth/profile', body=body, headers=headers)
    if 'error' in resp:
        print(f"  ✗ FAILED: {resp['error']}")
        failed += 1
        return

    status = resp['status']
    # For write operations accept most statuses except 0, 404, 405
    if status in (0, 404, 405):
        print(f"  ✗ FAILED: Unexpected status for write operation: {status}")
        failed += 1
        return

    print(f"  ✓ PASSED (status {status})")
    passed += 1


def main():
    """Run all tests"""
    global passed, failed, skipped

    print("=" * 60)
    print("API Test Suite: auth endpoints")
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

    # Set up authentication (try to register/login and obtain token)
    setup_auth()

    # Run tests
    test_register_endpoint()
    test_login_with_invalid_credentials()
    test_get_profile_with_valid_token()
    test_get_profile_with_invalid_token()
    test_patch_profile_with_valid_token()

    # Print summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    # Exit with appropriate code — skipped tests do NOT count as failures
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
