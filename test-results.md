# Test Execution Results

Generated: 2026-04-13T17:34:38.506Z

================================================================================

Command: SERVER_PORT=3000 python test-api-kan-45.py
Exit Code: 1

Output:
    Request: POST http://localhost:3000/api/auth/register
    Status: 201
    Body: {"success": true, "data": {"user": {"id": "709872b8-7cc6-467b-a8de-458d262cc8d3", "email": "newuser@example.com", "name": "New User", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI3MDk4NzJiOC03Y2M2LTQ2N2ItYThkZS00NThkMjYyY2M4ZDMiLCJlbWFpbCI6Im5ld3VzZXJAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlhdCI6MTc3NjEwMTY3OCwiZXhwIjoxNzc2NzA2NDc4fQ.HGZnose54UGCzDLyMsHWwsjxXD6e5mjrKhlnC3paUd4"}}
    Request: POST http://localhost:3000/api/auth/register/nonexistent-xyz-123
    Status: 404
    Body: {"success": false, "error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}
    Request: POST http://localhost:3000/api/auth/register
    Status: 409
    Body: {"success": false, "message": "User with this email already exists", "error": {"code": "CONFLICT"}}
    Request: POST http://localhost:3000/api/auth/login
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "3f41e1b6-e595-4682-93a8-695205abcebb", "email": "testbot@example.com", "name": "Test Bot", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIzZjQxZTFiNi1lNTk1LTQ2ODItOTNhOC02OTUyMDVhYmNlYmIiLCJlbWFpbCI6InRlc3Rib3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlhdCI6MTc3NjEwMTY3OCwiZXhwIjoxNzc2NzA2NDc4fQ.080DiJVhxTPyXUgnatDwpRgjkLWpNrLd80MgtKBjbuA"}}
    Request: POST http://localhost:3000/api/auth/login/nonexistent-xyz-123
    Status: 404
    Body: {"success": false, "error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}
    Request: POST http://localhost:3000/api/auth/login
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "3f41e1b6-e595-4682-93a8-695205abcebb", "email": "testbot@example.com", "name": "Test Bot", "role": "USER"}, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIzZjQxZTFiNi1lNTk1LTQ2ODItOTNhOC02OTUyMDVhYmNlYmIiLCJlbWFpbCI6InRlc3Rib3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlhdCI6MTc3NjEwMTY3OCwiZXhwIjoxNzc2NzA2NDc4fQ.080DiJVhxTPyXUgnatDwpRgjkLWpNrLd80MgtKBjbuA"}}
    Request: GET http://localhost:3000/api/auth/profile
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "3f41e1b6-e595-4682-93a8-695205abcebb", "email": "testbot@example.com", "name": "Test Bot", "role": "USER", "whatsappEnabled": true}}}
    Request: GET http://localhost:3000/api/auth/profile/nonexistent-xyz-123
    Status: 404
    Body: {"success": false, "error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}
    Request: GET http://localhost:3000/api/auth/profile
    Status: 401
    Body: {"success": false, "message": "Invalid or expired token", "error": {"code": "UNAUTHORIZED"}}
    Request: PATCH http://localhost:3000/api/auth/profile
    Status: 200
    Body: {"success": true, "data": {"user": {"id": "3f41e1b6-e595-4682-93a8-695205abcebb", "email": "testbot@example.com", "name": "Test Bot", "role": "USER", "whatsappEnabled": true}}}
    Request: PATCH http://localhost:3000/api/auth/profile/nonexistent-xyz-123
    Status: 404
    Body: {"success": false, "error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}
    Request: PATCH http://localhost:3000/api/auth/profile
    Status: 401
    Body: {"success": false, "message": "Invalid or expired token", "error": {"code": "UNAUTHORIZED"}}
Passed: 11, Failed: 1, Skipped: 0

================================================================================

