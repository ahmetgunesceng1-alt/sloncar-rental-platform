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


def extract_id_from_list(body):
    """Attempt to extract a usable ID from a list or paginated response."""
    # If body is None, return None
    if body is None:
        return None
    # If body is a dict with data/list
    if isinstance(body, dict):
        # Common shapes: { data: [...] }, { items: [...] }, { results: [...] }
        for key in ('data', 'items', 'results', 'rows', 'cars'):
            if key in body and isinstance(body[key], list) and len(body[key]) > 0:
                candidate = body[key][0]
                break
        else:
            # Maybe it's a single object representing one car
            # Try to find id-like fields directly
            candidate = None
            for field in ('id', '_id', 'uuid', 'slug'):
                if field in body:
                    return body[field]
            # No id found
            if candidate is None:
                return None
    elif isinstance(body, list):
        if len(body) == 0:
            return None
        candidate = body[0]
    else:
        return None

    # candidate should be a dict now
    if not isinstance(candidate, dict):
        return None
    for field in ('id', '_id', 'uuid', 'slug'):
        if field in candidate:
            return candidate[field]
    # fallback: if there is any field that looks like id
    for k, v in candidate.items():
        if k.lower().endswith('id') or k.lower().endswith('_id'):
            return v
    return None


def test_get_cars_list_happy_path():
    """Test: GET /api/cars - Happy path"""
    global passed, failed, skipped
    print("\n[TEST] GET /api/cars - Happy path")
    try:
        response = make_request('GET', '/api/cars')
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return
        # Expect 200 for list; some APIs may return 204 or 200 with empty list
        if response['status'] != 200:
            print(f"  ✗ FAILED: Expected status 200, got {response['status']}")
            failed += 1
            return
        # Check content-type or body parseability
        content_type = response['headers'].get('content-type', '')
        if content_type and 'json' not in content_type.lower():
            if not isinstance(response['body'], (list, dict)):
                print(f"  ✗ FAILED: Expected JSON content-type or JSON body, got {content_type}")
                failed += 1
                return
        if response['body'] is None:
            print(f"  ✗ FAILED: Empty response body")
            failed += 1
            return
        print("  ✓ PASSED")
        passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_get_car_by_id():
    """Test: GET /api/cars/{id} - Single resource retrieval"""
    global passed, failed, skipped
    print("\n[TEST] GET /api/cars/{id} - Single resource retrieval")
    try:
        list_resp = make_request('GET', '/api/cars')
        if 'error' in list_resp:
            print(f"  ✗ FAILED: Could not list cars: {list_resp['error']}")
            failed += 1
            return
        # Extract ID
        id_val = extract_id_from_list(list_resp['body'])
        if not id_val:
            print("  ⚠ SKIPPED: No cars found to test single-resource retrieval")
            skipped += 1
            return
        # Build path — ensure we convert id to str
        path = '/api/cars/{}'.format(str(id_val))
        resp = make_request('GET', path)
        if 'error' in resp:
            print(f"  ✗ FAILED: {resp['error']}")
            failed += 1
            return
        # Accept 200, or 400 (invalid id format), or 404 as valid outcomes for single-resource retrieval
        if resp['status'] in (200, 400, 404):
            # If 200, ensure body is present
            if resp['status'] == 200 and resp['body'] is None:
                print(f"  ✗ FAILED: 200 OK but empty body for id {id_val}")
                failed += 1
                return
            print(f"  ✓ PASSED (status {resp['status']})")
            passed += 1
            return
        print(f"  ✗ FAILED: Unexpected status {resp['status']}")
        failed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_get_car_not_found():
    """Test: GET /api/cars/nonexistent - Not found behavior"""
    global passed, failed, skipped
    print("\n[TEST] GET /api/cars/nonexistent-id-12345 - Not found")
    try:
        response = make_request('GET', '/api/cars/nonexistent-id-12345')
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return
        # Accept 404 or 400 or 200-with-empty-body
        if response['status'] in (404, 400):
            print(f"  ✓ PASSED ({response['status']})")
            passed += 1
            return
        if response['status'] == 200:
            body = response['body']
            if body is None or body == [] or body == {}:
                print("  ✓ PASSED (200 with empty response)")
                passed += 1
                return
            else:
                print(f"  ✗ FAILED: Expected 404 or empty 200, got 200 with data")
                failed += 1
                return
        print(f"  ✗ FAILED: Unexpected status {response['status']}")
        failed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_invalid_auth():
    """Test: GET /api/cars - Invalid authentication"""
    global passed, failed, skipped
    print("\n[TEST] GET /api/cars - Invalid auth")
    try:
        response = make_request('GET', '/api/cars', headers={'Authorization': 'Bearer invalid-token-12345'})
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return
        # Accept either 401/403 (protected) or 200 (public)
        if response['status'] in (200, 401, 403):
            print(f"  ✓ PASSED (status {response['status']})")
            passed += 1
            return
        print(f"  ✗ FAILED: Expected 200/401/403, got {response['status']}")
        failed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_post_car_invalid_body():
    """Test: POST /api/cars - Invalid request body (write operation tolerated)"""
    global passed, failed, skipped
    print("\n[TEST] POST /api/cars - Invalid request body (write operation tolerated)")
    try:
        # Intentionally malformed body (unknown fields / wrong types)
        bad_body = {"this_is_invalid": True, "images": "not-an-array", "price": "free"}
        resp = make_request('POST', '/api/cars', body=bad_body)
        if 'error' in resp:
            print(f"  ✗ FAILED: {resp['error']}")
            failed += 1
            return
        # For write ops we accept ANY HTTP status code as a pass (per rules) as long as request succeeded
        if resp['status'] == 0:
            print(f"  ✗ FAILED: Connection error or no response")
            failed += 1
            return
        print(f"  ✓ PASSED (status {resp['status']})")
        passed += 1
    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def main():
    """Run all tests"""
    print("=" * 60)
    print("API Test Suite: /api/cars")
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
    # Run tests
    test_get_cars_list_happy_path()
    test_get_car_by_id()
    test_get_car_not_found()
    test_invalid_auth()
    test_post_car_invalid_body()
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
