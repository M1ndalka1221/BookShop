# 📚 BookShop - Django E-Commerce Application

An e-commerce web application for browsing, searching, managing, and purchasing books, built with **Django 5**, **Stripe Checkout**, **Pytest**, and **Docker**.

---

## 🚀 Tech Stack

- **Framework**: Django 5 (Python 3.14)
- **Database**: SQLite / PostgreSQL (Docker ready)
- **Payment Processing**: Stripe Checkout API
- **Testing**: `pytest`, `pytest-django`, `pytest-cov`
- **Containerization**: Docker & Docker Compose
- **Async Processing**: Django Async Views (`asgiref`, `acount`, `aget`)

---

## 🛠️ Getting Started

### Prerequisites

- Python 3.11+
- Virtual environment (`venv`)

### Installation & Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/M1ndalka1221/BookShop.git
   cd BookShop
   ```

2. **Set up virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply migrations & run dev server**:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

---

## 🧪 Testing & Coverage

Run the full automated test suite using `pytest` with coverage reporting:

```powershell
.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing --cov-report=html
```

### Coverage Report Summary
- **Overall Project Coverage**: **94%**
- **Model Coverage (`catalog/models.py`, `users/models.py`)**: **100%**
- **View Coverage (`catalog/views.py`, `catalog/async_views.py`)**: **97% - 100%**
- **Total Test Count**: **48 passing tests**

---

## 🤖 AI Usage

This project was enhanced using AI (Antigravity AI) for Code Review, Test Generation, and Documentation.

### 1. Code Review (`AI_REVIEW.md`)
AI performed a code review on 3 core views:
- **`checkout`**: Optimized DB queries using `bulk_create` / `bulk_update`, moved `send_mail` outside transaction blocks to avoid row locks.
- **`BookListView`**: Fixed $N+1$ queries using `select_related('category')` and added whitespace stripping for queries.
- **`async_order_status`**: Enforced HTTP 404 response on missing resources.

### 2. Prompts Utilized (`AI_PROMPTS.md`)

- **Code Review**:
  > *"Review `checkout` in `catalog/views.py`. Analyze database transaction safety, batch operations, side effects inside transaction atomic blocks, type safety, and docstrings."*
  > *"Review `BookListView` in `catalog/views.py`. Identify N+1 query bottlenecks, query sanitization, and docstrings."*
  > *"Review `async_order_status` in `catalog/async_views.py`. Check HTTP status code compliance on missing resources."*

- **Test Generation**:
  > *"Generate comprehensive pytest unit tests for models (`Book`, `Order`, `OrderItem`, `Category`, `CustomUser`), including `# Generated with AI, reviewed and modified` annotations and achieving coverage $\ge 60\%$."*

- **Documentation**:
  > *"Generate docstrings and type annotations for all views in `catalog/views.py`, `catalog/async_views.py`, and `users/views.py`."*
