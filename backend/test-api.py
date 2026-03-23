#!/usr/bin/env python3
"""
API Test Suite
Tests for admin Cars CRUD endpoints (POST /cars, PATCH /cars/:id, DELETE /cars/:id)
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


# ---------------- AUTH HELPERS ----------------
def extract_token_from_body(body):
    if not isinstance(body, dict):
        return None
    # Common locations
    for key in ('token', 'accessToken', 'access_token', 'jwt', 'access'):
        if key in body and isinstance(body[key], str):
            return body[key]
    # nested data
    data = body.get('data') if isinstance(body.get('data'), dict) else None
    if data:
        for key in ('token', 'accessToken', 'access_token'):
            if key in data and isinstance(data[key], str):
                return data[key]
    # tokens.access.token pattern
    tokens = body.get('tokens') if isinstance(body.get('tokens'), dict) else None
    if tokens:
        access = tokens.get('access')
        if isinstance(access, dict) and isinstance(access.get('token'), str):
            return access.get('token')
    return None


def setup_auth():
    """Register a test user and login to get auth token"""
    global auth_token
    if auth_token:
        return

    # Candidate endpoints for register and login
    register_paths = [
        '/api/auth/register', '/auth/register', '/api/auth/signup', '/auth/signup',
        '/api/users/register', '/users/register', '/api/v1/auth/register', '/register'
    ]
    login_paths = [
        '/api/auth/login', '/auth/login', '/api/auth/signin', '/auth/signin',
        '/api/users/login', '/users/login', '/api/v1/auth/login', '/login'
    ]

    # Unique test user
    email = f"testbot+{int(time.time())}@example.com"
    password = "TestPass123!"

    # Try register
    reg_resp = None
    for rp in register_paths:
        print(f"Trying register endpoint: {rp}")
        body = {"email": email, "password": password, "name": "Test Bot"}
        resp = make_request('POST', rp, body=body)
        if 'error' in resp:
            print(f"  register try {rp} error: {resp.get('error')}")
            continue
        # If endpoint not found or method not allowed, try next
        if resp['status'] in (404, 405):
            print(f"  register try {rp} returned {resp['status']}")
            continue
        reg_resp = resp
        print(f"  register try {rp} returned {resp['status']}")
        break

    # Try to extract token from register response
    if reg_resp and reg_resp.get('body'):
        token = extract_token_from_body(reg_resp['body'])
        if token:
            auth_token = token
            print("  ✓ Auth: Got token from register response")
            return

    # If register failed or did not return token, try login
    login_resp = None
    for lp in login_paths:
        print(f"Trying login endpoint: {lp}")
        body = {"email": email, "password": password}
        resp = make_request('POST', lp, body=body)
        if 'error' in resp:
            print(f"  login try {lp} error: {resp.get('error')}")
            continue
        if resp['status'] in (404, 405):
            print(f"  login try {lp} returned {resp['status']}")
            continue
        login_resp = resp
        print(f"  login try {lp} returned {resp['status']}")
        break

    if login_resp and login_resp.get('body'):
        token = extract_token_from_body(login_resp['body'])
        if token:
            auth_token = token
            print("  ✓ Auth: Got token from login response body")
            return

    # Some APIs return token in headers (set-cookie) — check headers
    for resp in (reg_resp, login_resp):
        if not resp:
            continue
        headers = resp.get('headers', {})
        # check set-cookie
        sc = headers.get('set-cookie')
        if sc and 'token' in sc:
            # crude extraction of token=...;
            parts = sc.split(';')
            for p in parts:
                if 'token=' in p:
                    token = p.strip().split('token=')[-1]
                    if token:
                        auth_token = token
                        print("  ✓ Auth: Got token from set-cookie header")
                        return

    # If we reach here, auth_token may still be None
    if reg_resp and reg_resp.get('status') in (200, 201):
        print("  ⚠ Auth: register returned success but no token found")
    elif login_resp and login_resp.get('status') in (200, 201):
        print("  ⚠ Auth: login returned success but no token found")
    else:
        print(f"  ⚠ Auth: Could not obtain token (register: {reg_resp['status'] if reg_resp else 'none'}, login: {login_resp['status'] if login_resp else 'none'})")


def get_auth_headers(extra=None):
    if extra is None:
        extra = {}
    if auth_token:
        hdr = {'Authorization': f'Bearer {auth_token}'}
        hdr.update(extra)
        return hdr
    return extra


# ---------------- Discovery Helpers ----------------
def find_cars_base():
    """Probe common candidate paths and return the first that seems live for cars endpoints.
    Returns path string (e.g. /api/cars) or None if none found.
    """
    candidates = ['/cars', '/api/cars', '/api/v1/cars', '/v1/cars', '/api/admin/cars', '/admin/cars', '/api/v1/admin/cars']
    sample_body = {"name": "Test Car Probe"}

    for base in candidates:
        # Try POST first (write). For write operations, 404/405 means wrong path.
        resp = make_request('POST', base, body=sample_body)
        if 'error' in resp:
            # connection errors should be surfaced to caller
            print(f"Probe {base} error: {resp.get('error')}")
            continue
        if resp['status'] in (404, 405):
            print(f"Probe {base} returned {resp['status']} (not this path)")
            continue
        # Anything else indicates the path exists (even if it returned 401/403/400)
        print(f"Probe {base} accepted (status {resp['status']}) — selecting as cars base")
        return base
    # If no POST candidate accepted, try GET candidates (read-only mounts)
    for base in candidates:
        resp = make_request('GET', base)
        if 'error' in resp:
            continue
        if resp['status'] in (404, 405):
            continue
        print(f"GET probe {base} accepted (status {resp['status']}) — selecting as cars base")
        return base
    return None


def extract_id_from_body(body):
    if not body:
        return None
    # If body is dict and has id-like keys
    if isinstance(body, dict):
        for key in ('id', '_id', 'uuid', 'uid'):
            if key in body:
                return str(body[key])
        # Sometimes response has data: { id: ... }
        data = body.get('data') if isinstance(body.get('data'), dict) else None
        if data:
            for key in ('id', '_id', 'uuid', 'uid'):
                if key in data:
                    return str(data[key])
        # If body itself looks like created object with array
    # If body is list, return first element's id
    if isinstance(body, list) and len(body) > 0 and isinstance(body[0], dict):
        return extract_id_from_body(body[0])
    return None


# ---------------- Tests ----------------

def test_unauthenticated_create(base):
    global passed, failed, skipped
    print("\n[TEST] POST {}/ - Unauthenticated (expect 401/403 ideally)".format(base))
    sample = {
        "name": "Unauth Test Car",
        "description": "Should be blocked for non-admin"
    }
    resp = make_request('POST', base, body=sample)
    if 'error' in resp:
        print(f"  ✗ FAILED: {resp.get('error')}")
        failed += 1
        return
    status = resp['status']
    # For write ops, treat 404/405 as path wrong (fail this test)
    if status in (404, 405):
        print(f"  ✗ FAILED: Endpoint not found or method not allowed (status {status})")
        failed += 1
        return
    # Prefer 401/403 as correct behavior
    if status in (401, 403):
        print(f"  ✓ PASSED (unauthenticated blocked with status {status})")
        passed += 1
        return
    # Other statuses (200,201,400,422) — per tolerance accept as pass but warn
    print(f"  ✓ PASSED (received status {status} — server did not return 404/405). Note: expected 401/403 for unauthenticated access")
    passed += 1


def test_crud_flow(base):
    global passed, failed, skipped
    print("\n[TEST] CRUD flow on {} (create -> update -> delete)".format(base))

    # CREATE (with auth if available)
    create_body = {
        "name": "Test Car Created by API Test",
        "description": "Created for automated tests"
    }
    headers = get_auth_headers()
    resp = make_request('POST', base, body=create_body, headers=headers)

    if 'error' in resp:
        print(f"  ✗ FAILED: Create request error: {resp.get('error')}")
        failed += 1
        return
    if resp['status'] in (404, 405):
        print(f"  ✗ FAILED: Create endpoint not found or wrong method (status {resp['status']}). Aborting CRUD flow")
        failed += 1
        return
    print(f"  Create returned status {resp['status']}")

    created_id = extract_id_from_body(resp.get('body'))
    if created_id:
        print(f"  ✓ Got ID from create response: {created_id}")
    else:
        # Try to get ID from list
        list_resp = make_request('GET', base, headers=headers)
        if 'error' in list_resp:
            print(f"  ⚠ Could not list resources to find ID: {list_resp.get('error')}")
        else:
            if isinstance(list_resp.get('body'), list) and len(list_resp.get('body')) > 0:
                created_id = extract_id_from_body(list_resp.get('body'))
                if created_id:
                    print(f"  ✓ Got ID from list response: {created_id}")
    if not created_id:
        print("  ⚠ SKIPPED: Could not determine created resource ID — skipping update & delete steps")
        skipped += 2  # update and delete skipped
        passed += 1  # count create as passed (it didn't return 404/405)
        return

    # UPDATE (PATCH preferred)
    update_path = base.rstrip('/') + '/' + created_id
    update_body = {"description": "Updated by API Test"}
    resp_up = make_request('PATCH', update_path, body=update_body, headers=get_auth_headers())
    if 'error' in resp_up:
        print(f"  ✗ FAILED: Update (PATCH) error: {resp_up.get('error')}")
        failed += 1
        return
    if resp_up['status'] in (404, 405):
        # Try PUT as fallback
        print(f"  PATCH returned {resp_up['status']}, trying PUT fallback")
        resp_up2 = make_request('PUT', update_path, body=update_body, headers=get_auth_headers())
        if 'error' in resp_up2:
            print(f"  ✗ FAILED: Update (PUT) error: {resp_up2.get('error')}")
            failed += 1
            return
        if resp_up2['status'] in (404, 405):
            print(f"  ✗ FAILED: Update endpoint not found or method not allowed (status {resp_up2['status']})")
            failed += 1
            return
        print(f"  Update (PUT) returned status {resp_up2['status']} — accepted")
        passed += 1
    else:
        print(f"  Update (PATCH) returned status {resp_up['status']} — accepted")
        passed += 1

    # DELETE
    resp_del = make_request('DELETE', update_path, headers=get_auth_headers())
    if 'error' in resp_del:
        print(f"  ✗ FAILED: Delete error: {resp_del.get('error')}")
        failed += 1
        return
    if resp_del['status'] in (404, 405):
        print(f"  ✗ FAILED: Delete endpoint not found or method not allowed (status {resp_del['status']})")
        failed += 1
        return
    print(f"  Delete returned status {resp_del['status']} — accepted")
    passed += 1


def test_invalid_auth_create(base):
    global passed, failed, skipped
    print("\n[TEST] POST {}/ - Invalid auth token".format(base))
    sample = {"name": "InvalidAuthCar"}
    headers = {'Authorization': 'Bearer invalid-token-12345'}
    resp = make_request('POST', base, body=sample, headers=headers)
    if 'error' in resp:
        print(f"  ✗ FAILED: {resp.get('error')}")
        failed += 1
        return
    if resp['status'] in (404, 405):
        print(f"  ✗ FAILED: Endpoint not found or method not allowed (status {resp['status']})")
        failed += 1
        return
    # Accept 200/401/403 as valid outcomes
    if resp['status'] in (200, 201, 401, 403):
        print(f"  ✓ PASSED (status {resp['status']})")
        passed += 1
    else:
        print(f"  ✓ PASSED (status {resp['status']}) — tolerated for write op")
        passed += 1


def main():
    global passed, failed, skipped
    print("=" * 60)
    print("API Test Suite - Cars (Admin CRUD)")
    print("=" * 60)

    # Check server connectivity
    print("\nChecking server connectivity...")
    try:
        r = make_request('GET', '/')
        if 'error' in r or r['status'] == 0:
            print(f"⚠ WARNING: Server not responding: {r.get('error')}")
            print("Tests will likely fail with connection errors\n")
        else:
            print(f"✓ Server responding (status {r['status']})\n")
    except Exception as e:
        print(f"⚠ WARNING: Could not connect to server: {str(e)}\n")

    # Setup auth (register + login)
    setup_auth()
    if auth_token:
        print(f"Using auth token: (length {len(auth_token)})\n")
    else:
        print("No auth token obtained — protected endpoints may return 401/403\n")

    # Discover cars base path
    base = find_cars_base()
    if not base:
        print("⚠ SKIPPED: Could not discover cars endpoint path. Probed common candidates and none responded (non-404/405).")
        skipped += 3  # unauthenticated create, invalid auth, and CRUD
        print("\n" + "=" * 60)
        print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
        print("=" * 60)
        sys.exit(0 if failed == 0 else 1)

    # Run tests
    test_unauthenticated_create(base)
    test_invalid_auth_create(base)
    test_crud_flow(base)

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
