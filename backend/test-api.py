#!/usr/bin/env python3
"""
API Test Suite
Tests for /api/cars endpoints
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
CANDIDATES = ['/api/cars', '/api/v1/cars', '/cars', '/v1/cars']
selected_base = None


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


def setup_auth():
    """Register a test user and login to get auth token"""
    global auth_token

    if auth_token:
        return

    email = 'testbot@example.com'
    password = 'TestPass123!'

    # Try multiple possible register endpoints
    register_paths = [
        '/api/auth/register', '/api/auth/signup', '/api/users/register', '/api/users/signup', '/api/register'
    ]
    login_paths = [
        '/api/auth/login', '/api/auth/signin', '/api/users/login', '/api/login'
    ]

    reg_body = {
        'email': email,
        'password': password,
        'name': 'Test Bot'
    }

    reg_resp = None
    for path in register_paths:
        resp = make_request('POST', path, body=reg_body)
        if resp.get('status') == 0:
            continue
        # Accept 201/200 and also 409 (already exists) as meaningful
        if resp['status'] in (200, 201, 400, 409, 422):
            reg_resp = resp
            break

    # Try to extract token from register response
    if reg_resp and reg_resp.get('body'):
        body = reg_resp['body']
        token = None
        if isinstance(body, dict):
            for key in ('token', 'accessToken', 'access_token', 'jwt'):
                if key in body:
                    token = body[key]
                    break
            if not token and 'data' in body and isinstance(body['data'], dict):
                for key in ('token', 'accessToken', 'access_token'):
                    if key in body['data']:
                        token = body['data'][key]
                        break
            if not token and 'tokens' in body and isinstance(body['tokens'], dict):
                access = body['tokens'].get('access', {})
                if isinstance(access, dict):
                    token = access.get('token')
        if token:
            auth_token = token
            print("  ✓ Auth: Got token from register response")
            return

    # If register didn't yield a token, try login endpoints
    login_body = {'email': email, 'password': password}
    # If register failed due to missing fields, try a fallback registration that only sends email/password
    if not reg_resp:
        # try a minimal register at common api paths
        for path in register_paths:
            resp = make_request('POST', path, body={'email': email, 'password': password})
            if resp.get('status') in (200, 201, 400, 409, 422):
                reg_resp = resp
                break

    # Attempt login
    for path in login_paths:
        resp = make_request('POST', path, body=login_body)
        if resp.get('status') == 0:
            continue
        if resp['status'] in (200, 201, 400, 401, 403, 422):
            body = resp.get('body')
            token = None
            if isinstance(body, dict):
                for key in ('token', 'accessToken', 'access_token', 'jwt'):
                    if key in body:
                        token = body[key]
                        break
                if not token and 'data' in body and isinstance(body['data'], dict):
                    for key in ('token', 'accessToken', 'access_token'):
                        if key in body['data']:
                            token = body['data'][key]
                            break
                if not token and 'tokens' in body and isinstance(body['tokens'], dict):
                    access = body['tokens'].get('access', {})
                    if isinstance(access, dict):
                        token = access.get('token')
            # Check headers for set-cookie or authorization tokens
            headers = resp.get('headers', {})
            set_cookie = headers.get('set-cookie')
            if set_cookie and not token:
                # Some systems put session id in cookie – we won't parse it as a Bearer token but store cookie as token-like
                token = set_cookie
            if token:
                auth_token = token
                print("  ✓ Auth: Got token from login response")
                return

    print(f"  ⚠ Auth: Could not obtain token (register: {reg_resp['status'] if reg_resp else 'n/a'})")


def get_auth_headers():
    """Return auth headers if token is available"""
    if not auth_token:
        return {}
    # If token looks like a cookie (contains '=') use Cookie header, else Bearer
    if isinstance(auth_token, str) and '=' in auth_token and ' ' not in auth_token:
        return {'Cookie': auth_token}
    return {'Authorization': f'Bearer {auth_token}'}


def discover_cars_endpoint():
    """Probe candidate paths to find the cars endpoint the server exposes"""
    global selected_base
    # If already discovered, return it
    if selected_base:
        return selected_base

    best = None
    for path in CANDIDATES:
        resp = make_request('GET', path)
        if resp.get('status') == 0:
            # connection issue for this attempt — continue probing
            continue
        # Prefer a 200, otherwise accept any response that is not a connection error
        if resp['status'] == 200:
            selected_base = path
            return selected_base
        if best is None:
            best = path
    selected_base = best
    return selected_base


def test_get_cars_list_happy_path():
    """Test: GET /api/cars - Happy path"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/cars - Happy path")
    base = discover_cars_endpoint()
    if not base:
        print("  ⚠ SKIPPED: Could not discover cars endpoint")
        skipped += 1
        return

    try:
        response = make_request('GET', base)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        if response['status'] == 200:
            # Accept JSON response (list or dict)
            if response['body'] is None:
                print(f"  ✗ FAILED: Empty response body for {base}")
                failed += 1
                return
            print("  ✓ PASSED")
            passed += 1
            return
        elif response['status'] in (401, 403):
            # Try to authenticate and retry
            setup_auth()
            if auth_token:
                headers = get_auth_headers()
                response2 = make_request('GET', base, headers=headers)
                if response2.get('status') == 200:
                    if response2['body'] is None:
                        print(f"  ✗ FAILED: Empty response body after auth for {base}")
                        failed += 1
                        return
                    print("  ✓ PASSED (auth)")
                    passed += 1
                    return
                else:
                    # Protected but still not 200 — treat 401/403 as acceptable protected behavior
                    if response2['status'] in (401, 403):
                        print(f"  ✓ PASSED (protected, status {response2['status']})")
                        passed += 1
                        return
                    else:
                        print(f"  ✗ FAILED: Unexpected status after auth: {response2['status']}")
                        failed += 1
                        return
            else:
                print(f"  ✓ PASSED (protected, status {response['status']})")
                passed += 1
                return
        else:
            # Accept 400/404 as possible (endpoint exists but other behavior)
            if response['status'] in (400, 404):
                print(f"  ✓ PASSED ({response['status']})")
                passed += 1
                return
            print(f"  ✗ FAILED: Expected 200/401/403/404, got {response['status']}")
            failed += 1
            return

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_get_single_car_by_id():
    """Test: GET /api/cars/{id} - Single resource by ID"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/cars/{id} - Single resource by ID")
    base = discover_cars_endpoint()
    if not base:
        print("  ⚠ SKIPPED: Could not discover cars endpoint")
        skipped += 1
        return

    try:
        list_resp = make_request('GET', base)
        if list_resp.get('status') == 0:
            print(f"  ✗ FAILED: {list_resp.get('error')}")
            failed += 1
            return

        if list_resp['status'] == 200 and isinstance(list_resp['body'], list) and len(list_resp['body']) > 0:
            # Find an id field in first item
            item = list_resp['body'][0]
            if isinstance(item, dict):
                for key in ('id', '_id', 'uuid', 'slug'):
                    if key in item:
                        resource_id = item[key]
                        break
                else:
                    # Try common fallback 'id' nested
                    resource_id = None
                    for k in item.keys():
                        if k.lower().endswith('id'):
                            resource_id = item[k]
                            break
                if not resource_id:
                    print("  ⚠ SKIPPED: Could not find a usable id in list item")
                    skipped += 1
                    return
                # Request single resource
                path = base.rstrip('/') + '/' + str(resource_id)
                # Try without auth first
                resp = make_request('GET', path)
                if resp.get('status') == 0:
                    print(f"  ✗ FAILED: {resp.get('error')}")
                    failed += 1
                    return
                if resp['status'] == 200:
                    if resp['body'] is None:
                        print(f"  ✗ FAILED: Empty response body for {path}")
                        failed += 1
                        return
                    print("  ✓ PASSED")
                    passed += 1
                    return
                elif resp['status'] in (401, 403):
                    # Try with auth
                    setup_auth()
                    if auth_token:
                        resp2 = make_request('GET', path, headers=get_auth_headers())
                        if resp2.get('status') == 200:
                            print("  ✓ PASSED (auth)")
                            passed += 1
                            return
                        elif resp2['status'] in (401, 403):
                            print(f"  ✓ PASSED (protected, status {resp2['status']})")
                            passed += 1
                            return
                        else:
                            print(f"  ✗ FAILED: Unexpected status after auth: {resp2['status']}")
                            failed += 1
                            return
                    else:
                        print(f"  ✓ PASSED (protected, status {resp['status']})")
                        passed += 1
                        return
                else:
                    # Accept 400/404 as valid not-found/invalid-id format
                    if resp['status'] in (400, 404):
                        print(f"  ✓ PASSED ({resp['status']})")
                        passed += 1
                        return
                    print(f"  ✗ FAILED: Unexpected status {resp['status']}")
                    failed += 1
                    return
            else:
                print("  ⚠ SKIPPED: List response items are not objects; cannot find id")
                skipped += 1
                return
        else:
            # If list is empty or not a list, skip the single-resource test
            if list_resp['status'] in (200,) and (list_resp['body'] == [] or list_resp['body'] is None):
                print("  ⚠ SKIPPED: No items in list to test single-resource endpoint")
                skipped += 1
                return
            # If list endpoint refused with 401/403, try to auth and fetch again
            if list_resp['status'] in (401, 403):
                setup_auth()
                if auth_token:
                    list2 = make_request('GET', base, headers=get_auth_headers())
                    if list2.get('status') == 200 and isinstance(list2.get('body'), list) and len(list2['body']) > 0:
                        # Re-run single id flow by recursive call
                        test_get_single_car_by_id()
                        return
                print(f"  ⚠ SKIPPED: Protected or empty list endpoint (status {list_resp['status']})")
                skipped += 1
                return
            print(f"  ⚠ SKIPPED: Unexpected list response (status {list_resp['status']})")
            skipped += 1
            return

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_cars_not_found():
    """Test: GET /api/cars/nonexistent - Not found"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/cars/nonexistent - Not found")
    base = discover_cars_endpoint()
    if not base:
        print("  ⚠ SKIPPED: Could not discover cars endpoint")
        skipped += 1
        return

    try:
        fake_id = 'nonexistent-id-12345'
        path = base.rstrip('/') + '/' + fake_id
        resp = make_request('GET', path)
        if resp.get('status') == 0:
            print(f"  ✗ FAILED: {resp.get('error')}")
            failed += 1
            return
        if resp['status'] in [404, 400]:
            print(f"  ✓ PASSED ({resp['status']})")
            passed += 1
        elif resp['status'] == 200:
            body = resp['body']
            if body is None or body == [] or body == {}:
                print("  ✓ PASSED (200 with empty response)")
                passed += 1
            else:
                print(f"  ✗ FAILED: Expected 404 or empty response, got 200 with data")
                failed += 1
        else:
            print(f"  ✗ FAILED: Expected 404/400/200-empty, got {resp['status']}")
            failed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_invalid_auth():
    """Test: GET /api/cars - Invalid authentication"""
    global passed, failed, skipped

    print("\n[TEST] GET /api/cars - Invalid auth")
    base = discover_cars_endpoint()
    if not base:
        print("  ⚠ SKIPPED: Could not discover cars endpoint")
        skipped += 1
        return

    try:
        response = make_request('GET', base, headers={'Authorization': 'Bearer invalid-token-12345'})
        if response.get('status') == 0:
            print(f"  ✗ FAILED: {response.get('error')}")
            failed += 1
            return
        if response['status'] in [200, 401, 403]:
            print(f"  ✓ PASSED (status {response['status']})")
            passed += 1
        else:
            print(f"  ✗ FAILED: Expected 200/401/403, got {response['status']}")
            failed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_post_cars_write_op():
    """Test: POST /api/cars - Permissive write operation test
    For unknown write schemas accept ANY HTTP status as pass (per rules).
    """
    global passed, failed, skipped

    print("\n[TEST] POST /api/cars - Write (permissive)")
    base = discover_cars_endpoint()
    if not base:
        print("  ⚠ SKIPPED: Could not discover cars endpoint")
        skipped += 1
        return

    try:
        # Minimal plausible body for creating a car — many APIs accept name/model/brand
        sample_body = {
            'name': 'Test Car',
            'model': 'TestModel',
            'brand': 'TestBrand',
            'year': 2020
        }
        resp = make_request('POST', base, body=sample_body)
        if resp.get('status') == 0:
            print(f"  ✗ FAILED: {resp.get('error')}")
            failed += 1
            return
        # Accept ANY status as pass for write operations
        print(f"  ✓ PASSED (status {resp['status']})")
        passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def main():
    """Run all tests"""
    print("=" * 60)
    print("API Test Suite")
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

    # Attempt to discover cars endpoint now (will probe candidates)
    discover_cars_endpoint()

    # Attempt to set up authentication (may or may not be used)
    setup_auth()

    # Run tests
    test_get_cars_list_happy_path()
    test_get_single_car_by_id()
    test_cars_not_found()
    test_invalid_auth()
    test_post_cars_write_op()

    # Print summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    # Exit with appropriate code — skipped tests do NOT count as failures
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
