# RBAC Security Portal: API Specifications

All endpoints are prefixed with `/api` and expect JSON payloads unless specified otherwise.

---

## 1. Authentication Endpoints

### 1.1 User Login
- **Endpoint**: `POST /api/auth/login`
- **Rate Limit**: Max 10 requests per 15 mins per IP.
- **Payload**:
  ```json
  {
    "username": "superadmin",
    "password": "P@ssw0rd123!"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Login successful",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "superadmin",
      "email": "superadmin@cybersecurity.local"
    }
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: Invalid credentials.
  - `403 Forbidden`: Account suspended.
  - `429 Too Many Requests`: Rate limit reached.

### 1.2 User Logout
- **Endpoint**: `POST /api/auth/logout`
- **Headers**: `Authorization: Bearer <token>`
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Logout successful"
  }
  ```

---

## 2. User Management Endpoints
*All requests require valid `Authorization` header bearer token.*

### 2.1 Fetch Users List
- **Endpoint**: `GET /api/users`
- **Required Permission**: `user:read`
- **Success Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "username": "superadmin",
      "email": "superadmin@cybersecurity.local",
      "status": "active",
      "created_at": "2026-06-18T10:15:43.000Z",
      "updated_at": "2026-06-18T10:15:43.000Z",
      "roles": ["SuperAdmin"]
    }
  ]
  ```

### 2.2 Create User
- **Endpoint**: `POST /api/users`
- **Required Permission**: `user:create`
- **Payload**:
  ```json
  {
    "username": "sec_engineer",
    "email": "engineer@cybersecurity.local",
    "password": "TempP@ssword1!",
    "roles": ["Analyst"]
  }
  ```
- **Success Response (201 Created)**:
  ```json
  {
    "message": "User created successfully",
    "userId": 5
  }
  ```
- **Error Response (409 Conflict)**:
  ```json
  {
    "message": "Username or email already exists"
  }
  ```

### 2.3 Update User
- **Endpoint**: `PUT /api/users/:id`
- **Required Permission**: `user:update`
- **Payload**:
  ```json
  {
    "email": "updated_email@cybersecurity.local",
    "status": "suspended",
    "roles": ["Auditor"]
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "User updated successfully"
  }
  ```

### 2.4 Delete User
- **Endpoint**: `DELETE /api/users/:id`
- **Required Permission**: `user:delete`
- **Success Response (200 OK)**:
  ```json
  {
    "message": "User deleted successfully"
  }
  ```
