# Local Engineering Research Resource Hub Backend

This is the backend for the Local Engineering Research Resource Hub, built with FastAPI, PostgreSQL, and Firebase Storage.

## Features
- User authentication (JWT, OAuth-ready)
- Research upload, browse, search, and download
- Multi-category tagging system (core and student-suggested, with moderation)
- Tag suggestion and approval workflow
- Advanced filtering and full-text search
- File storage with Firebase
- **Notifications system** (user alerts, system messages)
- **Resource management** (guides, templates, etc.)
- **Structured logging** (file and console)
- **Email integration stub** (easy to connect SendGrid/Mailgun)
- **ElasticSearch integration stub** (future full-text search)

## Setup Instructions

### 1. Clone the repository

### 2. Create a virtual environment and install dependencies
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the `app/` directory with the following:
```
DATABASE_URL=postgresql+psycopg2://user:password@localhost/research_hub
FIREBASE_CRED_PATH=path/to/firebase_credentials.json
FIREBASE_STORAGE_BUCKET=your-firebase-bucket-name
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REDIS_URL=redis://localhost:6379/0
```

### 4. Run Database Migrations
(Coming soon: Alembic or manual migration steps)

### 5. Start the FastAPI Server
```
uvicorn app.main:app --reload
```

## Folder Structure
- `app/` - Main application code
  - `models.py` - SQLAlchemy models (User, ResearchSubmission, Tag, Notification, Resource, etc.)
  - `schemas.py` - Pydantic schemas for request/response validation
  - `crud.py` - Business logic and DB operations
  - `routers/` - API endpoints (users, research, tags, notifications, resources)
  - `utils.py` - Utility functions (email, ElasticSearch stub, etc.)
  - `firebase_utils.py` - Firebase file storage integration
  - `main.py` - FastAPI app, logging, error handling
- `tests/` - Unit and integration tests (pytest)
- `requirements.txt` - Python dependencies

## Main API Endpoints

### Authentication & Users
- `POST /register` — Register a new user
- `POST /login` — Login and receive JWT

### Research Submission
- `POST /submissions` — Upload a new research submission (PDF + metadata + tags)
- `GET /submissions/{id}` — Get details of a submission
- `GET /submissions` — List all submissions

### Tagging System
- `GET /tags` — List all tags (with filters)
- `POST /tags` — Suggest a new tag
- `PATCH /tags/{id}/approve` — Approve a pending tag (admin)
- `PATCH /tags/{id}/reject` — Reject a pending tag (admin)

### Notifications
- `POST /notifications/` — Create a notification
- `GET /notifications/` — List notifications for a user (with pagination)
- `PATCH /notifications/{id}/read` — Mark as read/unread
- `DELETE /notifications/{id}` — Delete a notification

### Resources (Guides, Templates, etc.)
- `POST /resources/` — Create a resource (guide, template, etc.)
- `GET /resources/` — List resources (with filters)
- `GET /resources/{id}` — Get resource details
- `PUT /resources/{id}` — Update a resource
- `DELETE /resources/{id}` — Delete a resource

### Library & Discovery
- `GET /library/browse` — Browse research with advanced filters (department, year, supervisor, tags, status, pagination)
- `GET /library/search` — Full-text search with filters and pagination
- `GET /library/{submission_id}/download` — Download a research file

## Tagging System
- Multi-level, multi-category tags (department, subject area, method, application, technology)
- Core (faculty-approved) and student-suggested tags
- Tag moderation workflow (pending, approved, rejected)
- Tags can be associated with research submissions and resources for advanced filtering and discovery

## Logging, Monitoring, and Extensibility
- Structured logging to both file (`app.log`) and console for easy debugging and monitoring
- Global error handlers for HTTP and generic exceptions
- Sentry integration stub for future monitoring
- Email sending is abstracted for easy integration with any provider
- ElasticSearch search logic is stubbed for future full-text search

## Code Annotations & Auditability
- All major modules and functions are documented with docstrings
- Business logic is separated from API endpoints for clarity and testability
- Pydantic schemas enforce input validation and provide OpenAPI documentation
- Utility functions are clearly marked and ready for extension
- Test suite provided for endpoints and core logic (see `tests/`)
- Codebase is organized for easy audit and onboarding of new developers

## Next Steps
- Add admin dashboard, notifications UI, and resource guides frontend
- Integrate AI-powered tag suggestion and search (future)
- Add production-ready deployment and monitoring

## User Onboarding & Authentication Flow

This backend implements a robust, secure, and extensible onboarding and authentication system for the ARB Research Hub. Below is a summary for developers:

### Core Endpoints
- `POST /register` — User registration with full validation and field-specific error messages.
- `GET /verify-email?token=...` — Email verification via secure, time-limited token.
- `POST /resend-verification` — Resend verification email for pending accounts.
- `POST /login` — Login with email or Matric Number, rate-limited, returns JWT and first/last login info.
- `POST /forgot-password` — Initiate password reset, sends secure, time-limited reset token to email.
- `POST /reset-password` — Reset password using token, with strength and match validation.

