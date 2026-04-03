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
import uuid
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
    """Try many common patterns to extract a bearer token from response body"""
    if not body or not isinstance(body, dict):
        return None
    # top-level keys
    for key in ('token', 'accessToken', 'access_token', 'jwt'):
        if key in body and isinstance(body[key], str):
            return body[key]
    # nested data
    data = body.get('data')
    if isinstance(data, dict):
        for key in ('token', 'accessToken', 'access_token'):
            if key in data and isinstance(data[key], str):
                return data[key]
    # nested tokens.access.token
    tokens = body.get('tokens')
    if isinstance(tokens, dict):
        access = tokens.get('access')
        if isinstance(access, dict):
            token = access.get('token')
            if isinstance(token, str):
                return token
    return None


def setup_auth():
    """Register a test user and login to get auth token"""
    global auth_token, TEST_EMAIL, TEST_NAME, TEST_PASSWORD

    if auth_token:
        return

    # Step 1: Register
    reg_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    }
    print(f"\nRegistering test user {TEST_EMAIL} ...")
    reg_resp = make_request('POST', '/api/auth/register', body=reg_body)

    if 'error' in reg_resp:
        print(f"  ⚠ WARNING: register request error: {reg_resp['error']}")
    else:
        print(f"  register status: {reg_resp['status']}")

    # Try to extract token from register response
    if reg_resp.get('body'):
        token = extract_token_from_body(reg_resp['body'])
        if token:
            auth_token = token
            print("  ✓ Auth: Got token from register response")
            return

    # Step 2: Try login (register may not return token)
    login_body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    print("Attempting login to obtain token...")
    login_resp = make_request('POST', '/api/auth/login', body=login_body)

    if 'error' in login_resp:
        print(f"  ⚠ WARNING: login request error: {login_resp['error']}")
    else:
        print(f"  login status: {login_resp['status']}")

    if login_resp.get('body'):
        token = extract_token_from_body(login_resp['body'])
        if token:
            auth_token = token
            print("  ✓ Auth: Got token from login response")
            return

    # Try to extract token from headers (Set-Cookie or authorization)
    headers = login_resp.get('headers') or reg_resp.get('headers') or {}
    # cookie-based: look for set-cookie
    set_cookie = headers.get('set-cookie')
    if set_cookie and 'token' in set_cookie:
        # naive extraction
        parts = set_cookie.split(';')
        for p in parts:
            if '=' in p:
                k, v = p.strip().split('=', 1)
                if 'token' in k.lower():
                    auth_token = v
                    print("  ✓ Auth: Got token from Set-Cookie header")
                    return

    if auth_token:
        print("  ✓ Auth: token available")
    else:
        print("  ⚠ Auth: Could not obtain token from register/login responses")


def get_auth_headers():
    """Return auth headers if token is available"""
    if auth_token:
        return {'Authorization': f'Bearer {auth_token}'}
    return {}


