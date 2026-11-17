import csv
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, ProtectedError
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (ApplicationForm, DepartmentForm, EmployeeForm, LeaveTypeForm,
                    ProcessForm, TeamSizeForm)
from .models import (Department, Employee, LeaveApplication, LeaveRecord, LeaveType, TeamSize)
from .permissions import can_process, get_employee, is_hr, is_manager, role_of
from .utils import holidays_for_years


# ---------------------------------------------------------------- helpers
def visible_applications(user):
    """HR sees everything, a manager sees their team + themselves, an employee sees only their own."""
    qs = LeaveApplication.objects.select_related("employee", "employee__department", "leave_type")
    if is_hr(user):
        return qs
    emp = get_employee(user)
    if not emp:
        return qs.none()
    scope = Q(employee=emp)
    if is_manager(user):
        scope |= Q(employee__manager=emp)
    return qs.filter(scope)


def _meter(allowed, used):
    """Share of an entitlement already used, plus a level that drives the meter colour."""
    if not allowed:
        return {"pct": 0, "level": "unlimited"}
    pct = min(100, round(used * 100 / allowed))
    level = "out" if used >= allowed else "low" if used >= allowed * 0.8 else "ok"
    return {"pct": pct, "level": level}


def paginate(request, items, per_page=15):
    return Paginator(items, per_page).get_page(request.GET.get("page"))


# ---------------------------------------------------------------- dashboard
@login_required
def home(request):
    today = timezone.localdate()
    emp = get_employee(request.user)
    scope = visible_applications(request.user)

    balances = []
    if emp:
        for lt in LeaveType.objects.all():
            if lt.gender_restriction and lt.gender_restriction != emp.gender:
                continue
            used = lt.used_days(emp, today.year)
            left = lt.remaining(emp, today.year)
            balances.append({"type": lt, "used": used, "left": left, **_meter(lt.days_allowed, used)})

    approvable = [a for a in scope.filter(status="Pending") if can_process(request.user, a)]
    ctx = {
        "role": role_of(request.user),
        "employee": emp,
        "balances": balances,
        "year": today.year,
        "to_approve": approvable,
        "on_leave_today": scope.filter(status="Approved", start_date__lte=today, end_date__gte=today),
        "upcoming": scope.filter(status="Approved", start_date__gt=today,
                                 start_date__lte=today + timedelta(days=30)).order_by("start_date"),
        "recent": scope.filter(employee=emp)[:5] if emp else [],
        "stats": {
            "employees": Employee.objects.count(),
            "departments": Department.objects.count(),
            "pending": LeaveApplication.objects.filter(status="Pending").count(),
            "approved": LeaveApplication.objects.filter(status="Approved").count(),
        } if is_hr(request.user) else None,
    }
    return render(request, "leave/home.html", ctx)


# ---------------------------------------------------------------- master data CRUD
MASTERS = {
    "department": dict(
        model=Department, form=DepartmentForm, title="Departments", singular="Department",
        columns=[("ID", lambda o: o.pk), ("Department Name", lambda o: o.name),
                 ("Description", lambda o: o.description or "-"), ("Employees", lambda o: o.employee_count)],
        search=["name"], everyone=False, annotate={"employee_count": Count("employees")}),
    "employee": dict(
        model=Employee, form=EmployeeForm, title="Employees", singular="Employee",
        columns=[("ID", lambda o: o.pk), ("Full Name", lambda o: o.full_name),
                 ("Gender", lambda o: o.get_gender_display()), ("Email", lambda o: o.email),
                 ("Department", lambda o: o.department), ("Manager", lambda o: o.manager or "-"),
                 ("Login", lambda o: o.user.username if o.user else "-")],
        search=["full_name", "email"], everyone=False, related=["department", "manager", "user"]),
    "teamsize": dict(
        model=TeamSize, form=TeamSizeForm, title="Team Sizes", singular="Team",
        columns=[("Team ID", lambda o: o.pk), ("Manager", lambda o: o.manager),
                 ("Team Size", lambda o: o.size), ("Registered members", lambda o: o.member_count),
                 ("Max away at once", lambda o: o.max_away)],
        search=["manager__full_name"], everyone=False, related=["manager"],
        annotate={"member_count": Count("manager__reports")}),
    "leavetype": dict(
        model=LeaveType, form=LeaveTypeForm, title="Leave Types", singular="Leave Type",
        columns=[("ID", lambda o: o.pk), ("Type Name", lambda o: o.name),
                 ("Description", lambda o: o.description or "-"),
                 ("Days / year", lambda o: o.days_allowed or "No limit"),
                 ("Restricted to", lambda o: o.get_gender_restriction_display() or "Anyone")],
        search=["name"], everyone=True),
}


