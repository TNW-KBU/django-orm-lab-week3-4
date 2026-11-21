"""
Part 6: Advanced Challenge Exercises (Q Objects & F Expressions).

Every function pushes the logic down to the database so that no rows are
loaded into Python memory for filtering/calculation, and no race condition
can occur between a "read" and a "write".
"""
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Q, When
from django.db.models.functions import Round
from django.db.models.lookups import GreaterThan

from .models import Product


class InsufficientStockError(Exception):
    """Raised when a purchase cannot be fulfilled because stock is too low."""


# ---------------------------------------------------------------------------
# Challenge 1: Advanced Conditional Search & Nested Logic (Q Objects)
# ---------------------------------------------------------------------------
def marketing_products():
    """
    (category = 'Electronics' AND price > 10,000)
    OR
    (status = 'DISCOUNTED' AND warehouse_country <> 'China')

    Q objects inside the same Q(...) call are ANDed together, `|` is OR and
    `~` is NOT. The parentheses keep the two AND groups separate, so the
    generated SQL is:
        WHERE (category.name = 'Electronics' AND price > 10000)
           OR (status = 'DISCOUNTED' AND NOT warehouse_country = 'China')
    """
    electronics_high_price = Q(category__name='Electronics') & Q(price__gt=10000)
    discounted_outside_china = Q(status='DISCOUNTED') & ~Q(warehouse_country='China')

    return Product.objects.select_related('category').filter(
        electronics_high_price | discounted_outside_china
    )


# ---------------------------------------------------------------------------
# Challenge 2: Dynamic Stock Threshold Alert (F Expression + Q Object)
# ---------------------------------------------------------------------------
def stock_alert_products():
    """
    stock_quantity <= reorder_level
    OR
    (is_promotional = TRUE AND stock_quantity < reorder_level * 2)

    F('reorder_level') makes the comparison column-to-column, i.e. each row is
    compared against its OWN threshold instead of one fixed number. The
    multiplication `F('reorder_level') * 2` is also evaluated by the database.
    """
    normal_threshold = Q(stock_quantity__lte=F('reorder_level'))
    promo_threshold = Q(is_promotional=True) & Q(stock_quantity__lt=F('reorder_level') * 2)

    return Product.objects.filter(normal_threshold | promo_threshold)


# ---------------------------------------------------------------------------
# Challenge 3: Atomic Price Increase with Safety Ceiling (F + Case/When)
# ---------------------------------------------------------------------------
def increase_gadget_prices(rate=Decimal('1.15')):
    """
    Single bulk UPDATE (no Python loop):

        UPDATE product SET price = CASE
            WHEN price * 1.15 > max_allowed_price THEN max_allowed_price
            ELSE ROUND(price * 1.15, 2)
        END
        WHERE category.name = 'Gadgets'

    Case/When is SQL's CASE expression. Each row's new price is computed from
    its own current price and its own ceiling inside the DB engine, so the
    operation is atomic and safe under concurrency.

    Returns the number of rows updated.
    """
    new_price = F('price') * rate

    return Product.objects.filter(category__name='Gadgets').update(
        price=Case(
            When(GreaterThan(new_price, F('max_allowed_price')),
                 then=F('max_allowed_price')),
            default=Round(new_price, 2),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )


# ---------------------------------------------------------------------------
# Challenge 4: Atomic Purchase Guard Constraint (Race Condition Prevention)
# ---------------------------------------------------------------------------
def purchase_product(product_id, quantity):
    """
    Conditional atomic UPDATE:

        UPDATE product
           SET stock_quantity = stock_quantity - X,
               total_sold     = total_sold + X,
               total_revenue  = total_revenue + (price * X)
         WHERE id = <product_id> AND stock_quantity >= X

    The guard (stock_quantity >= X) lives in the WHERE clause, so the check
    and the write happen in ONE statement. Two concurrent buyers can never
    both pass the check on the same stock, because the second UPDATE is
    evaluated against the already-reduced value. `update()` returns the number
    of affected rows: 0 means the guard failed -> the purchase is rejected.
    """
    if quantity <= 0:
        raise ValueError('Quantity must be a positive integer.')

    updated = Product.objects.filter(
        pk=product_id,
        stock_quantity__gte=quantity,
    ).update(
        stock_quantity=F('stock_quantity') - quantity,
        total_sold=F('total_sold') + quantity,
        total_revenue=F('total_revenue') + F('price') * quantity,
    )

    if updated == 0:
        raise InsufficientStockError(
            f'Purchase of {quantity} unit(s) failed for product id={product_id}: '
            f'insufficient stock or product does not exist.'
        )
    return True