### Validation & Security
- **Registration:**
  - All required fields checked (name, email, matric/faculty ID, department, password, confirm password).
  - Matric Number/Faculty ID: 9-digit format enforced.
  - Department: Must be one of 10 recognized engineering departments.
  - Password: Minimum 8 chars, must include uppercase, lowercase, number, special character.
  - Duplicate email/ID checks.
  - Field-specific error messages for all validation failures.
- **Email Verification:**
  - Secure, time-limited token; account status updated on verification.
  - Handles expired/invalid tokens and already-verified accounts.
- **Login:**
  - Checks credentials, account status (`is_verified`, `is_active`, `account_status='active'`).
  - Rate limiting: 5 attempts per IP per 10 minutes.
  - Returns JWT and onboarding info (`first_login`, `last_login`).
- **Password Reset:**
  - Secure, time-limited reset tokens; generic responses to prevent user enumeration.
  - Password strength and match enforced on reset.
- **Protected Endpoints:**
  - All sensitive actions (upload, create, update, delete, notifications, tags) require valid JWT.

### Extensibility & Best Practices
- **Role-based access:** User model supports roles; endpoints can be extended for RBAC.
- **Profile updates:** Structure supports future addition.
- **Admin/monitoring:** Can be added as needed.
- **Production email:** Email sending is a stub, ready for integration with a real provider.
- **All code is annotated and auditable for future developers.**

For database migrations after model changes, see the section above.

## Database Migration After Model Changes

If you modify the database models (e.g., add fields like `verification_token` and `verification_token_expiry` to the User model), you must update your database schema. Here are two common approaches:

### 1. Manual Migration (for SQLite or simple setups)

1. Backup your database file (if using SQLite):
   ```sh
   cp app.db app_backup.db
   ```
2. Open a Python shell in your project directory:
   ```sh
   python
   ```
3. Run the following commands to update the schema:
   ```python
   from app.database import Base, engine
   Base.metadata.create_all(bind=engine)
   ```
   This will add new columns to existing tables if they do not exist (non-destructive for SQLite).

### 2. Alembic Migration (for production/complex setups)

If you use Alembic for migrations:

1. Generate a new migration script:
   ```sh
   alembic revision --autogenerate -m "Add verification_token fields to User"
   ```
2. Review and edit the generated migration script if needed.
3. Apply the migration:
   ```sh
   alembic upgrade head
   ```

**Note:** Always backup your database before running migrations in production.

If you add new fields (e.g., `account_status` to the User model), repeat the migration steps above to update your schema. For Alembic, generate a new migration script and apply it as described.

## Environment Variables
See `.env.example` for all required variables. Key variables:
- DATABASE_URL
- FIREBASE_CRED_PATH
- FIREBASE_STORAGE_BUCKET
- JWT_SECRET_KEY
- JWT_ALGORITHM
- ACCESS_TOKEN_EXPIRE_MINUTES
- REDIS_URL

## Running Tests
Tests are async and use pytest + httpx.AsyncClient:
```
pytest
```
Ensure you have a test database and Redis running for full coverage.

## Rate Limiting
Login endpoints use Redis for rate limiting. Set `REDIS_URL` in your environment.

## Background Tasks
Email sending is offloaded to FastAPI BackgroundTasks for non-blocking performance.

## Contributing
See `CONTRIBUTING.md` for guidelines on code style, PRs, and onboarding.

## Production Deployment
- Use a production-ready ASGI server (e.g., uvicorn with --workers, gunicorn with uvicorn workers)
- Set secure environment variables
- Use a managed PostgreSQL and Redis instance
- Configure CORS for trusted domains only
- Set up HTTPS and monitoring (Sentry, etc.)

## Async Testing
- All tests use `pytest-asyncio` and `httpx.AsyncClient` for async endpoint testing.
- To run tests:
  ```bash
  pip install pytest pytest-asyncio httpx
  pytest
  ```
- Ensure you have a test database configured. You may need to set a separate `DATABASE_URL` for tests.
- Example async test:
  ```python
  import pytest
  from httpx import AsyncClient
  from app.main import app

  @pytest.mark.asyncio
  async def test_example():
      async with AsyncClient(app=app, base_url="http://test") as ac:
          response = await ac.get("/api/dashboard/welcome")
      assert response.status_code == 200
  ```

## Developer Notes
- All routers, dependencies, and CRUD functions are async.
- Use the centralized `settings` for all config.
- For new features, follow the async pattern and update tests accordingly.

## Contributing
- See `CONTRIBUTING.md` for guidelines (add if not present).
- Use `.env.example` as a template for your environment variables.

---
For any questions, please refer to the code comments and docstrings, or contact the maintainers. 