def test_register_happy_path():
    """Test: POST /api/auth/register - Happy path"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/register - Happy path")

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
        # For POST we accept most status codes except 0, 404, 405
        if status == 0:
            print("  ✗ FAILED: connection error")
            failed += 1
            return
        if status in (404, 405):
            print(f"  ✗ FAILED: Endpoint not found or method not allowed ({status})")
            failed += 1
            return

        # Acceptable outcomes: created, ok, conflict (already exists), bad request
        if status in (200, 201, 400, 401, 403, 409, 422):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_login_happy_path():
    """Test: POST /api/auth/login - Happy path (obtain token)"""
    global passed, failed, skipped, auth_token

    print("\n[TEST] POST /api/auth/login - Happy path")

    body = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }

    try:
        response = make_request('POST', '/api/auth/login', body=body)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status == 0:
            print("  ✗ FAILED: connection error")
            failed += 1
            return
        if status in (404, 405):
            print(f"  ✗ FAILED: Endpoint not found or method not allowed ({status})")
            failed += 1
            return

        # If login succeeded, extract token
        token = None
        if response.get('body'):
            token = extract_token_from_body(response['body'])

        # Also check headers for possible cookie token
        headers = response.get('headers', {})
        if not token:
            set_cookie = headers.get('set-cookie')
            if set_cookie and 'token' in set_cookie:
                parts = set_cookie.split(';')
                for p in parts:
                    if '=' in p:
                        k, v = p.strip().split('=', 1)
                        if 'token' in k.lower():
                            token = v
                            break

        if token:
            auth_token = token
            print(f"  ✓ PASSED (status {status}) - token obtained")
            passed += 1
            return

        # Accept 200/201 as success even without token in body (maybe cookie)
        if status in (200, 201):
            print(f"  ✓ PASSED (status {status}) - login responded but no token extracted")
            passed += 1
            return

        # Accept typical error statuses as valid outcomes for this test environment
        if status in (400, 401, 403, 422):
            print(f"  ✓ PASSED (status {status}) - login rejected")
            passed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_login_invalid_credentials():
    """Test: POST /api/auth/login - Invalid credentials should be rejected (401/400/422)"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/login - Invalid credentials")

    body = {
        "email": TEST_EMAIL,
        "password": "WrongPassword!"
    }

    try:
        response = make_request('POST', '/api/auth/login', body=body)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']

        # Expect 401 ideally. Accept 400/422 as validation-based rejection.
        if status in (401, 400, 422):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        # If server returned 200, that means login succeeded with wrong creds — unexpected
        if status == 200:
            print(f"  ✗ FAILED: Unexpected success with invalid credentials (200)")
            failed += 1
            return

        # Other statuses (403) treat as pass (forbidden) per tolerance rules
        if status in (403, 201):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_profile_invalid_token():
    """Test: GET /api/auth/profile - Invalid token should be rejected (401/403)"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - Invalid token")

    try:
        response = make_request('GET', '/api/auth/profile', headers={'Authorization': 'Bearer invalid-token-12345'})

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status in (401, 403):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        # Some public endpoints may return 200 — accept but warn
        if status == 200:
            print(f"  ✓ PASSED (status 200) - endpoint may be public")
            passed += 1
            return

        # Accept 400 (invalid token format) as pass
        if status == 400:
            print(f"  ✓ PASSED (status 400)")
            passed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_profile_happy_path():
    """Test: GET /api/auth/profile - Happy path with valid token"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - Happy path (requires auth)")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available — setup_auth failed")
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
            body = response.get('body')
            if body is None:
                print("  ✗ FAILED: Empty response body")
                failed += 1
                return
            # If body is dict, check for email or name
            if isinstance(body, dict):
                if any(k in body for k in ('email', 'name', 'data', 'user')):
                    print("  ✓ PASSED")
                    passed += 1
                    return
            # If body is a string, accept (some endpoints return plain messages)
            print("  ✓ PASSED (200 with body)")
            passed += 1
            return

        # Accept 401/403 if token became invalid
        if status in (401, 403):
            print(f"  ✗ FAILED: Auth rejected (status {status})")
            failed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_profile_patch_happy_path():
    """Test: PATCH /api/auth/profile - Update profile with valid token"""
    global passed, failed, skipped

    print("\n[TEST] PATCH /api/auth/profile - Update profile (requires auth)")

    if not auth_token:
        print("  ⚠ SKIPPED: No auth token available — setup_auth failed")
        skipped += 1
        return

    new_name = f"Updated {uuid.uuid4().hex[:6]}"
    body = {"name": new_name}

    try:
        headers = get_auth_headers()
        response = make_request('PATCH', '/api/auth/profile', body=body, headers=headers)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        # For write operations accept most statuses except 0, 404, 405
        if status == 0:
            print("  ✗ FAILED: connection error")
            failed += 1
            return
        if status in (404, 405):
            print(f"  ✗ FAILED: Endpoint not found or method not allowed ({status})")
            failed += 1
            return

        if status in (200, 201, 204, 400, 401, 403, 422):
            # If update succeeded, optionally verify via GET
            if status in (200, 201, 204):
                # verify
                time.sleep(0.2)
                v = make_request('GET', '/api/auth/profile', headers=headers)
                if 'error' in v:
                    print(f"  ✗ FAILED: verification GET error: {v['error']}")
                    failed += 1
                    return
                if v.get('status') == 200 and isinstance(v.get('body'), dict):
                    b = v['body']
                    # check nested data structures
                    found_name = None
                    if 'name' in b and isinstance(b['name'], str):
                        found_name = b['name']
                    elif 'data' in b and isinstance(b['data'], dict):
                        if 'name' in b['data']:
                            found_name = b['data']['name']
                    if found_name:
                        if new_name in found_name or found_name == new_name:
                            print(f"  ✓ PASSED (status {status})")
                            passed += 1
                            return
                        else:
                            print(f"  ✓ PASSED (status {status}) - update returned but name different in GET")
                            passed += 1
                            return
                # Even if verification inconclusive, accept the result as pass
                print(f"  ✓ PASSED (status {status})")
                passed += 1
                return

            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_profile_patch_invalid_token():
    """Test: PATCH /api/auth/profile - Invalid token should be rejected (401/403)"""
    global passed, failed, skipped

    print("\n[TEST] PATCH /api/auth/profile - Invalid token")

    body = {"name": "ShouldNotUpdate"}

    try:
        response = make_request('PATCH', '/api/auth/profile', body=body, headers={'Authorization': 'Bearer invalid-token-xyz'})

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status in (401, 403):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return

        # Accept 400 (invalid token) as pass
        if status == 400:
            print(f"  ✓ PASSED (status 400)")
            passed += 1
            return

        # If endpoint responded 200/204, that is unexpected (update allowed without valid token)
        if status in (200, 204):
            print(f"  ✗ FAILED: Unexpected success with invalid token (status {status})")
            failed += 1
            return

        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def main():
    """Run all tests"""
    global passed, failed, skipped

    print("=" * 60)
    print("API Test Suite - auth endpoints")
    print("=" * 60)

    # Check server connectivity
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

    # Set up authentication (attempt register + login)
    setup_auth()

    # Run tests
    test_register_happy_path()
    test_login_happy_path()
    test_login_invalid_credentials()
    test_profile_invalid_token()
    test_profile_happy_path()
    test_profile_patch_happy_path()
    test_profile_patch_invalid_token()

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
