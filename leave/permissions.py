"""Three roles, as in the system description: Employee, Manager, HR Officer (administrator)."""
from django.contrib.auth.mixins import UserPassesTestMixin

HR_GROUP = "HR Officer"


def get_employee(user):
    return getattr(user, "employee", None) if user.is_authenticated else None


def is_hr(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=HR_GROUP).exists())


def is_manager(user):
    emp = get_employee(user)
    return bool(emp and emp.reports.exists())


def role_of(user):
    if is_hr(user):
        return "HR Officer"
    if is_manager(user):
        return "Manager"
    if get_employee(user):
        return "Employee"
    return "No employee profile"


def can_process(user, application):
    """HR or the line manager may decide - but never on their own application."""
    emp = get_employee(user)
    if emp and application.employee_id == emp.pk:
        return False
    if is_hr(user):
        return True
    return bool(emp and application.employee.manager_id == emp.pk)


class HRRequiredMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return is_hr(self.request.user)
