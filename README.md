# Django Inventory Manager

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="Django" src="https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white">
  <img alt="DRF" src="https://img.shields.io/badge/DRF-3.15-A30000?logo=django&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white">
  <img alt="Redis" src="https://img.shields.io/badge/Redis-Celery-DC382D?logo=redis&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-deployed-2496ED?logo=docker&logoColor=white">
  <img alt="Tests" src="https://img.shields.io/badge/pytest-90%25%2B-0A9EDC?logo=pytest&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
</p>

A production-grade REST API for inventory and sales operations. JWT-authenticated, < 120 ms endpoint response times, 90%+ test coverage. Celery Beat scheduled jobs handle nightly profit summaries and low-stock alerts. Containerised with Docker + Nginx and deployed on AWS EC2.

---

## Why This Exists

Real small-business inventory pain: counting stock by hand, end-of-day profit math in spreadsheets, no early warning when fast-moving SKUs run low. This API answers four questions a shop owner asks every day:

1. What do I have, and how much of it?
2. What did I sell today, and what did I make on it?
3. What's about to run out?
4. Where did the month go?

Built for solo operators and small retail teams — no enterprise weight, every endpoint testable, every job auditable.

---

## Architecture

```
                ┌────────────────────────────┐
                │  Client (HTTP / JWT)       │
                └──────────────┬─────────────┘
                               │
                ┌──────────────▼─────────────┐
                │  Nginx (reverse proxy)     │
                └──────────────┬─────────────┘
                               │
                ┌──────────────▼─────────────┐
                │  Django + DRF (Gunicorn)   │
                │  • Inventory app           │
                │  • Sales app               │
                │  • Reports app             │
                │  • Accounts (JWT)          │
                └─┬──────────┬───────────────┘
                  │          │
                  │          │
     ┌────────────▼──┐   ┌───▼─────────────────┐
     │ PostgreSQL 17 │   │ Redis (broker +     │
     │ (source of    │   │ result backend)     │
     │  truth)       │   └─────────┬───────────┘
     └───────────────┘             │
                                   │
                       ┌───────────▼──────────┐
                       │  Celery worker       │  ← async tasks
                       │  Celery beat         │  ← schedules nightly
                       └──────────────────────┘     summary + alerts
```

**Runtime path:** Client → Nginx → Gunicorn (Django/DRF) → Postgres (read/write).
**Async path:** Scheduled task → Celery Beat → Redis queue → Worker → Postgres write (DailySummary).

---

## Features

- **Inventory management** — Items with auto-generated SKUs (`NAME-XXXXXX`), categories, purchase prices, and automatic stock status (`in_stock` / `low_stock` / `out_of_stock`) driven by `quantity` vs. `reorder_level`
- **Sales recording** — Multi-line-item sales with per-item profit/revenue/cost calculation; cost prices snapshotted at sale time so reports stay correct when item prices later change
- **Reports** — Daily financial summaries (revenue · cost · profit · units sold) and low-stock alerts
- **JWT authentication** — Access/refresh token pairs via SimpleJWT
- **Background tasks** — Celery + Redis with django-celery-beat for nightly summary generation
- **Admin interface** — Full Django admin for every model
- **Seed commands** — Management commands to populate dev data
- **Test suite** — pytest + factory-boy, 90%+ coverage on models and API

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.0, Django REST Framework 3.15 |
| Auth | SimpleJWT (access + refresh) |
| Database | PostgreSQL 17 |
| Task Queue | Celery 5.4 + Redis |
| Scheduler | django-celery-beat |
| Testing | pytest, pytest-django, factory-boy |
| Config | python-decouple |
| Deploy | Docker, Nginx, AWS EC2 |

---

## Project Structure

```
inventory_manager/
├── config/                  # Django settings, URLs, WSGI, Celery config
│   ├── settings.py
│   ├── celery.py
│   └── urls.py
├── apps/
│   ├── inventory/           # Item model, CRUD API, seed commands
│   ├── sales/               # Sale & SaleItem models, sales API
│   ├── reports/             # DailySummary model, Celery tasks, report endpoints
│   ├── accounts/            # User auth, signals, context processors
│   └── frontend/            # Template-based frontend views
├── templates/               # HTML templates
├── manage.py
├── requirements.txt
└── .env.example
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/token/` | Obtain JWT access + refresh tokens |
| POST | `/api/auth/token/refresh/` | Refresh access token |

### Inventory
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/inventory/items/` | List all items |
| POST | `/api/inventory/items/` | Create item |
| GET | `/api/inventory/items/{id}/` | Retrieve item |
| PUT/PATCH | `/api/inventory/items/{id}/` | Update item |
| DELETE | `/api/inventory/items/{id}/` | Delete item |

### Sales
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/sales/` | List all sales |
| POST | `/api/sales/` | Create sale (with line items) |
| GET | `/api/sales/{id}/` | Retrieve sale |
| PUT/PATCH | `/api/sales/{id}/` | Update sale |
| DELETE | `/api/sales/{id}/` | Delete sale |

