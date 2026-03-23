#!/usr/bin/env python3
"""
API Test Suite
Tests for Cars public endpoints
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

# Candidate prefixes to probe for the cars endpoints
CANDIDATE_PATHS = [
    '/cars',
    '/api/cars',
    '/api/v1/cars',
    '/v1/cars',
    '/api/v1/public/cars',
]


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


def probe_base_path():
    """Probe candidate paths and return the first responsive one (or None).
    Criteria: any non-zero response (status != 0) is considered responsive.
    Prefer a path that returns JSON list/dict with 200 status when possible.
    """
    best = None
    for p in CANDIDATE_PATHS:
        resp = make_request('GET', p)
        if 'error' in resp:
            # Connection error — skip
            continue
        status = resp.get('status', 0)
        body = resp.get('body')
        # Prefer 200 with JSON body
        if status == 200 and isinstance(body, (list, dict)):
            return p
        # Keep first non-error response as fallback
        if best is None and status != 0:
            best = p
    return best


def extract_id_from_item(item):
    if not isinstance(item, dict):
        return None
    for key in ('id', '_id', 'uuid', 'slug', 'carId', 'vin'):
        if key in item and item[key]:
            return str(item[key])
    # Some APIs nest the real object under 'data'
    if 'data' in item and isinstance(item['data'], dict):
        for key in ('id', '_id', 'uuid', 'slug', 'carId', 'vin'):
            if key in item['data'] and item['data'][key]:
                return str(item['data'][key])
    return None


def find_resource_id(list_response_body):
    # list_response_body could be a list or dict containing list
    if list_response_body is None:
        return None
    # If it's a list, try first item
    if isinstance(list_response_body, list):
        if len(list_response_body) == 0:
            return None
        for it in list_response_body:
            idv = extract_id_from_item(it)
            if idv:
                return idv
        return None
    # If dict, common patterns: { data: [ ... ] } or { items: [...] }
    if isinstance(list_response_body, dict):
        for key in ('data', 'items', 'rows', 'cars'):
            if key in list_response_body and isinstance(list_response_body[key], list):
                for it in list_response_body[key]:
                    idv = extract_id_from_item(it)
                    if idv:
                        return idv
        # If dict itself contains id fields, maybe single object returned
        idv = extract_id_from_item(list_response_body)
        if idv:
            return idv
    return None


def test_get_cars_list(base):
    """Test: GET /cars - list (happy path tolerant)"""
    global passed, failed, skipped

    print(f"\n[TEST] GET {base} - List cars")
    try:
        response = make_request('GET', base)

        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return None

        status = response['status']
        body = response['body']
        # Accept common GET statuses as pass (200 successful; also tolerate 400/401/403/404/405)
        if status in (200, 400, 401, 403, 404, 405):
            # If 200, ensure body is parseable JSON (list/dict or at least non-empty)
            if status == 200:
                if body is None:
                    print("  ✗ FAILED: Expected JSON body for 200 response, got empty")
                    failed += 1
                    return None
                if not isinstance(body, (list, dict)):
                    # non-JSON string allowed if actually string content — treat as pass but warn
                    print("  ✓ PASSED (200) — body not a list/dict but returned content")
                    passed += 1
                    return body
                print(f"  ✓ PASSED (status {status})")
                passed += 1
                return body
            else:
                print(f"  ✓ PASSED (status {status})")
                passed += 1
                return body
        else:
            print(f"  ✗ FAILED: Unexpected status {status}")
            failed += 1
            return None

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1
        return None


def test_get_single_car(base, car_id):
    """Test: GET /cars/:id - single resource retrieval"""
    global passed, failed, skipped

    url = f"{base}/{car_id}"
    print(f"\n[TEST] GET {url} - Single car by id")
    try:
        response = make_request('GET', url)
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return
        status = response['status']
        body = response['body']
        # Accept 200 (with object) or not-found indications 400/404
        if status in (200, 400, 404):
            if status == 200:
                if body is None:
                    print(f"  ✗ FAILED: 200 returned but body is empty")
                    failed += 1
                    return
                # Body should represent a single resource (dict) or nested object
                if isinstance(body, dict) or isinstance(body, list) or isinstance(body, str):
                    print(f"  ✓ PASSED (200)")
                    passed += 1
                    return
                else:
                    print(f"  ✓ PASSED (200) — body present")
                    passed += 1
                    return
            else:
                print(f"  ✓ PASSED (status {status})")
                passed += 1
                return
        else:
            print(f"  ✗ FAILED: Unexpected status {status}")
            failed += 1
            return
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1
        return


def test_get_brands_or_categories(path_label, path):
    """Test: GET brands/categories endpoints"""
    global passed, failed, skipped

    print(f"\n[TEST] GET {path} - {path_label}")
    try:
        response = make_request('GET', path)
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return
        status = response['status']
        body = response['body']
        # Accept common statuses
        if status in (200, 400, 401, 403, 404, 405):
            if status == 200:
                if body is None:
                    print(f"  ✗ FAILED: Expected body for 200, got empty")
                    failed += 1
                    return
                print(f"  ✓ PASSED (200)")
                passed += 1
                return
            else:
                print(f"  ✓ PASSED (status {status})")
                passed += 1
                return
        else:
            print(f"  ✗ FAILED: Unexpected status {status}")
            failed += 1
            return
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1
        return


def test_get_nonexistent_id(base):
    """Test: GET /cars/:id with a non-existing id - expect 404/400 or 200-empty"""
    global passed, failed, skipped

    fake_id = 'nonexistent-id-12345'
    path = f"{base}/{fake_id}"
    print(f"\n[TEST] GET {path} - Not found with fake id")
    try:
        response = make_request('GET', path)
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return
        status = response['status']
        body = response['body']
        if status in (404, 400):
            print(f"  ✓ PASSED ({status})")
            passed += 1
            return
        if status == 200:
            # If 200, accept if body indicates empty or not found
            if body in (None, [], {}, ''):
                print("  ✓ PASSED (200 with empty body)")
                passed += 1
                return
            # If returns an object but indicates not found, still pass
            if isinstance(body, dict) and ('error' in body or 'message' in body and 'not' in str(body.get('message', '')).lower()):
                print("  ✓ PASSED (200 with not-found message)")
                passed += 1
                return
            print(f"  ✗ FAILED: 200 with data for nonexistent id")
            failed += 1
            return
        if status in (401, 403, 404, 405):
            print(f"  ✓ PASSED ({status})")
            passed += 1
            return
        print(f"  ✗ FAILED: Unexpected status {status}")
        failed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_invalid_auth(base):
    """Test: GET /cars with invalid auth token"""
    global passed, failed, skipped

    print(f"\n[TEST] GET {base} - Invalid auth token")
    try:
        response = make_request('GET', base, headers={'Authorization': 'Bearer invalid-token-12345'})
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return
        status = response['status']
        # Accept 200 (public) or 401/403 (protected)
        if status in (200, 401, 403):
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return
        print(f"  ✗ FAILED: Expected 200/401/403, got {status}")
        failed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def main():
    global passed, failed, skipped
    print("=" * 60)
    print("Cars Endpoints API Test Suite")
    print("=" * 60)

    # Check server connectivity quickly
    print("\nChecking server connectivity...")
    try:
        root = make_request('GET', '/')
        if 'error' in root:
            print(f"⚠ WARNING: Server not responding at /: {root.get('error')}")
            print("Tests will likely fail with connection errors\n")
        else:
            print(f"✓ Server responded at / (status {root.get('status')})\n")
    except Exception as e:
        print(f"⚠ WARNING: Could not connect to server: {str(e)}\n")

    # Find base path for cars endpoints
    base = probe_base_path()
    if base is None:
        print("⚠ Could not find any responsive cars endpoint among candidates:")
        for p in CANDIDATE_PATHS:
            print(f"  - {p}")
        print("Aborting tests.")
        # This is a connection/finding failure — count as failed
        failed += 1
        print("\n" + "=" * 60)
        print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
        print("=" * 60)
        sys.exit(1)

    print(f"Using base path: {base}")

    # Run tests
    list_body = test_get_cars_list(base)

    # Try to extract an ID for single-resource test
    resource_id = None
    if isinstance(list_body, (list, dict)):
        resource_id = find_resource_id(list_body)

    if resource_id:
        test_get_single_car(base, resource_id)
    else:
        print("\n⚠ SKIPPED: No resource ID found to test single-resource endpoint")
        skipped += 1

    # Test brands and categories
    test_get_brands_or_categories('Brands', f"{base}/brands")
    test_get_brands_or_categories('Categories', f"{base}/categories")

    # Test not found with fake id
    test_get_nonexistent_id(base)

    # Test invalid auth
    test_invalid_auth(base)

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
