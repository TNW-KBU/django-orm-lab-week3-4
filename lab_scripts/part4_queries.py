# Part 4: QuerySet API, Advanced Logic, and Optimization
# Run: python manage.py shell -c "exec(open('lab_scripts/part4_queries.py').read())"
# NOTE: connection.queries is only recorded when DEBUG = True.
import django.db
from django.db.models import Q, F
from core.models import Employee, Course

print("=" * 60)
print("Task 4.1: Complex Conditional Lookups with Q Objects")
print("=" * 60)

# Query 1: Find employees in IT department OR earning > $70,000
query_or = Employee.objects.filter(
    Q(department__code="IT") | Q(salary__gt=70000)
)
print("OR Query Results:", list(query_or))

# Query 2: Find employees named "John" AND NOT in HR department
query_not = Employee.objects.filter(
    Q(first_name__icontains="John") & ~Q(department__code="HR")
)
print("AND NOT Query Results:", list(query_not))

print()
print("=" * 60)
print("Task 4.2: Database-Side Calculations with F Expressions")
print("=" * 60)

for emp in Employee.objects.filter(department__code="IT"):
    print(f"{emp.first_name} Old Salary: {emp.salary}")

# Grant a 10% salary increase directly inside the DB engine (Atomic)
Employee.objects.filter(department__code="IT").update(salary=F('salary') * 1.10)

for emp in Employee.objects.filter(department__code="IT"):
    print(f"{emp.first_name} New Salary: {emp.salary}")

print()
print("=" * 60)
print("Task 4.3: Diagnosing and Solving N+1 Query Problem")
print("=" * 60)

print("--- Unoptimized (N+1 Problem) ---")
django.db.reset_queries()
employees = Employee.objects.all()
for emp in employees:
    print(f"Employee: {emp.first_name}, Department: {emp.department.name}")
print(f"Total Queries Executed (Unoptimized): {len(django.db.connection.queries)}")

print()
print("--- Solution 1: select_related() ---")
django.db.reset_queries()
optimized_employees = Employee.objects.select_related('department').all()
for emp in optimized_employees:
    print(f"Employee: {emp.first_name}, Department: {emp.department.name}")
print(f"Total Queries with select_related: {len(django.db.connection.queries)}")

print()
print("--- Solution 2: prefetch_related() ---")
django.db.reset_queries()
courses = Course.objects.prefetch_related('attendees').all()
for course in courses:
    attendee_names = [emp.first_name for emp in course.attendees.all()]
    print(f"Course: {course.code}, Attendees: {', '.join(attendee_names)}")
print(f"Total Queries with prefetch_related: {len(django.db.connection.queries)}")
