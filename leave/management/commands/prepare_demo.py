import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from leave.models import Department, Employee


class Command(BaseCommand):
    help = "Prepare demo records and the assessment admin account"

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_ADMIN_PASSWORD")

        if not password:
            raise CommandError(
                "DEMO_ADMIN_PASSWORD is not configured."
            )

        if not Department.objects.exists() and not Employee.objects.exists():
            call_command("seed_leave")
            self.stdout.write("Demo records created.")

        User = get_user_model()
        admin, _ = User.objects.get_or_create(
            username="admin"
        )

        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.set_password(password)
        admin.save()

        self.stdout.write(
            self.style.SUCCESS("Admin account ready.")
        )
