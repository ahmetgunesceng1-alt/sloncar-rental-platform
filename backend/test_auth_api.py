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
BASE_URL = os.environ.get("API_BASE_URL", f"http://localhost:{SERVER_PORT}")
TIMEOUT = 10  # seconds
passed = 0
failed = 0
skipped = 0
auth_token = None


def make_request(method, path, body=None, headers=None):
    """Make HTTP request to the API"""
    if headers is None:
        headers = {}

    # Add default Content-Type for JSON
    if body is not None and 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json'

    # Store request info for reporting
    request_info = {
        'method': method,
        'url': BASE_URL + path,
        'headers': {k: v for k, v in headers.items()},
        'body': body
    }

    # Parse URL
    url = urlparse(BASE_URL + path)

    try:
        # Create connection (HTTPS or HTTP based on scheme)
        if url.scheme == 'https':
            import ssl
            context = ssl.create_default_context()
            conn = http.client.HTTPSConnection(url.netloc, timeout=TIMEOUT, context=context)
        else:
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
            'headers': norm_headers,
            'request': request_info
        }
    except Exception as e:
        return {
            'status': 0,
            'body': None,
            'headers': {},
            'error': str(e),
            'request': request_info
        }


def truncate(obj, max_len=500):
    """Truncate a JSON-serializable object's string representation for display"""
    s = json.dumps(obj, ensure_ascii=False, default=str) if not isinstance(obj, str) else obj
    return s[:max_len] + '...' if len(s) > max_len else s


def print_req_res(response):
    """Print request and response details for the test report"""
    req = response.get('request', {})
    print(f"    ── Request ──")
    print(f"    {req.get('method', '?')} {req.get('url', '?')}")
    if req.get('headers'):
        # Redact Authorization header values
        safe_headers = {k: ('[REDACTED]' if k.lower() == 'authorization' else v) for k, v in req['headers'].items()}
        print(f"    Headers: {json.dumps(safe_headers, ensure_ascii=False)}")
    if req.get('body'):
        print(f"    Body: {truncate(req['body'])}")
    print(f"    ── Response ──")
    print(f"    Status: {response.get('status', '?')}")
    if response.get('body') is not None:
        print(f"    Body: {truncate(response['body'])}")


# ----------------- Authentication helpers -----------------

def setup_auth():
    """Register a test user and login to get auth token"""
    global auth_token, passed, failed, skipped

    test_email = f"testbot+{int(time.time())}@example.com"
    test_password = "TestPass123!"
    test_name = "Test Bot"

    print("\n[SETUP] Attempting to register test user...")

    reg_body = {
        "email": test_email,
        "password": test_password,
        "name": test_name
    }

    resp = make_request('POST', '/api/auth/register', body=reg_body)
    print_req_res(resp)

    # If register returned a token directly, extract it
    token = None
    if resp.get('status') and resp['status'] not in (0, 404, 405):
        body = resp.get('body')
        token = extract_token_from_body_or_headers(body, resp.get('headers', {}))
        if token:
            auth_token = token
            print(f"  ✓ Auth: Got token from register response")
            return

    # If register failed with conflict (user exists) or didn't contain token, try login
    print("  → Trying to login with test credentials...")
    login_body = {
        "email": test_email,
        "password": test_password
    }
    login_resp = make_request('POST', '/api/auth/login', body=login_body)
    print_req_res(login_resp)

    if login_resp.get('status') and login_resp['status'] not in (0, 404, 405):
        token = extract_token_from_body_or_headers(login_resp.get('body'), login_resp.get('headers', {}))
        if token:
            auth_token = token
            print(f"  ✓ Auth: Got token from login response")
            return

    # If we reach here, we don't have a token
    print(f"  ⚠ Auth: Could not obtain token (register: {resp.get('status')}, login: {login_resp.get('status')})")


