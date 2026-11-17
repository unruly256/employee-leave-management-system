import math

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from .utils import count_days


class Gender(models.TextChoices):
    FEMALE = "F", "Female"
    MALE = "M", "Male"


class Department(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="employee",
        help_text="Login account of this employee (needed to apply or approve online).",
    )
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    manager = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports",
        help_text="Line manager who approves this employee's leave.",
    )

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name

    def clean(self):
        if self.manager_id and self.manager_id == self.pk:
            raise ValidationError({"manager": "An employee cannot be their own manager."})


class TeamSize(models.Model):
    manager = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="team_size")
    size = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="Total headcount of the team.")

    class Meta:
        ordering = ["manager__full_name"]

    def __str__(self):
        return f"{self.manager} - team of {self.size}"

    @property
    def max_away(self):
        """Most people who may be away at the same time before a warning is raised."""
        ratio = getattr(settings, "LEAVE_MAX_TEAM_ON_LEAVE_RATIO", 0.5)
        return max(1, math.floor(self.size * ratio))


class LeaveType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200, blank=True)
    days_allowed = models.PositiveSmallIntegerField(
        default=0, help_text="Days per calendar year (0 = no limit).",
    )
    gender_restriction = models.CharField(
        max_length=1, choices=Gender.choices, blank=True,
        help_text="Leave empty if anyone can take it (e.g. Maternity = Female).",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    def used_days(self, employee, year, exclude_pk=None):
        qs = LeaveApplication.objects.filter(
            employee=employee, leave_type=self, start_date__year=year,
            status__in=[LeaveApplication.Status.PENDING, LeaveApplication.Status.APPROVED],
        )
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        return qs.aggregate(t=Sum("days"))["t"] or 0

    def remaining(self, employee, year, exclude_pk=None):
        if not self.days_allowed:
            return None
        return self.days_allowed - self.used_days(employee, year, exclude_pk)


class LeaveApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"
        CANCELLED = "Cancelled", "Cancelled"

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="applications")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="applications")
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveSmallIntegerField(editable=False, default=0)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    applied_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applied_on", "-id"]

    def __str__(self):
        return f"#{self.pk} {self.employee} - {self.leave_type} ({self.start_date} to {self.end_date})"

    def clean(self):
        if not (self.start_date and self.end_date and self.employee_id and self.leave_type_id):
            return
        if self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before the start date."})

        days = count_days(self.start_date, self.end_date)
        if days == 0:
            raise ValidationError("The chosen dates contain no working days (weekend / public holiday only).")

        lt = self.leave_type
        if lt.gender_restriction and lt.gender_restriction != self.employee.gender:
            raise ValidationError({"leave_type": f"{lt.name} leave is not available for this employee."})

        clash = LeaveApplication.objects.filter(
            employee=self.employee,
            status__in=[self.Status.PENDING, self.Status.APPROVED],
            start_date__lte=self.end_date, end_date__gte=self.start_date,
        ).exclude(pk=self.pk).first()
        if clash:
            raise ValidationError(
                f"Overlaps with application #{clash.pk} ({clash.start_date} to {clash.end_date}, {clash.status})."
            )

        left = lt.remaining(self.employee, self.start_date.year, exclude_pk=self.pk)
        if left is not None and days > left:
            raise ValidationError(
                f"Not enough {lt.name} leave: {days} day(s) requested, {max(left, 0)} left for {self.start_date.year}."
            )

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.days = count_days(self.start_date, self.end_date)
        super().save(*args, **kwargs)

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    def team_clash(self):
        """Other approved leaves from the same manager's team that overlap these dates."""
        mgr = self.employee.manager
        if not mgr:
            return []
        return list(
            LeaveApplication.objects.filter(
                employee__manager=mgr, status=self.Status.APPROVED,
                start_date__lte=self.end_date, end_date__gte=self.start_date,
            ).exclude(employee=self.employee).select_related("employee", "leave_type")
        )

    def team_warning(self):
        mgr = self.employee.manager
        if not mgr or not hasattr(mgr, "team_size"):
            return ""
        away = {a.employee_id for a in self.team_clash()} | {self.employee_id}
        limit = mgr.team_size.max_away
        if len(away) > limit:
            return (f"Approving this puts {len(away)} people of {mgr}'s team away at the same time "
                    f"(recommended maximum: {limit}).")
        return ""


class LeaveRecord(models.Model):
    """Audit log created when an application is processed (approved or rejected)."""
    application = models.OneToOneField(LeaveApplication, on_delete=models.CASCADE, related_name="record")
    decision = models.CharField(max_length=10, choices=[("Approved", "Approved"), ("Rejected", "Rejected")])
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    comments = models.CharField(max_length=255, blank=True)
    date_logged = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_logged", "-id"]

    def __str__(self):
        return f"Record #{self.pk} for application #{self.application_id}"

    @property
    def processor_name(self):
        u = self.processed_by
        if not u:
            return "-"
        emp = getattr(u, "employee", None)
        return emp.full_name if emp else (u.get_full_name() or u.username)
