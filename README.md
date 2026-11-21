# Lab 3-4: Database Design, Django ORM, and Query Optimization

**Course:** DTI412 Special Topic in Application Development

A Training Management System built with Django 5.2 and SQLite. It covers relational data modeling, migrations, the admin interface, the QuerySet API (Q objects, F expressions) and query optimization (`select_related` / `prefetch_related`). It also includes the advanced challenge exercises on a Product/Inventory schema.

## Project Structure

```
django_labs/
├── manage.py
├── requirements.txt
├── training_system/        # Project settings & URLs
├── core/                   # Training Management System
│   ├── models.py           # Department, Employee, Course, TrainingRecord
│   ├── admin.py            # Customized admin
│   └── tests.py            # Part 4 functional benchmark tests
├── inventory/              # Part 6 challenge exercises
│   ├── models.py           # Category, Product
│   ├── challenges.py       # Challenge 1-4 solutions
│   └── tests.py            # Unit tests for the challenges
└── lab_scripts/
    ├── seed_data.py        # Step 3.5 test data
    ├── part4_queries.py    # Part 4 Q / F / N+1 demonstrations
    └── part6_challenges.py # Part 6 demo with sample products
```

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py shell -c "exec(open('lab_scripts/seed_data.py').read())"
python manage.py runserver           # http://127.0.0.1:8000/admin/
```

Run the Part 4 and Part 6 scripts and the tests:

```powershell
python manage.py shell -c "exec(open('lab_scripts/part4_queries.py').read())"
python manage.py shell -c "exec(open('lab_scripts/part6_challenges.py').read())"
python manage.py test core inventory -v 2
```

## Data Model

| Relationship | Type | Implementation |
|---|---|---|
| Department → Employee | 1:N | `Employee.department = ForeignKey(Department, related_name='employees')` |
| Employee ↔ Course | N:M | `Course.attendees = ManyToManyField(Employee, through='TrainingRecord')` |
| TrainingRecord | Intermediate model | `enrollment_date`, `completion_status`, `score` + `UniqueConstraint(employee, course)` |

The Employee table has composite indexes on (`last_name`, `first_name`) and on `employee_code`.

## Part 4 Results

| Task | Result |
|---|---|
| 4.1 OR query (IT dept OR salary > 70,000) | John Doe, Jane Smith |
| 4.1 AND NOT query (name contains "John" AND NOT HR) | John Doe |
| 4.2 F expression +10% for IT | John 65,000 → 71,500; Jane 75,000 → 82,500 |
| 4.3 Unoptimized loop | **5 queries** (1 + N, N = 4 employees) |
| 4.3 `select_related('department')` | **1 query** (SQL JOIN) |
| 4.3 `prefetch_related('attendees')` | **2 queries** (courses + one batched `IN` query) |

### Part 4 Functional Benchmarks

Verified automatically in [`core/tests.py`](core/tests.py) with `python manage.py test core -v 2`. All tests pass.

| Task ID | Functional Milestone & Query Logic | Target Metric | Verified By | Result |
|---|---|---|---|---|
| Task 4.1 | Complex conditional queries using Q objects with AND (`&`), OR (`\|`) and NOT (`~`) | Correct Record Set | `assertEqual` on the returned employees | ✅ Pass |
| Task 4.2 | Database-side field calculation using `F()` with `update()` | 0 Memory Loops | `assertNumQueries(1)`: a single SQL `UPDATE`, no rows loaded into Python | ✅ Pass |
| Task 4.3 | Eliminate N+1 overhead on ForeignKey using `select_related()` | Exactly 1 Query | `assertNumQueries(1)` (unoptimized baseline = 5) | ✅ Pass |
| Task 4.4 | Optimize Many-to-Many queries using `prefetch_related()` | Exactly 2 Queries | `assertNumQueries(2)` | ✅ Pass |

### Task 4.4: Comparative Analysis

| Optimization Method | Target Relationship | SQL Mechanism | Primary Use Case |
|---|---|---|---|
| `select_related()` | Single-valued (ForeignKey, OneToOne) | One SQL INNER / LEFT JOIN | Accessing parent details (e.g. Employee → Department) |
| `prefetch_related()` | Multi-valued (ManyToMany, Reverse FK) | Two batch queries using an SQL `IN` clause, joined in Python | Accessing collections (e.g. Course → Attendees) |
| Database Indexing | Filter fields (`db_index=True`, `Meta.indexes`) | B-Tree / Hash index lookup | Speeding up `filter()`, `order_by()` and unique lookups |

**Analysis:** In the N+1 problem, one query loads the list of objects and then one more query runs for every row when a related object is accessed. The number of queries grows with the data. `select_related` fixes this for single-valued relations by joining the parent table into the same query. `prefetch_related` is used for multi-valued relations, where a JOIN would duplicate rows. It runs one extra query for all the related rows at once, so the total stays at 2 no matter how many courses there are. Indexes do not reduce the number of queries. They make each `WHERE` or `ORDER BY` lookup faster by avoiding a full table scan.

## Part 6: Advanced Challenge Solutions

All solutions are in [`inventory/challenges.py`](inventory/challenges.py) and tested in [`inventory/tests.py`](inventory/tests.py).

### Challenge 1: Advanced Conditional Search (Q Objects)

```python
electronics_high_price = Q(category__name='Electronics') & Q(price__gt=10000)
discounted_outside_china = Q(status='DISCOUNTED') & ~Q(warehouse_country='China')