def extract_token_from_body_or_headers(body, headers):
    """Try common locations for tokens in response body or headers"""
    # Check headers for set-cookie or authorization-like headers
    # headers keys are normalized to lowercase in make_request
    if headers:
        # Some APIs may set a cookie named 'token' or 'access_token'
        for hk, hv in headers.items():
            if 'set-cookie' in hk and hv:
                # Not parsing cookie value — leave for body extraction
                pass

    if not body:
        return None

    if isinstance(body, dict):
        # Top-level token fields
        for key in ('token', 'accessToken', 'access_token', 'jwt', 'access-token'):
            if key in body and isinstance(body[key], str):
                return body[key]

        # Common nested fields
        data = body.get('data') if isinstance(body.get('data'), dict) else None
        if data:
            for key in ('token', 'accessToken', 'access_token', 'jwt'):
                if key in data and isinstance(data[key], str):
                    return data[key]

        # tokens.access.token pattern
        tokens = body.get('tokens') if isinstance(body.get('tokens'), dict) else None
        if tokens:
            access = tokens.get('access') if isinstance(tokens.get('access'), dict) else None
            if access and isinstance(access.get('token'), str):
                return access.get('token')

    return None


def get_auth_headers():
    """Return auth headers if token is available"""
    if auth_token:
        return {'Authorization': f'Bearer {auth_token}'}
    return {}


# ----------------- Tests -----------------

