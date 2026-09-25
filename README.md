# Fast Simon — New Hire Challenge

## Task I: Hello World

`GET /` returns `"Hello, World!"`

URL: https://fast-simon-task-2026.ey.r.appspot.com/

## Task II: Simple Key-Value Database

Built with FastAPI on App Engine Standard (python312), using Google Cloud Datastore for persistence across requests (each App Engine request may hit a different instance, so in-memory state won't survive).

### State model

A single Datastore entity (`AppState/state`) stores the full app state as JSON: current variables, a count of how many variables equal each value (for O(1) NUMEQUALTO), and undo/redo stacks of applied actions.

### Endpoints

- `GET /set?name=X&value=Y`
- `GET /get?name=X`
- `GET /unset?name=X`
- `GET /numequalto?value=Y`
- `GET /undo`
- `GET /redo`
- `GET /end` — clears all data

### Feature: Transactional consistency

Every command runs inside a single Datastore transaction (read state → mutate → write state). The task description says to ignore multi-client issues, but since all commands share one entity, wrapping each command in a transaction is a small, cheap addition that prevents a lost update if two requests happen to land close together — Datastore will retry one of them instead of silently overwriting data.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

## Deploy

```bash
gcloud app deploy
```

Pushes to `main` also run [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) (smoke test, then deploy). Required GitHub secrets: `GCP_PROJECT_ID`, `GCP_SA_KEY`.

## Future improvements

- Unit tests (pytest) covering all example sequences from the spec.
- Rate limiting / basic auth if this were exposed publicly long-term.
- Structured logging per command for easier debugging.
