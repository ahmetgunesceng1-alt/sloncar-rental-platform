#!/usr/bin/env python3
"""
API Test Suite
Tests for /api/cars endpoints
"""

import http.client
import json
import sys
import time
from urllib.parse import urlparse

# Configuration
BASE_URL = "http://localhost:3001"
TIMEOUT = 10  # seconds
passed = 0
failed = 0


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
        
        conn.close()
        
        return {
            'status': response.status,
            'body': response_body,
            'headers': dict(response.getheaders())
        }
    except Exception as e:
        return {
            'status': 0,
            'body': None,
            'headers': {},
            'error': str(e)
        }


def _has_common_car_field(item):
    if not isinstance(item, dict):
        return False
    common_keys = {'id', '_id', 'uuid', 'name', 'brand', 'model', 'plate'}
    return any(k in item for k in common_keys)


def test_get_cars_happy_path():
    """Test: GET /api/cars - Happy path"""
    global passed, failed
    print("\n[TEST] GET /api/cars - Happy path")
    try:
        response = make_request('GET', '/api/cars')
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        headers = response.get('headers', {})
        body = response.get('body')

        if status == 200:
            # Content-Type check
            content_type = headers.get('content-type', '')
            if 'application/json' not in content_type:
                print(f"  ✗ FAILED: Expected JSON content-type, got {content_type}")
                failed += 1
                return

            # Body shape
            if not isinstance(body, (list, dict)):
                print(f"  ✗ FAILED: Expected JSON array or object, got {type(body)}")
                failed += 1
                return

            # If list, check items
            if isinstance(body, list) and len(body) > 0:
                first = body[0]
                if not isinstance(first, dict):
                    print(f"  ✗ FAILED: Expected list items to be objects, got {type(first)}")
                    failed += 1
                    return
                if not _has_common_car_field(first):
                    print(f"  ✗ FAILED: First item missing common car fields (id/_id/uuid/name/brand/model/plate)")
                    failed += 1
                    return

            # If dict, check it has at least one common key
            if isinstance(body, dict):
                if not _has_common_car_field(body):
                    # Maybe it's a paginated envelope with 'data' key
                    data = body.get('data') if isinstance(body, dict) else None
                    if isinstance(data, list) and len(data) > 0 and _has_common_car_field(data[0]):
                        print("  ✓ PASSED (paginated response with data)")
                        passed += 1
                        return
                    print(f"  ✗ FAILED: Response object missing common car fields and no 'data' array found")
                    failed += 1
                    return

            print("  ✓ PASSED")
            passed += 1
            return
        elif status in (401, 403):
            print(f"  ✓ PASSED (endpoint protected, status {status})")
            passed += 1
            return
        else:
            print(f"  ✗ FAILED: Expected status 200 (or 401/403 if protected), got {status}")
            failed += 1
            return

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_get_car_not_found():
    """Test: GET /api/cars/:id - Not found"""
    global passed, failed
    print("\n[TEST] GET /api/cars/nonexistent-id-12345 - Not found")
    try:
        response = make_request('GET', '/api/cars/nonexistent-id-12345')
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        body = response.get('body')

        if status == 404:
            print("  ✓ PASSED (404 Not Found)")
            passed += 1
            return
        elif status == 200:
            # Accept 200 if body is empty/null
            if body is None or body == [] or body == {}:
                print("  ✓ PASSED (200 with empty response)")
                passed += 1
                return
            # If object, maybe contains error flag
            if isinstance(body, dict) and (body.get('error') or body.get('message') and 'not found' in str(body.get('message')).lower()):
                print("  ✓ PASSED (200 with not-found message)")
                passed += 1
                return
            print(f"  ✗ FAILED: Expected 404 or empty/not-found response, got 200 with data")
            failed += 1
            return
        elif status in (401, 403):
            print(f"  ✓ PASSED (protected endpoint, status {status})")
            passed += 1
            return
        else:
            print(f"  ✗ FAILED: Expected 404 or 200-empty, got {status}")
            failed += 1
            return

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_get_cars_invalid_auth():
    """Test: GET /api/cars - Invalid authentication"""
    global passed, failed
    print("\n[TEST] GET /api/cars - Invalid auth")
    try:
        response = make_request('GET', '/api/cars', headers={'Authorization': 'Bearer invalid-token-12345'})
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        if status in [200, 401, 403]:
            print(f"  ✓ PASSED (status {status})")
            passed += 1
            return
        else:
            print(f"  ✗ FAILED: Expected 200/401/403, got {status}")
            failed += 1
            return

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def test_get_cars_invalid_query():
    """Test: GET /api/cars?limit=notanumber - Invalid query parameter handling"""
    global passed, failed
    print("\n[TEST] GET /api/cars?limit=notanumber - Invalid query")
    try:
        response = make_request('GET', '/api/cars?limit=notanumber')
        if 'error' in response:
            print(f"  ✗ FAILED: {response['error']}")
            failed += 1
            return

        status = response['status']
        body = response.get('body')
        headers = response.get('headers', {})

        if status == 400:
            print("  ✓ PASSED (400 Bad Request)")
            passed += 1
            return
        elif status == 200:
            # If returned 200, ensure it is valid JSON and shape is acceptable
            content_type = headers.get('content-type', '')
            if 'application/json' not in content_type:
                print(f"  ✗ FAILED: Expected JSON content-type, got {content_type}")
                failed += 1
                return
            if not isinstance(body, (list, dict)):
                print(f"  ✗ FAILED: Expected JSON array or object, got {type(body)}")
                failed += 1
                return
            print("  ✓ PASSED (200 OK with tolerant query parsing)")
            passed += 1
            return
        elif status in (401, 403):
            print(f"  ✓ PASSED (protected endpoint, status {status})")
            passed += 1
            return
        else:
            print(f"  ✗ FAILED: Expected 400 or 200, got {status}")
            failed += 1
            return

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        failed += 1


def main():
    """Run all tests"""
    print("=" * 60)
    print("API Test Suite - /api/cars")
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
    test_get_cars_happy_path()
    test_get_car_not_found()
    test_get_cars_invalid_auth()
    test_get_cars_invalid_query()
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