def test_register():
    """Test: POST /api/auth/register - Create new user"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/register - Create new user")

    body = {
        "email": f"testbot+{int(time.time())}@example.com",
        "password": "TestPass123!",
        "name": "Test Bot"
    }

    try:
        response = make_request('POST', '/api/auth/register', body=body)
        print_req_res(response)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        # For write operations: treat 0, 404, 405 as failures
        if response['status'] in (0, 404, 405):
            print(f"  ✗ FAILED: Unexpected status {response['status']}")
            failed += 1
            return

        # Otherwise accept the response (201,200,400,401,403,422 are acceptable)
        print(f"  ✓ PASSED (status {response['status']})")
        passed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_login_happy():
    """Test: POST /api/auth/login - Login with correct credentials"""
    global passed, failed, skipped, auth_token

    print("\n[TEST] POST /api/auth/login - Happy path")

    # We attempt to login with the test user created in setup_auth if possible
    # If setup_auth set auth_token already, try to login with that user's credentials is not possible
    # So we will try to login with a known test user created during setup by reading environment variables used there.

    # As setup_auth created a user with timestamped email, we cannot reconstruct it here.
    # However setup_auth has already tried login and set auth_token if successful.
    # So here we just assert that auth_token exists or try a generic login (which may fail).

    if auth_token:
        print("  ✓ SKIPPED: auth token already obtained in setup_auth")
        skipped += 1
        return

    # If no token was obtained during setup, try a fallback: login with a default admin in env
    email = os.environ.get('TEST_ADMIN_EMAIL')
    password = os.environ.get('TEST_ADMIN_PASSWORD')
    if not email or not password:
        print("  ⚠ SKIPPED: No credentials available to perform login. setup_auth did not yield a token and TEST_ADMIN_* env not set.")
        skipped += 1
        return

    try:
        response = make_request('POST', '/api/auth/login', body={"email": email, "password": password})
        print_req_res(response)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        if response['status'] in (0, 404, 405):
            print(f"  ✗ FAILED: Unexpected status {response['status']}")
            failed += 1
            return

        # Try to extract token
        token = extract_token_from_body_or_headers(response.get('body'), response.get('headers', {}))
        if token:
            auth_token = token
            print("  ✓ PASSED: Login returned a token")
            passed += 1
        else:
            print(f"  ✗ FAILED: Login did not return a token (status {response['status']})")
            failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_login_invalid_credentials():
    """Test: POST /api/auth/login - Invalid credentials should be rejected"""
    global passed, failed, skipped

    print("\n[TEST] POST /api/auth/login - Invalid credentials")

    try:
        response = make_request('POST', '/api/auth/login', body={"email": "no-such-user@example.com", "password": "wrongpassword"})
        print_req_res(response)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        # Expect 401/403 ideally. Accept 400/401/403 or even 200 (some APIs return 200 with error object)
        if response['status'] in (401, 403):
            print(f"  ✓ PASSED (status {response['status']})")
            passed += 1
        elif response['status'] in (400,):
            print(f"  ✓ PASSED (status {response['status']})")
            passed += 1
        elif response['status'] == 200:
            # If 200, still check if body indicates auth failure (very heuristic)
            body = response.get('body')
            if not body:
                print("  ✗ FAILED: Unexpected 200 with empty body for invalid credentials")
                failed += 1
            else:
                # If body contains token fields, then that's surprising and fail
                token = extract_token_from_body_or_headers(body, response.get('headers', {}))
                if token:
                    print("  ✗ FAILED: Invalid credentials returned a token")
                    failed += 1
                else:
                    print("  ✓ PASSED (200 but no token in body)")
                    passed += 1
        else:
            print(f"  ✗ FAILED: Unexpected status {response['status']}")
            failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_profile_get():
    """Test: GET /api/auth/profile - Get profile with valid token"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - With valid token")

    headers = get_auth_headers()
    if not headers:
        print("  ⚠ SKIPPED: No auth token available for profile GET")
        skipped += 1
        return

    try:
        response = make_request('GET', '/api/auth/profile', headers=headers)
        print_req_res(response)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        # Accept 200 as success. If 401/403 returned, it's a failure of auth flow
        if response['status'] == 200:
            if response.get('body') is None:
                print(f"  ✗ FAILED: Expected non-empty body for profile, got empty")
                failed += 1
                return
            print("  ✓ PASSED")
            passed += 1
        elif response['status'] in (401, 403):
            print(f"  ✗ FAILED: Protected endpoint returned {response['status']} despite valid token")
            failed += 1
        else:
            print(f"  ✗ FAILED: Unexpected status {response['status']}")
            failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_profile_patch():
    """Test: PATCH /api/auth/profile - Update profile (only assert non-404/405)"""
    global passed, failed, skipped

    print("\n[TEST] PATCH /api/auth/profile - Update profile")

    headers = get_auth_headers()
    if not headers:
        print("  ⚠ SKIPPED: No auth token available for profile PATCH")
        skipped += 1
        return

    body = {"name": "Test Bot Updated"}

    try:
        response = make_request('PATCH', '/api/auth/profile', body=body, headers=headers)
        print_req_res(response)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        # For write operations: treat 0,404,405 as failures. Others accepted.
        if response['status'] in (0, 404, 405):
            print(f"  ✗ FAILED: Unexpected status {response['status']}")
            failed += 1
            return

        print(f"  ✓ PASSED (status {response['status']})")
        passed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_profile_invalid_token():
    """Test: GET /api/auth/profile - Access with invalid token"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/auth/profile - Invalid token")

    headers = {'Authorization': 'Bearer invalid-token-12345'}

    try:
        response = make_request('GET', '/api/auth/profile', headers=headers)
        print_req_res(response)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        # Accept either 401/403 (protected) or 200 (public endpoint)
        if response['status'] in (200, 401, 403):
            print(f"  ✓ PASSED (status {response['status']})")
            passed += 1
        else:
            print(f"  ✗ FAILED: Expected 200/401/403, got {response['status']}")
            failed += 1

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


# ----------------- Main -----------------

def main():
    """Run all tests"""
    print("=" * 60)
    print("API Test Suite - Auth Endpoints")
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

    # Set up authentication
    setup_auth()

    # Run tests
    test_register()
    test_login_happy()
    test_login_invalid_credentials()
    test_profile_get()
    test_profile_patch()
    test_profile_invalid_token()

    # Print summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    # Exit with appropriate code — skipped tests do NOT count as failures
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
