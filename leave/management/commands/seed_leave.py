"""Load the sample data from the original HTML pages (corrected) into the database.

    python manage.py seed_leave            # sample data + demo logins
    python manage.py seed_leave --no-users # sample data only
    python manage.py seed_leave --reset    # wipe leave data first
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from leave.models import (Department, Employee, LeaveApplication, LeaveRecord, LeaveType, TeamSize)
from leave.permissions import HR_GROUP

DEMO_PASSWORD = "Leave@2026"

DEPARTMENTS = ["IT", "HR", "Finance", "Administration", "Legal", "Procurement", "Marketing"]

# name, gender, email, dept id, manager emp id
EMPLOYEES = [
    ("Shukie Sabr", "F", "shukie.sabr@iuiu.ac.ug", 2, None),
    ("Atu Gilbo", "M", "atu.gilbo@iuiu.ac.ug", 1, None),
    ("Nagie Shadia", "F", "nagie.shadia@iuiu.ac.ug", 1, 2),
    ("Walu Hakim", "M", "walu.hakim@iuiu.ac.ug", 3, None),
    ("Mweh Hamn", "F", "mweh.hamn@iuiu.ac.ug", 4, 6),
    ("Nalu Shamirah", "F", "nalu.shamirah@iuiu.ac.ug", 5, None),
    ("Suna Abdul", "M", "suna.abdul@iuiu.ac.ug", 2, 1),   # email typo in the HTML fixed
    ("Nesser Wai", "M", "nesser.wai@iuiu.ac.ug", 6, 6),
    ("Shanga Shifa", "F", "shanga.shifa@iuiu.ac.ug", 7, 6),
    ("Sseba Jamiri", "M", "sseba.jamiri@iuiu.ac.ug", 3, 4),
    ("Naki Tahia", "F", "naki.tahia@iuiu.ac.ug", 1, 2),
    ("Anoor Abdul", "M", "anoor.abdul@iuiu.ac.ug", 1, 2),
]
HR_EMPLOYEES = [1, 7]  # Shukie and Suna work in HR -> HR Officer role

TEAMS = [(1, 5), (2, 8), (4, 3), (6, 6)]  # manager emp id, team size

# name, description, days/year (working days), gender restriction
LEAVE_TYPES = [
    ("Annual", "Yearly vacation entitlement", 21, ""),
    ("Sick", "Medical or health reasons", 14, ""),
    ("Study", "Exam or academic preparation", 10, ""),
    ("Maternity", "Maternity leave for new mothers", 60, "F"),
    ("Paternity", "Paternity leave for new fathers", 4, "M"),
    ("Emergency", "Urgent unforeseen circumstances", 5, ""),
]

# emp id, type id, start, end, reason, status   (dates moved to 2026; app 7 now uses a male employee)
APPLICATIONS = [
    (3, 1, "2026-06-01", "2026-06-05", "Annual rest", "Approved"),
    (3, 2, "2026-08-10", "2026-08-12", "Flu symptoms", "Pending"),
    (4, 3, "2026-07-14", "2026-07-18", "ACCA exams", "Approved"),
    (5, 4, "2026-09-01", "2026-11-24", "Maternity", "Approved"),
    (7, 2, "2026-06-20", "2026-06-22", "Malaria treatment", "Rejected"),
    (8, 1, "2026-12-20", "2026-12-31", "Christmas holiday", "Pending"),
    (10, 5, "2026-10-01", "2026-10-05", "Newborn care", "Approved"),
    (10, 6, "2026-08-05", "2026-08-06", "Family emergency", "Approved"),
    (11, 1, "2026-11-10", "2026-11-14", "Rest and travel", "Pending"),
    (2, 3, "2026-07-01", "2026-07-03", "AWS certification", "Approved"),
]

# application id, processed by employee id, comment
RECORDS = [(1, 1, ""), (3, 2, ""), (4, 1, ""), (5, 1, "Medical form not attached"),
           (7, 4, ""), (8, 4, ""), (10, 1, "")]


class Command(BaseCommand):
    help = "Load sample leave-management data"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing leave data first")
        parser.add_argument("--no-users", action="store_true", help="Do not create demo login accounts")

    def handle(self, *args, **opts):
        if opts["reset"]:
            for m in (LeaveRecord, LeaveApplication, TeamSize, Employee, LeaveType, Department):
                m.objects.all().delete()
        elif Department.objects.exists() or Employee.objects.exists():
            raise CommandError("Leave data already exists. Use --reset to replace it.")

        depts = {i: Department.objects.create(name=n) for i, n in enumerate(DEPARTMENTS, 1)}
        types = {i: LeaveType.objects.create(name=n, description=d, days_allowed=days, gender_restriction=g)
                 for i, (n, d, days, g) in enumerate(LEAVE_TYPES, 1)}
        emps = {}
        for i, (name, g, email, d, _) in enumerate(EMPLOYEES, 1):
            emps[i] = Employee.objects.create(full_name=name, gender=g, email=email, department=depts[d])
        for i, (*_, mgr) in enumerate(EMPLOYEES, 1):
            if mgr:
                emps[i].manager = emps[mgr]
                emps[i].save(update_fields=["manager"])
        for mgr, size in TEAMS:
            TeamSize.objects.create(manager=emps[mgr], size=size)

        if not opts["no_users"]:
            User = get_user_model()
            hr_group, _ = Group.objects.get_or_create(name=HR_GROUP)
            for i, e in emps.items():
                username = e.email.split("@")[0]
                u, _ = User.objects.get_or_create(username=username, defaults={"email": e.email, "first_name": e.full_name})
                u.set_password(DEMO_PASSWORD)
                u.save()
                e.user = u
                e.save(update_fields=["user"])
                if i in HR_EMPLOYEES:
                    u.groups.add(hr_group)

        apps = {}
        for i, (emp, t, s, e, reason, status) in enumerate(APPLICATIONS, 1):
            apps[i] = LeaveApplication.objects.create(
                employee=emps[emp], leave_type=types[t], start_date=date.fromisoformat(s),
                end_date=date.fromisoformat(e), reason=reason, status=status)
        for app_id, proc, comment in RECORDS:
            a = apps[app_id]
            LeaveRecord.objects.create(application=a, decision=a.status, comments=comment,
                                       processed_by=emps[proc].user)

        if opts["verbosity"] == 0:
            return
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(depts)} departments, {len(emps)} employees, {len(types)} leave types, "
            f"{len(apps)} applications, {len(RECORDS)} records."))
        if not opts["no_users"]:
            self.stdout.write(f"Demo logins: username = email prefix (e.g. shukie.sabr = HR Officer, "
                              f"atu.gilbo = Manager, nagie.shadia = Employee); password = {DEMO_PASSWORD}")
            self.stdout.write(self.style.WARNING("Change or delete these demo accounts before real use."))