Product.objects.select_related('category').filter(
    electronics_high_price | discounted_outside_china
)
```

**Explanation:** `&` means AND, `|` means OR and `~` means NOT. Building each condition as its own Q object keeps the two AND groups apart, so the generated SQL is `WHERE (cat = 'Electronics' AND price > 10000) OR (status = 'DISCOUNTED' AND NOT country = 'China')`. `price__gt` matches "strictly greater than". `select_related('category')` avoids an N+1 problem when the category name is displayed.

### Challenge 2: Dynamic Stock Threshold Alert (F + Q)

```python
normal_threshold = Q(stock_quantity__lte=F('reorder_level'))
promo_threshold = Q(is_promotional=True) & Q(stock_quantity__lt=F('reorder_level') * 2)

Product.objects.filter(normal_threshold | promo_threshold)
```

**Explanation:** `F('reorder_level')` refers to the column value of the same row, so each product is compared with its own threshold rather than one fixed number. The database computes `reorder_level * 2`. No rows are loaded into Python for filtering.

### Challenge 3: Atomic Price Increase with Safety Ceiling (F + Case/When)

```python
new_price = F('price') * Decimal('1.15')

Product.objects.filter(category__name='Gadgets').update(
    price=Case(
        When(GreaterThan(new_price, F('max_allowed_price')), then=F('max_allowed_price')),
        default=Round(new_price, 2),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
)
```

**Explanation:** `Case/When` becomes an SQL `CASE` expression inside a single `UPDATE` statement. For each row, the database calculates `price * 1.15`, compares it with that row's `max_allowed_price`, and writes whichever is lower. There is no Python loop and no read-modify-write gap. Example: 8,000 → 9,200 (under the ceiling), and 18,000 → 20,700, capped at 20,000.

### Challenge 4: Atomic Purchase Guard (Race Condition Prevention)

```python
updated = Product.objects.filter(
    pk=product_id,
    stock_quantity__gte=quantity,          # guard lives in the WHERE clause
).update(
    stock_quantity=F('stock_quantity') - quantity,
    total_sold=F('total_sold') + quantity,
    total_revenue=F('total_revenue') + F('price') * quantity,
)
if updated == 0:
    raise InsufficientStockError(...)
```

**Explanation:** A Python check such as `if product.stock_quantity >= X` followed by `save()` has a race window. Two requests can both read the same stock and both pass the check, which oversells the product. Here the check and the write are one SQL statement: `UPDATE ... SET stock = stock - X ... WHERE id = ? AND stock >= X`. The database applies the WHERE condition atomically, so a second concurrent buyer is evaluated against the already-reduced stock. `update()` returns the number of rows changed, and `0` means the guard failed and the purchase is rejected. Revenue is computed from the row's own current `price` with `F('price') * X`.

## Lab Verification Checklist

- [x] Virtual environment `venv` active and isolated
- [x] Models defined with explicit `ForeignKey` and `ManyToManyField(through=...)`
- [x] Migrations executed without errors (`makemigrations` and `migrate`)
- [x] Admin configured with custom `list_display` and `search_fields`
- [x] Q objects and F() expressions tested in the Django shell
- [x] `select_related()` and `prefetch_related()` applied to eliminate N+1 queries
- [x] Sensitive files (`venv/`, `db.sqlite3`) excluded via `.gitignore`
- [x] Source code pushed to GitHub
- [x] Part 4 functional benchmarks verified by unit tests (6/6 passing)
- [x] Part 6 bonus challenges solved and covered by unit tests (5/5 passing)
