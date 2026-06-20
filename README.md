# Cyber-Shield RBAC Cybersecurity Platform

A secure Role-Based Access Control (RBAC) cybersecurity application configured with structured user role mappings, session validation, active token revocation, rate limiting, and standard database-backed audit logging.

## Project Structure

```text
rbac-cybersecurity/
├── database/
│   ├── schema.sql         # Database tables, relationships, and index definitions
│   └── seeds.sql          # Seed scripts with default users, permissions, and roles
├── backend/
│   ├── src/
│   │   ├── config/        # Connection pool configurations and Winston logger setup
│   │   ├── controllers/   # Route actions (Auth, Users registry)
│   │   ├── middlewares/   # JWT verification, RBAC permissions check, Rate Limiters
│   │   ├── routes/        # Router bindings
│   │   ├── app.ts         # Express config
│   │   └── server.ts      # Main network socket listener
│   ├── package.json       # Backend configurations & dev configurations
│   ├── tsconfig.json      # TypeScript compiler specifications
│   └── .env.example       # Port, database configuration guidelines
├── frontend/
│   ├── src/
│   │   ├── App.tsx        # High-fidelity dashboard interface
│   │   ├── index.css      # Vanilla CSS theme and styling variable parameters
│   │   └── main.tsx       # React mounting point
│   ├── index.html         # Portal mounting HTML page
│   └── package.json       # Front-end tooling (React, Router, Vite)
├── docs/
│   ├── architecture.md    # Security threat models and mitigation mechanisms
│   └── api.md             # REST API specifications
└── README.md              # Installation instructions and overview
```

## Quick Start Setup

### 1. Database Setup
1. Log in to your MySQL server instance:
   ```bash
   mysql -u root -p
   ```
2. Import the schema to generate the entities:
   ```sql
   SOURCE database/schema.sql;
   ```
3. Load the initial security seeds:
   ```sql
   SOURCE database/seeds.sql;
   ```

### 2. Backend Initialization
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Setup configuration:
   Copy `.env.example` to `.env` and fill in your database port/user/passwords:
   ```bash
   cp .env.example .env
   ```
4. Run in dev mode:
   ```bash
   npm run dev
   ```

### 3. Frontend Initialization
1. Navigate to the frontend folder:
   ```bash
   cd ../frontend
   ```
2. Install tools:
   ```bash
   npm install
   ```
3. Run the development server locally:
   ```bash
   npm run dev
   ```