def _config(key):
    return MASTERS[key]


@login_required
def master_list(request, key):
    cfg = _config(key)
    if not (cfg["everyone"] or is_hr(request.user)):
        raise PermissionDenied
    qs = cfg["model"].objects.all()
    if cfg.get("annotate"):
        qs = qs.annotate(**cfg["annotate"])
    if cfg.get("related"):
        qs = qs.select_related(*cfg["related"])
    q = request.GET.get("q", "").strip()
    if q:
        cond = Q()
        for f in cfg["search"]:
            cond |= Q(**{f + "__icontains": q})
        qs = qs.filter(cond)
    page = paginate(request, qs)
    rows = [(o, [col(o) for _, col in cfg["columns"]]) for o in page]
    return render(request, "leave/list.html", {
        "key": key, "cfg": cfg, "page": page, "rows": rows,
        "headers": [h for h, _ in cfg["columns"]], "q": q, "can_edit": is_hr(request.user),
    })


@login_required
def master_form(request, key, pk=None):
    if not is_hr(request.user):
        raise PermissionDenied
    cfg = _config(key)
    obj = get_object_or_404(cfg["model"], pk=pk) if pk else None
    form = cfg["form"](request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{cfg['singular']} {'updated' if obj else 'added'}.")
        return redirect(f"leave:{key}_list")
    return render(request, "leave/form.html", {
        "form": form, "title": f"{'Edit' if obj else 'Add'} {cfg['singular']}", "back": f"leave:{key}_list"})


@login_required
def master_delete(request, key, pk):
    if not is_hr(request.user):
        raise PermissionDenied
    cfg = _config(key)
    obj = get_object_or_404(cfg["model"], pk=pk)
    if request.method == "POST":
        try:
            obj.delete()
            messages.success(request, f"{cfg['singular']} deleted.")
        except ProtectedError:
            messages.error(request, f"Cannot delete '{obj}': other records still depend on it.")
        return redirect(f"leave:{key}_list")
    return render(request, "leave/confirm_delete.html", {"obj": obj, "back": f"leave:{key}_list"})


# ---------------------------------------------------------------- applications
def _filtered_applications(request):
    qs = visible_applications(request.user)
    status = request.GET.get("status", "")
    ltype = request.GET.get("type", "")
    q = request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(status=status)
    if ltype:
        qs = qs.filter(leave_type_id=ltype)
    if q:
        qs = qs.filter(employee__full_name__icontains=q)
    return qs, status, ltype, q


@login_required
def application_list(request):
    qs, status, ltype, q = _filtered_applications(request)
    page = paginate(request, qs)
    user, emp = request.user, get_employee(request.user)
    for a in page:
        a.can_process = a.is_pending and can_process(user, a)
        a.can_cancel = a.is_pending and (is_hr(user) or (emp and a.employee_id == emp.pk))
    return render(request, "leave/applications.html", {
        "page": page, "status": status, "ltype": ltype, "q": q,
        "filtered": bool(status or ltype or q),
        "statuses": LeaveApplication.Status.choices, "types": LeaveType.objects.all(),
        "show_employee": is_hr(user) or is_manager(user),
    })


def _csv_safe(value):
    """Stop spreadsheet apps from running a cell that starts like a formula (CSV injection)."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@login_required
def application_export(request):
    qs, *_ = _filtered_applications(request)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="leave_applications_{timezone.localdate():%Y-%m-%d}.csv"'
    resp.write("\ufeff")  # byte-order mark so Excel reads names and accents correctly
    w = csv.writer(resp)
    w.writerow(["App ID", "Employee", "Department", "Leave Type", "Start", "End", "Days", "Reason", "Status", "Applied on"])
    for a in qs:
        w.writerow([a.pk, _csv_safe(a.employee), _csv_safe(a.employee.department), a.leave_type,
                    a.start_date, a.end_date, a.days, _csv_safe(a.reason), a.status,
                    timezone.localtime(a.applied_on).strftime("%Y-%m-%d %H:%M")])
    return resp


@login_required
def application_add(request):
    emp = get_employee(request.user)
    hr = is_hr(request.user)
    if not emp and not hr:
        messages.error(request, "Your login is not linked to an employee record. Ask HR to link it.")
        return redirect("leave:home")
    form = ApplicationForm(request.POST or None, employee=emp, allow_choose=hr)
    if request.method == "POST" and form.is_valid():
        app = form.save()
        messages.success(request, f"Application #{app.pk} submitted ({app.days} day(s)). Status: Pending.")
        return redirect("leave:application_list")
    today = timezone.localdate()
    types = list(form.fields["leave_type"].queryset)  # only the types this person can actually choose
    type_info = {
        str(t.pk): {
            "name": t.name, "allowed": t.days_allowed,
            "left": t.remaining(emp, today.year) if emp and not hr else None,
        } for t in types
    }
    return render(request, "leave/application_form.html", {
        "form": form, "types": types, "employee": emp, "is_hr": hr, "type_info": type_info,
        "holidays": holidays_for_years(range(today.year - 1, today.year + 3)),
        "day_basis": getattr(settings, "LEAVE_DAY_BASIS", "working"),
    })


@login_required
@require_POST
def application_cancel(request, pk):
    app = get_object_or_404(visible_applications(request.user), pk=pk)
    emp = get_employee(request.user)
    if not (is_hr(request.user) or (emp and app.employee_id == emp.pk)):
        raise PermissionDenied
    if not app.is_pending:
        messages.error(request, "Only pending applications can be cancelled.")
    else:
        app.status = LeaveApplication.Status.CANCELLED
        app.save(update_fields=["status"])
        messages.success(request, f"Application #{app.pk} cancelled.")
    return redirect("leave:application_list")


@login_required
def application_process(request, pk):
    app = get_object_or_404(visible_applications(request.user), pk=pk)
    if not can_process(request.user, app):
        raise PermissionDenied
    if not app.is_pending:
        messages.error(request, "This application has already been processed.")
        return redirect("leave:application_list")

    form = ProcessForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            app = LeaveApplication.objects.select_for_update().get(pk=app.pk)
            if not app.is_pending:
                messages.error(request, "This application was just processed by someone else.")
                return redirect("leave:application_list")
            decision = form.cleaned_data["decision"]
            app.status = decision
            app.save(update_fields=["status"])
            LeaveRecord.objects.create(application=app, decision=decision,
                                       processed_by=request.user, comments=form.cleaned_data["comments"])
        messages.success(request, f"Application #{app.pk} {decision.lower()} and logged.")
        return redirect("leave:application_list")

    return render(request, "leave/process.html", {
        "app": app, "form": form, "warning": app.team_warning(), "clashes": app.team_clash(),
        "left": app.leave_type.remaining(app.employee, app.start_date.year),
    })


# ---------------------------------------------------------------- records
@login_required
def record_list(request):
    qs = LeaveRecord.objects.filter(application__in=visible_applications(request.user)).select_related(
        "application__employee", "application__leave_type", "processed_by", "processed_by__employee")
    decision = request.GET.get("decision", "")
    if decision:
        qs = qs.filter(decision=decision)
    return render(request, "leave/records.html", {"page": paginate(request, qs), "decision": decision})
