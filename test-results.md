# Test Execution Results

Generated: 2026-05-08T12:02:45.331Z

================================================================================

Command: SERVER_PORT=3000 python test-api-kan-45.py
Exit Code: 1

Output:
    Request: POST http://localhost:3000/api/auth/register
    Status: 201
    Body: {"success": true, "data": {"user": {"id": "0a76804a-006b-430a-8565-fcac1426b3ed", "email": "newuser@example.com", "name": "New User", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIwYTc2ODA0YS0wMDZiLTQzMGEtODU2NS1mY2FjMTQyNmIzZWQiLCJlbWFpbCI6Im5ld3VzZXJAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlhdCI6MTc3ODI0MTc2NSwiZXhwIjoxNzc4ODQ2NTY1fQ.Bkbss3Z8F2sl6VZ8FIiRPEjS6APhYliQI-Gaygd5SmM"}}
    Request: POST http://localhost:3000/api/auth/register/nonexistent-xyz-123
    Status: 404
    Body: {"success": false, "error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}
    Request: POST http://localhost:3000/api/auth/register
    Status: 409
    Body: {"success": false, "message": "User with this email already exists", "error": {"code": "CONFLICT"}}
    Request: POST http://localhost:3000/api/auth/login
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "88e5fa1f-7da4-4dd0-81ea-765c7cd6feb6", "email": "testbot@example.com", "name": "Test Bot", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI4OGU1ZmExZi03ZGE0LTRkZDAtODFlYS03NjVjN2NkNmZlYjYiLCJlbWFpbCI6InRlc3Rib3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlhdCI6MTc3ODI0MTc2NSwiZXhwIjoxNzc4ODQ2NTY1fQ.9CTmWf9Ix5apkON5b8KdfmUB2ATCmdFMk7SD_7cgoX4"}}
    Request: POST http://localhost:3000/api/auth/login/nonexistent-xyz-123
    Status: 404
    Body: {"success": false, "error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}
    Request: POST http://localhost:3000/api/auth/login
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "88e5fa1f-7da4-4dd0-81ea-765c7cd6feb6", "email": "testbot@example.com", "name": "Test Bot", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI4OGU1ZmExZi03ZGE0LTRkZDAtODFlYS03NjVjN2NkNmZlYjYiLCJlbWFpbCI6InRlc3Rib3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlhdCI6MTc3ODI0MTc2NSwiZXhwIjoxNzc4ODQ2NTY1fQ.9CTmWf9Ix5apkON5b8KdfmUB2ATCmdFMk7SD_7cgoX4"}}
    Request: GET http://localhost:3000/api/auth/profile
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "88e5fa1f-7da4-4dd0-81ea-765c7cd6feb6", "email": "testbot@example.com", "name": "Test Bot", "role": "USER", "whatsappEnabled": true}}}
    Request: GET http://localhost:3000/api/auth/profile/nonexistent-xyz-123
    Status: 404
    Body: {"success": false, "error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}
    Request: GET http://localhost:3000/api/auth/profile
    Status: 401
    Body: {"success": false, "message": "Invalid or expired token", "error": {"code": "UNAUTHORIZED"}}
    Request: PATCH http://localhost:3000/api/auth/profile
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "88e5fa1f-7da4-4dd0-81ea-765c7cd6feb6", "email": "testbot@example.com", "name": "Test Bot", "role": "USER", "whatsappEnabled": true}}}
    Request: PATCH http://localhost:3000/api/auth/profile/nonexistent-xyz-123
    Status: 404
    Body: {"success": false, "error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}
    Request: PATCH http://localhost:3000/api/auth/profile
    Status: 401
    Body: {"success": false, "message": "Invalid or expired token", "error": {"code": "UNAUTHORIZED"}}
Passed: 11, Failed: 1, Skipped: 0

================================================================================

