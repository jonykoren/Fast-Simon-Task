# Fast Simon — New Hire Challenge

A two-part take-home assessment: a "Hello World" app on Google App Engine, and a small persistent key-value database exposed over HTTP, built for Fast Simon's engineering hiring process.

**Live app:** https://fast-simon-task-2026.ey.r.appspot.com/
**Repository:** https://github.com/jonykoren/Fast-Simon-Task

---

## What this project does (plain-language overview)

This is a tiny web server with two parts:

1. **Task I** — a page that says "Hello, World!" when you visit it, deployed to Google's cloud.
2. **Task II** — a simple database you talk to using web addresses (URLs) instead of a query language. You can set variables, read them back, undo/redo changes, and count how many variables share a value — all by visiting specific URLs in a browser or with `curl`.

Everything is written in Python, runs on **Google App Engine** (Google's serverless hosting), and stores its data in **Google Cloud Datastore** so nothing is lost between requests.

---

## Task I — Hello World

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/` |
| **Response** | `Hello, World!` (plain text) |
| **Live example** | https://fast-simon-task-2026.ey.r.appspot.com/ |

Built per Google's official [App Engine Standard Python 3 quickstart](https://cloud.google.com/appengine/docs/standard/python3/quickstart).

---

## Task II — Simple Key-Value Database

### Why Datastore, not just a Python dictionary?

App Engine can run multiple instances of the app, and any instance can handle any request. A plain Python variable would reset or be inconsistent between requests. **Google Cloud Datastore** is a managed database that all instances share, so state survives and stays consistent no matter which instance answers a request.

### How the data is stored

Everything lives in **one Datastore entity** (`AppState/state`), holding a single JSON blob with:

| Field | Purpose |
|---|---|
| `variables` | current name → value pairs |
| `value_counts` | how many variables currently equal each value (makes `NUMEQUALTO` instant, no scanning) |
| `undo_stack` | history of applied SET/UNSET actions, most recent last |
| `redo_stack` | actions undone and available to redo |

Every command **reads, changes, and writes back this one entity inside a single Datastore transaction** — see [Extra Feature](#extra-feature--transactional-consistency) below.

### Endpoints

All endpoints are `GET` requests and return **plain text** (not JSON), matching the original command-line-style spec.

#### `GET /set?name={name}&value={value}`
Sets `name` to `value`. Overwrites any existing value.

| Example request | Response |
|---|---|
| `/set?name=x&value=10` | `x = 10` |

---

#### `GET /get?name={name}`
Returns the current value of `name`, or `None` if it was never set / has been unset.

| Example request | Response |
|---|---|
| `/get?name=x` | `10` |
| `/get?name=missing` | `None` |

---

#### `GET /unset?name={name}`
Removes `name` entirely, as if it was never set.

| Example request | Response |
|---|---|
| `/unset?name=x` | `x = None` |

---

#### `GET /numequalto?value={value}`
Counts how many variables currently equal `value`. Returns `0` if none do. Runs in constant time (no scanning), via the `value_counts` field.

| Example request | Response |
|---|---|
| `/numequalto?value=10` | `2` |

---

#### `GET /undo`
Reverses the most recent SET or UNSET. Repeated calls undo further back in history, in reverse order.

| Example request | Response |
|---|---|
| `/undo` | `x = 10` *(shows the variable's value after undoing)* |
| `/undo` *(nothing left to undo)* | `NO COMMANDS` |

---

#### `GET /redo`
Re-applies the most recently undone command. Repeated calls redo further forward, in original order. **Any new SET/UNSET clears the redo history** (you can't redo "around" a new change).

| Example request | Response |
|---|---|
| `/redo` | `x = 40` |
| `/redo` *(nothing left to redo)* | `NO COMMANDS` |

---

#### `GET /end`
Deletes **all** stored data — every variable and the full undo/redo history. It queries every `AppState` entity in Datastore and deletes them, so nothing is left behind. This is always the last command sent in a session.

| Example request | Response |
|---|---|
| `/end` | `CLEANED` |

---

### Full worked example (taken directly from the spec, verified against production)
```
GET /set?name=a&value=10 → a = 10
GET /set?name=b&value=20 → b = 20
GET /get?name=a → 10
GET /get?name=b → 20
GET /undo → b = None
GET /get?name=a → 10
GET /get?name=b → None
GET /set?name=a&value=40 → a = 40
GET /get?name=a → 40
GET /undo → a = 10
GET /get?name=a → 10
GET /undo → a = None
GET /get?name=a → None
GET /undo → NO COMMANDS
GET /redo → a = 10
GET /redo → a = 40
```


You can paste any of these directly into a browser, prefixed with the live URL, e.g.:
`https://fast-simon-task-2026.ey.r.appspot.com/set?name=a&value=10`

---

### Extra feature — Transactional consistency

**What it is:** every state command (`SET`, `GET`, `UNSET`, `NUMEQUALTO`, `UNDO`, `REDO`) runs inside one Datastore transaction: read the current state → apply the change → write the new state back, atomically. (`END` is a teardown command — it deletes every `AppState` entity outright.)

**Why it matters:** the spec says it's fine to ignore multi-client issues, but since *all* commands touch the same single entity, this was a small, essentially free addition. Without it, two requests arriving at almost the same moment could each read the old state, make their own change, and the second write would silently erase the first ("lost update"). With the transaction, Datastore detects the conflict and automatically retries one of them — so no update is ever silently lost, at no extra cost in code complexity.

---

## Interactive API explorer

FastAPI auto-generates a Swagger UI at [`/docs`](https://fast-simon-task-2026.ey.r.appspot.com/docs) — you can try every endpoint directly from the browser without `curl`.

---

## Project structure
```
fast-simon-task/
├── main.py # the FastAPI app — all 8 endpoints + Datastore logic
├── app.yaml # App Engine config (runtime, scaling, startup command)
├── requirements.txt # Python dependencies (pinned versions)
├── README.md # this file
├── .gcloudignore # files excluded from gcloud app deploy uploads
├── .gitignore # files excluded from git
└── .github/
└── workflows/
└── deploy.yml # auto-deploys to App Engine on every push to main
```


---

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

Then test with:
```bash
curl "http://127.0.0.1:8080/set?name=x&value=1"
```

## Deploying

**Manual:**
```bash
gcloud app deploy
```

**Automatic:** every push to `main` triggers [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml), which installs dependencies, runs a basic smoke test, authenticates to GCP, and deploys. Requires two repository secrets: `GCP_PROJECT_ID` and `GCP_SA_KEY` (a service account key with App Engine deploy permissions).

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Web framework | **FastAPI** | Modern, type-hint-driven, async-ready, automatic input parsing |
| Server | **gunicorn + uvicorn worker** | Required to run FastAPI's ASGI interface on App Engine Standard |
| Hosting | **App Engine Standard**, `python312` | Matches the assignment's requirement |
| Data storage | **Google Cloud Datastore** | Shared, durable state across App Engine instances; naturally fits key-value access patterns |

## Known limitations & future improvements

- **No automated tests yet** — all sequences from the spec were verified manually with `curl` against both local and production. Adding `pytest` coverage for all example sequences would be the next step.
- **Input validation** — missing or malformed query parameters return a plain-text `400` error (via a custom `RequestValidationError` handler), consistent with the rest of the API's plain-text responses.
- **CI smoke test is basic** — it only confirms the app imports correctly, not that the command sequences behave correctly. A next step would be running the example sequences as part of CI before deploying.
- Possible additions if this were a long-lived service: rate limiting, authentication, structured per-command logging.