### Reports
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/reports/daily/` | Daily financial summaries |
| GET | `/api/reports/low-stock/` | Items at or below reorder level |

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 17
- Redis

### 1. Clone the repository

```bash
git clone https://github.com/davitramishvili/django-inventory-manager.git
cd django-inventory-manager
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=inventory_db
DB_USER=inventory_user
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Set up the database

```bash
# Create the database and user in PostgreSQL
psql -U postgres -c "CREATE DATABASE inventory_db;"
psql -U postgres -c "CREATE USER inventory_user WITH PASSWORD 'yourpassword';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE inventory_db TO inventory_user;"
psql -U postgres -d inventory_db -c "GRANT ALL ON SCHEMA public TO inventory_user;"

# Run migrations
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. (Optional) Seed development data

```bash
python manage.py seed_users
python manage.py seed_data
```

### 8. Start the development server

```bash
python manage.py runserver
```

### 9. Start Celery (requires Redis)

```bash
# Worker
celery -A config worker --loglevel=info

# Beat scheduler (for periodic tasks)
celery -A config beat --loglevel=info
```

---

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=apps --cov-report=term-missing
```

---

## Data Models

### Item
| Field | Type | Notes |
|---|---|---|
| `name` | CharField | |
| `sku` | CharField | Auto-generated if blank (`NAME-XXXXXX`) |
| `category` | CharField | |
| `quantity` | IntegerField | Drives automatic status |
| `reorder_level` | IntegerField | Threshold for `low_stock` |
| `purchase_price` | DecimalField | |
| `currency` | CharField | `GEL` or `USD` |
| `status` | CharField | Auto-set: `in_stock` / `low_stock` / `out_of_stock` |

### Sale
| Field | Type | Notes |
|---|---|---|
| `buyer_name` | CharField | Optional |
| `note` | TextField | Optional |
| `total_revenue` | DecimalField | Calculated from line items |
| `total_cost` | DecimalField | Calculated from line items |
| `total_profit` | DecimalField | `revenue - cost` |
| `currency` | CharField | `GEL` or `USD` |

### SaleItem
| Field | Type | Notes |
|---|---|---|
| `sale` | FK → Sale | |
| `item` | FK → Item | Protected from deletion |
| `quantity` | IntegerField | |
| `sale_price` | DecimalField | Price sold at |
| `cost_price` | DecimalField | Snapshot of purchase price |

### DailySummary
| Field | Type | Notes |
|---|---|---|
| `date` | DateField | Unique per day |
| `total_revenue` | DecimalField | |
| `total_cost` | DecimalField | |
| `total_profit` | DecimalField | |
| `items_sold` | IntegerField | Total units sold that day |

---

## Design Decisions

A few choices worth calling out:

- **Cost-price snapshot on `SaleItem`** — `purchase_price` lives on `Item` and changes when stock is replenished at a different price. To keep historical reports stable, every `SaleItem` stores the `cost_price` *at the moment of sale*. The Item can drift; the sale's profit can't.
- **Status derived, not stored manually** — `Item.status` is computed from `quantity` and `reorder_level` on save. There's no "set to low stock" button — the only thing humans touch is the count.
- **Celery Beat for the summary, not a cron** — running the daily roll-up inside Django (via Celery) means the same code path is testable in pytest with `CELERY_TASK_ALWAYS_EAGER=True`. A system cron calling `manage.py` would have worked, but it splits the app's responsibilities between two systems.
- **`PROTECT` on `SaleItem.item`** — deleting an Item that has historical sales attached would silently destroy financial history. The DB enforces "can't delete an item that's ever been sold." If you really want to, you archive it.
- **Factory-boy over fixtures** — fixtures rot when models change. Factories regenerate matching data on every test run.
- **JWT in cookies vs. headers** — header-based JWT here because this is an API-first project. For the related SaaS (Leri Tracker), I moved to httpOnly cookies after a security audit; that lesson applies if/when this project gets a browser frontend.

---

## What I'd Do Next

Things on the list, in order of value:

1. **OpenAPI / Swagger UI** via `drf-spectacular` — schema is already self-describing from serializers, just needs the renderer wired up.
2. **Multi-currency reports** — currently summaries assume single currency per record. Real shops in Georgia run dual-priced (GEL + USD), so the DailySummary should aggregate per currency.
3. **Audit log** — a generic `AuditEvent` model for who-changed-what-when. Useful the first time a number "looks wrong."
4. **Soft-delete on Item** — paired with the `PROTECT` decision above, archive becomes the default and hard-delete becomes a superuser-only operation.

---

## License

MIT
