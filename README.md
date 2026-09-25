# Fast Simon Assessment API

FastAPI service on **Google App Engine Standard** (Python 3.12).

## Local development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Endpoints

### `GET /health`

Health check.

```bash
curl http://127.0.0.1:8000/health
```

```json
{"status": "healthy"}
```

### `GET /api/products`

List in-memory products. Optional query parameters:

| Parameter   | Type   | Description                          |
|------------|--------|--------------------------------------|
| `category` | string | Filter by category (case-insensitive)|
| `max_price`| float  | Non-negative; products with `price <= max_price` |

```bash
curl "http://127.0.0.1:8000/api/products?category=apparel&max_price=100"
```

```json
{
  "count": 1,
  "data": [
    {"id": 2, "name": "Cotton T-Shirt", "category": "apparel", "price": 25.0}
  ]
}
```

## Deploy

Pushes to `main` run [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml): smoke test, then `gcloud app deploy`.

Required GitHub repository secrets:

- `GCP_PROJECT_ID` — GCP project id
- `GCP_SA_KEY` — JSON key for a service account with App Engine deploy permissions

Live URL (after deploy): `https://fast-simon-task-2026.ey.r.appspot.com`
