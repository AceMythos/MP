# Backend

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Run

```bash
uvicorn app.main:app --app-dir backend --reload
```

## Test

```bash
pytest backend
```
