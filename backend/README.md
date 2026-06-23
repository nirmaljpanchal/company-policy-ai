# PolicyChat Backend

FastAPI + SQLAlchemy + PostgreSQL + pgvector RAG backend for company policy questions.

## Local DB

Start PostgreSQL 16 with pgvector extension:

```bash
docker-compose up -d
```

Wait for the healthcheck to pass (10-15s), then run migrations:

```bash
alembic upgrade head
```

To stop the database:

```bash
docker-compose down
```

To stop and remove all data:

```bash
docker-compose down -v
```

## Installation

Create a virtual environment and install dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate venv (Windows Git Bash)
source venv/Scripts/activate

# Or activate venv (Windows PowerShell)
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

Default `.env` values match the local Docker Postgres setup. For production, update:
- `OPENAI_API_KEY`
- `JWT_SECRET` (generate a strong secret)
- `DATABASE_URL` (if not using Docker)

## Seeding an Admin User

Create or update an admin user for local development and testing (no public signup route exists):

```bash
# Via CLI arguments
python -m app.scripts.seed_admin --email admin@example.com --password your_secure_password

# Via environment variables
export SEED_ADMIN_EMAIL=admin@example.com
export SEED_ADMIN_PASSWORD=your_secure_password
python -m app.scripts.seed_admin
```

The command is idempotent — if the email exists, it updates the password and role; otherwise, it creates a new user.

## Running the Application

Ensure the database is running, then start the API server:

```bash
uvicorn app.main:app --reload
```

API will be available at: `http://localhost:8000`

Swagger UI: `http://localhost:8000/docs`

## Health Check

Test the health endpoint to verify DB connectivity:

```bash
curl http://localhost:8000/health
```

Response: `{"status":"ok"}`

## Testing

Run tests with pytest:

```bash
pytest tests/ -v

# Or run specific test
pytest tests/test_health.py -v
```
