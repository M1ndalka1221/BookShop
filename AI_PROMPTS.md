# AI Prompts Log - BookShop Project

This document records the list of AI prompts utilized throughout the **BookShop** project for AI Code Review, Test Generation, and Documentation generation.

---

## 1. Code Review Prompts

### Prompt 1.1: `checkout` View Review
> **Prompt**:
> "Review the `checkout` function in `catalog/views.py`. Analyze database transaction safety, batch database operations, network calls inside `transaction.atomic()`, Stripe integration handling, type safety, and docstrings. Provide refactoring recommendations and improved code."

### Prompt 1.2: `BookListView` Review
> **Prompt**:
> "Review `BookListView` in `catalog/views.py`. Identify performance bottlenecks such as N+1 query problems when accessing category relations, query string sanitization, type annotations, and docstring formatting. Provide improved code."

### Prompt 1.3: `async_order_status` Review
> **Prompt**:
> "Review the asynchronous view `async_order_status` in `catalog/async_views.py`. Check HTTP status code compliance for missing resources, async ORM usage, type hints, and docstring quality."

---

## 2. Test Generation Prompts

### Prompt 2.1: Model Unit Test Generation
> **Prompt**:
> "Generate comprehensive pytest unit tests for the Django models `Category`, `Book`, `Order`, `OrderItem`, and `CustomUser`. Cover string representations (`__str__`), default field values, custom methods (`get_cost`), meta ordering options, and edge cases. Include the comment `# Generated with AI, reviewed and modified` at the top of each test file and maintain code coverage $\ge 60\%$."

### Prompt 2.2: Async Views Test Extension
> **Prompt**:
> "Generate pytest tests for async views in `catalog/tests/test_async_views.py`, specifically testing the HTTP 404 response when querying a non-existent order in `async_order_status`."

---

## 3. Documentation Prompts

### Prompt 3.1: View Docstring Generation
> **Prompt**:
> "Generate Google-style docstrings and PEP 484 type annotations for all class-based and function-based views across `catalog/views.py`, `catalog/async_views.py`, and `users/views.py`."

### Prompt 3.2: README & AI Usage Section Update
> **Prompt**:
> "Generate an updated `README.md` for the BookShop project including a project overview, technical stack, setup instructions, testing guide with pytest and coverage reporting, and a dedicated 'AI Usage' section detailing the prompts used."
