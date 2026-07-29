# Backend automated tests

The test suite uses FastAPI's `TestClient`, pytest, and an isolated in-memory
SQLite database. Each test starts with a fresh schema, so running the suite does
not read or modify the database used by the running Swagger server.

External Solar requests are replaced with a deterministic mock. Policy,
condition, document, category-question, and notification fixtures are created
only inside the test database.

## Run locally

From the repository root:

```powershell
Set-Location backend
python -m pip install -r requirements.txt
python -m pytest
```

For detailed test names and assertion failures:

```powershell
python -m pytest -vv
```

Run one test file:

```powershell
python -m pytest app/tests/test_auth_users_categories.py -vv
```

## Run with Docker

The current Compose file is `backend/compose.yaml`. Build the image first so the
container includes the newest test files:

```powershell
docker compose -f backend/compose.yaml build backend
docker compose -f backend/compose.yaml run --rm backend pytest -vv
```

`docker compose run --rm` creates a separate disposable test container. It does
not send test requests to the already-running Swagger container.

## Static verification

From the `backend` directory:

```powershell
python -m ruff check app scripts
python -m black --check app scripts
python -m compileall -q app scripts
```

## Expected result

pytest exits with code `0` and prints only passed tests. A non-zero exit code or
any `FAILED`/`ERROR` entry means the suite did not complete successfully; the
first traceback identifies the failing request or assertion.
