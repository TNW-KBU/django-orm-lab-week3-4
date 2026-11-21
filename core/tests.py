"""
Part 4 functional benchmarks.

Task 4.1  Q objects (&, |, ~)               -> Correct Record Set
Task 4.2  F() expressions with update()     -> 0 Memory Loops (single UPDATE)
Task 4.3  select_related() on ForeignKey    -> Exactly 1 Query
Task 4.4  prefetch_related() on ManyToMany  -> Exactly 2 Queries
"""
from decimal import Decimal

from django.db.models import F, Q
from django.test import TestCase

from .models import Course, Department, Employee, TrainingRecord


class Part4BenchmarkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        hr = Department.objects.create(name="Human Resources", code="HR")
        it = Department.objects.create(name="Information Technology", code="IT")
        fin = Department.objects.create(name="Finance", code="FIN")

        cls.e1 = Employee.objects.create(employee_code="EMP001", first_name="John", last_name="Doe", email="john@example.com", salary=Decimal("65000.00"), department=it)
        cls.e2 = Employee.objects.create(employee_code="EMP002", first_name="Jane", last_name="Smith", email="jane@example.com", salary=Decimal("75000.00"), department=it)
        cls.e3 = Employee.objects.create(employee_code="EMP003", first_name="Alice", last_name="Johnson", email="alice@example.com", salary=Decimal("55000.00"), department=hr)
        cls.e4 = Employee.objects.create(employee_code="EMP004", first_name="Bob", last_name="Brown", email="bob@example.com", salary=Decimal("60000.00"), department=fin)

        c1 = Course.objects.create(code="SEC101", title="Cybersecurity Essentials", capacity=25)
        c2 = Course.objects.create(code="DEV201", title="Advanced Django ORM", capacity=30)

        TrainingRecord.objects.create(employee=cls.e1, course=c1, completion_status="COMPLETED", score=Decimal("88.50"))
        TrainingRecord.objects.create(employee=cls.e1, course=c2, completion_status="IN_PROGRESS")
        TrainingRecord.objects.create(employee=cls.e2, course=c2, completion_status="COMPLETED", score=Decimal("95.00"))
        TrainingRecord.objects.create(employee=cls.e3, course=c1, completion_status="REGISTERED")

    # Task 4.1 -------------------------------------------------------------
    def test_task_4_1_q_or_correct_record_set(self):
        qs = Employee.objects.filter(Q(department__code="IT") | Q(salary__gt=70000))
        self.assertEqual(set(qs), {self.e1, self.e2})

    def test_task_4_1_q_and_not_correct_record_set(self):
        qs = Employee.objects.filter(Q(first_name__icontains="John") & ~Q(department__code="HR"))
        self.assertEqual(list(qs), [self.e1])

    # Task 4.2 -------------------------------------------------------------
    def test_task_4_2_f_expression_single_update_no_python_loop(self):
        # One UPDATE statement, no rows fetched into Python memory.
        with self.assertNumQueries(1) as ctx:
            updated = Employee.objects.filter(department__code="IT").update(salary=F("salary") * Decimal("1.10"))
        self.assertEqual(updated, 2)
        self.assertTrue(ctx.captured_queries[0]["sql"].lstrip().upper().startswith("UPDATE"))

        self.e1.refresh_from_db(); self.e2.refresh_from_db(); self.e3.refresh_from_db()
        self.assertEqual(self.e1.salary, Decimal("71500.00"))
        self.assertEqual(self.e2.salary, Decimal("82500.00"))
        self.assertEqual(self.e3.salary, Decimal("55000.00"))  # HR untouched

    # Task 4.3 -------------------------------------------------------------
    def test_task_4_3_unoptimized_is_n_plus_1(self):
        with self.assertNumQueries(1 + 4):
            [emp.department.name for emp in Employee.objects.all()]

    def test_task_4_3_select_related_exactly_1_query(self):
        with self.assertNumQueries(1):
            names = [emp.department.name for emp in Employee.objects.select_related("department")]
        self.assertEqual(len(names), 4)

    # Task 4.4 -------------------------------------------------------------
    def test_task_4_4_prefetch_related_exactly_2_queries(self):
        with self.assertNumQueries(2):
            result = {c.code: sorted(e.first_name for e in c.attendees.all())
                      for c in Course.objects.prefetch_related("attendees")}
        self.assertEqual(result, {"DEV201": ["Jane", "John"], "SEC101": ["Alice", "John"]})
