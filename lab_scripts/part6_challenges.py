# Part 6: Advanced Challenge Exercises - demo run with sample data
# Run: python manage.py shell -c "exec(open('lab_scripts/part6_challenges.py').read())"
from decimal import Decimal

from inventory.challenges import (
    InsufficientStockError, increase_gadget_prices, marketing_products,
    purchase_product, stock_alert_products,
)
from inventory.models import Category, Product

Product.objects.all().delete()
Category.objects.all().delete()

electronics = Category.objects.create(name="Electronics")
gadgets = Category.objects.create(name="Gadgets")
books = Category.objects.create(name="Books")

P = Product.objects.create
P(name="Gaming Laptop", category=electronics, price=Decimal("45000"), max_allowed_price=Decimal("50000"), stock_quantity=8, reorder_level=5, status="NORMAL", warehouse_country="Taiwan")
P(name="USB Cable", category=electronics, price=Decimal("150"), max_allowed_price=Decimal("300"), stock_quantity=200, reorder_level=50, status="DISCOUNTED", warehouse_country="China")
P(name="Bluetooth Speaker", category=electronics, price=Decimal("2500"), max_allowed_price=Decimal("3000"), stock_quantity=12, reorder_level=10, is_promotional=True, status="DISCOUNTED", warehouse_country="Thailand")
P(name="Smart Watch", category=gadgets, price=Decimal("8000"), max_allowed_price=Decimal("10000"), stock_quantity=5, reorder_level=5, status="NORMAL", warehouse_country="China")
P(name="Drone", category=gadgets, price=Decimal("18000"), max_allowed_price=Decimal("20000"), stock_quantity=3, reorder_level=2, status="NORMAL", warehouse_country="Japan")
P(name="Python Book", category=books, price=Decimal("990"), max_allowed_price=Decimal("1200"), stock_quantity=40, reorder_level=10, status="CLEARANCE", warehouse_country="Thailand")

print("=" * 60)
print("Challenge 1: Marketing products (Q objects)")
print("=" * 60)
for p in marketing_products():
    print(f"  {p.name:<18} {p.category.name:<12} {p.price:>10} {p.status:<11} {p.warehouse_country}")

print()
print("=" * 60)
print("Challenge 2: Stock alert list (F + Q)")
print("=" * 60)
for p in stock_alert_products():
    print(f"  {p.name:<18} stock={p.stock_quantity:<4} reorder={p.reorder_level:<4} promo={p.is_promotional}")

print()
print("=" * 60)
print("Challenge 3: +15% Gadgets price with ceiling (F + Case/When)")
print("=" * 60)
for p in Product.objects.filter(category__name="Gadgets"):
    print(f"  BEFORE {p.name:<12} price={p.price:>9}  max={p.max_allowed_price}")
rows = increase_gadget_prices()
print(f"  Rows updated: {rows}")
for p in Product.objects.filter(category__name="Gadgets"):
    print(f"  AFTER  {p.name:<12} price={p.price:>9}  max={p.max_allowed_price}")

print()
print("=" * 60)
print("Challenge 4: Atomic purchase guard")
print("=" * 60)
drone = Product.objects.get(name="Drone")
print(f"  Start: stock={drone.stock_quantity} sold={drone.total_sold} revenue={drone.total_revenue}")
purchase_product(drone.pk, 2)
drone.refresh_from_db()
print(f"  Buy 2 -> OK: stock={drone.stock_quantity} sold={drone.total_sold} revenue={drone.total_revenue}")
try:
    purchase_product(drone.pk, 5)
except InsufficientStockError as exc:
    print(f"  Buy 5 -> REJECTED: {exc}")
drone.refresh_from_db()
print(f"  Final: stock={drone.stock_quantity} sold={drone.total_sold} revenue={drone.total_revenue}")
