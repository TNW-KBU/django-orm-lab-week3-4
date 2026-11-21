from decimal import Decimal

from django.test import TestCase

from .challenges import (
    InsufficientStockError,
    increase_gadget_prices,
    marketing_products,
    purchase_product,
    stock_alert_products,
)
from .models import Category, Product


def make_product(category, **kwargs):
    defaults = dict(
        name='Item', price=Decimal('100.00'), max_allowed_price=Decimal('1000.00'),
        stock_quantity=50, reorder_level=10, is_promotional=False,
        status='NORMAL', warehouse_country='Thailand',
    )
    defaults.update(kwargs)
    return Product.objects.create(category=category, **defaults)


class ChallengeTests(TestCase):
    def setUp(self):
        self.electronics = Category.objects.create(name='Electronics')
        self.gadgets = Category.objects.create(name='Gadgets')
        self.books = Category.objects.create(name='Books')

    def test_challenge1_marketing_products(self):
        laptop = make_product(self.electronics, name='Laptop', price=Decimal('25000'))
        make_product(self.electronics, name='Mouse', price=Decimal('500'))
        novel = make_product(self.books, name='Novel', status='DISCOUNTED', warehouse_country='Japan')
        make_product(self.books, name='Comic', status='DISCOUNTED', warehouse_country='China')
        make_product(self.electronics, name='TV', price=Decimal('10000'))  # not strictly greater

        self.assertEqual(set(marketing_products()), {laptop, novel})

    def test_challenge2_stock_alert(self):
        low = make_product(self.books, name='Low', stock_quantity=10, reorder_level=10)
        promo = make_product(self.books, name='Promo', stock_quantity=15, reorder_level=10, is_promotional=True)
        make_product(self.books, name='PromoOk', stock_quantity=20, reorder_level=10, is_promotional=True)
        make_product(self.books, name='Ok', stock_quantity=15, reorder_level=10)

        self.assertEqual(set(stock_alert_products()), {low, promo})

    def test_challenge3_price_increase_with_ceiling(self):
        normal = make_product(self.gadgets, name='Watch', price=Decimal('100.00'),
                              max_allowed_price=Decimal('200.00'))
        capped = make_product(self.gadgets, name='Drone', price=Decimal('180.00'),
                              max_allowed_price=Decimal('200.00'))
        other = make_product(self.books, name='Book', price=Decimal('100.00'))

        self.assertEqual(increase_gadget_prices(), 2)
        for p in (normal, capped, other):
            p.refresh_from_db()
        self.assertEqual(normal.price, Decimal('115.00'))
        self.assertEqual(capped.price, Decimal('200.00'))   # 207 capped at 200
        self.assertEqual(other.price, Decimal('100.00'))    # other category untouched

    def test_challenge4_purchase_success(self):
        p = make_product(self.gadgets, price=Decimal('250.00'), stock_quantity=5)
        purchase_product(p.pk, 3)
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 2)
        self.assertEqual(p.total_sold, 3)
        self.assertEqual(p.total_revenue, Decimal('750.00'))

    def test_challenge4_purchase_fails_when_insufficient(self):
        p = make_product(self.gadgets, price=Decimal('250.00'), stock_quantity=2)
        with self.assertRaises(InsufficientStockError):
            purchase_product(p.pk, 3)
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 2)
        self.assertEqual(p.total_sold, 0)
        self.assertEqual(p.total_revenue, Decimal('0.00'))
