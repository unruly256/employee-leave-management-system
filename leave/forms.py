from django import forms

from .models import Department, Employee, LeaveApplication, LeaveType, TeamSize


class StyledFormMixin:
    """Give every widget its Bootstrap class and flag invalid fields for assistive technology."""

    def _style_fields(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                continue
            css = "form-select" if isinstance(widget, forms.Select) else "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()
            if self.is_bound and name in self.errors:
                widget.attrs["class"] += " is-invalid"
                widget.attrs["aria-invalid"] = "true"


class DepartmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class EmployeeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["full_name", "gender", "email", "department", "manager", "user"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["manager"].queryset = Employee.objects.exclude(pk=self.instance.pk)
        self._style_fields()


class LeaveTypeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ["name", "description", "days_allowed", "gender_restriction"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class TeamSizeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TeamSize
        fields = ["manager", "size"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class ApplicationForm(StyledFormMixin, forms.ModelForm):
    """Employees apply for themselves; HR may apply on someone's behalf."""

    class Meta:
        model = LeaveApplication
        fields = ["employee", "leave_type", "start_date", "end_date", "reason"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.TextInput(attrs={"placeholder": "Optional, e.g. family event"}),
        }

    def __init__(self, *args, employee=None, allow_choose=False, **kwargs):
        super().__init__(*args, **kwargs)
        if allow_choose:
            self.fields["employee"].queryset = Employee.objects.select_related("department")
        else:
            del self.fields["employee"]
            self.instance.employee = employee  # so model.clean() can run its rules
            if employee is not None:
                # Do not offer leave types this employee can never take (the model still enforces it).
                restricted = LeaveType.objects.exclude(gender_restriction="").exclude(gender_restriction=employee.gender)
                self.fields["leave_type"].queryset = LeaveType.objects.exclude(pk__in=restricted)
        self.fields["leave_type"].empty_label = "Choose a leave type"
        self._style_fields()


class ProcessForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[("Approved", "Approve"), ("Rejected", "Reject")],
        widget=forms.RadioSelect,
        error_messages={"required": "Choose Approve or Reject."},
    )
    comments = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={"placeholder": "Optional note the employee will see"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["comments"].widget.attrs["class"] = "form-control"
