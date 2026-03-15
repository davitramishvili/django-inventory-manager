# Django Inventory Manager

A full-stack inventory and sales management system built with Django REST Framework. Manages stock levels, records sales, tracks profit margins, and generates daily financial summaries via background tasks.

---

## Features

- **Inventory Management** — Create and manage items with auto-generated SKUs, categories, purchase prices, and automatic stock status (`in_stock`, `low_stock`, `out_of_stock`)
- **Sales Recording** — Log sales with line items, automatic profit/revenue/cost calculation per sale
- **Reports** — Daily financial summaries (revenue, cost, profit, units sold) and low-stock alerts
- **JWT Authentication** — Secure API access using access/refresh token pairs
- **Background Tasks** — Celery + Redis for scheduled daily summary generation
- **Admin Interface** — Full Django admin for all models
- **Seed Commands** — Management commands to populate dev data
- **Test Suite** — pytest with factory-boy for model and API coverage

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.0, Django REST Framework 3.15 |
| Auth | SimpleJWT |
| Database | PostgreSQL 17 |
| Task Queue | Celery 5.4 + Redis |
| Scheduler | django-celery-beat |
| Testing | pytest, pytest-django, factory-boy |
| Config | python-decouple |

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

## License

MIT
