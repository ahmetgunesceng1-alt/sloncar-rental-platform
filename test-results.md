# Test Execution Results

Generated: 2026-03-23T12:28:37.122Z

================================================================================

Command: SERVER_PORT=3000 python test-api.py
Exit Code: 0

Output:
============================================================
API Test Suite - Auth Endpoints
============================================================

Checking server connectivity...
✓ Server responding (status 404)


[SETUP] Registering test user: testbot+1774268917@example.com
  → Register status: 201
  ✓ Auth: Got token from register response

[TEST] POST /api/auth/register - Create new user (write op)
  → Status: 201
  ✓ PASSED

[TEST] POST /api/auth/login - Valid credentials
  → Status: 200
  ✓ PASSED (token obtained)

[TEST] POST /api/auth/login - Invalid credentials
  → Status: 401
  ✓ PASSED (401)

[TEST] GET /api/auth/profile - Valid token
  → Status: 200
  ✓ PASSED

[TEST] PATCH /api/auth/profile - Update profile (write op)
  → Patch status: 200
  ✓ PASSED (patch returned success but updated value not visible)

[TEST] GET /api/auth/profile - Invalid token
  → Status: 401
  ✓ PASSED (401)

============================================================
Results: 6 passed, 0 failed, 0 skipped
============================================================

================================================================================

