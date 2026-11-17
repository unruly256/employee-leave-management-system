from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import LeaveApplication, LeaveRecord, LeaveType
from .utils import count_days, holidays_for_years


class DayCountTests(TestCase):
    def test_working_days_skip_weekends_and_holidays(self):
        self.assertEqual(count_days(date(2026, 6, 1), date(2026, 6, 5)), 4)    # Jun 3 Martyrs' Day
        self.assertEqual(count_days(date(2026, 6, 20), date(2026, 6, 22)), 1)  # Sat-Mon
        self.assertEqual(count_days(date(2026, 6, 5), date(2026, 6, 4)), 0)


class WorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_leave", verbosity=0)
        U = get_user_model()
        cls.hr, cls.mgr, cls.staff = (U.objects.get(username=n) for n in ("shukie.sabr", "atu.gilbo", "nagie.shadia"))
        cls.staff_emp = cls.staff.employee

    def make(self, emp, type_name, s, e):
        a = LeaveApplication(employee=emp, leave_type=LeaveType.objects.get(name=type_name),
                             start_date=date.fromisoformat(s), end_date=date.fromisoformat(e))
        a.full_clean()
        a.save()
        return a

    def test_gender_restricted_type(self):
        with self.assertRaises(ValidationError):
            self.make(self.staff_emp, "Paternity", "2027-02-02", "2027-02-03")

    def test_overlap_rejected(self):
        with self.assertRaises(ValidationError):
            self.make(self.staff_emp, "Annual", "2026-08-11", "2026-08-11")  # inside pending sick leave

    def test_balance_enforced(self):
        with self.assertRaises(ValidationError):
            self.make(self.staff_emp, "Emergency", "2027-03-01", "2027-03-12")  # 10 days > 5

    def test_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.make(self.staff_emp, "Annual", "2027-03-10", "2027-03-01")

    def test_employee_cannot_process(self):
        app = LeaveApplication.objects.get(status="Pending", employee=self.staff_emp, leave_type__name="Sick")
        self.client.force_login(self.staff)
        r = self.client.post(reverse("leave:application_process", args=[app.pk]), {"decision": "Approved"})
        self.assertEqual(r.status_code, 403)
        app.refresh_from_db()
        self.assertEqual(app.status, "Pending")

    def test_manager_approves_team_member_and_logs_record(self):
        app = LeaveApplication.objects.get(employee=self.staff_emp, leave_type__name="Sick")
        self.client.force_login(self.mgr)
        r = self.client.post(reverse("leave:application_process", args=[app.pk]),
                             {"decision": "Approved", "comments": "Get well"})
        self.assertEqual(r.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, "Approved")
        self.assertEqual(LeaveRecord.objects.get(application=app).processed_by, self.mgr)

    def test_cannot_approve_own_application(self):
        mine = self.make(self.hr.employee, "Annual", "2027-04-05", "2027-04-07")
        self.client.force_login(self.hr)
        r = self.client.post(reverse("leave:application_process", args=[mine.pk]), {"decision": "Approved"})
        self.assertEqual(r.status_code, 403)

    def test_cannot_process_twice(self):
        app = LeaveApplication.objects.get(employee=self.staff_emp, leave_type__name="Sick")
        self.client.force_login(self.mgr)
        url = reverse("leave:application_process", args=[app.pk])
        self.client.post(url, {"decision": "Rejected"})
        self.client.post(url, {"decision": "Approved"})
        app.refresh_from_db()
        self.assertEqual(app.status, "Rejected")

    def test_visibility_and_master_data_permissions(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse("leave:application_list"))
        self.assertTrue(all(a.employee_id == self.staff_emp.pk for a in r.context["page"]))
        self.assertEqual(self.client.get(reverse("leave:employee_list")).status_code, 403)
        self.client.force_login(self.hr)
        self.assertEqual(self.client.get(reverse("leave:employee_list")).status_code, 200)

    def test_anonymous_redirected_to_login(self):
        for name in ("leave:home", "leave:application_list", "leave:leavetype_list", "leave:record_list"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_all_pages_render_for_all_roles(self):
        for u in (self.hr, self.mgr, self.staff):
            self.client.force_login(u)
            for name in ("home", "application_list", "application_add", "record_list", "leavetype_list",
                         "application_export"):
                self.assertEqual(self.client.get(reverse(f"leave:{name}")).status_code, 200, (u, name))

    def test_apply_via_form_starts_pending(self):
        self.client.force_login(self.staff)
        r = self.client.post(reverse("leave:application_add"), {
            "leave_type": LeaveType.objects.get(name="Annual").pk,
            "start_date": "2027-05-04", "end_date": "2027-05-06", "reason": "Rest", "status": "Approved"})
        self.assertEqual(r.status_code, 302)
        a = LeaveApplication.objects.latest("id")
        self.assertEqual((a.status, a.days, a.employee), ("Pending", 3, self.staff_emp))


class PolishTests(TestCase):
    """Behaviour added while polishing: safe CSV export, branded errors, balances and the apply form."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_leave", verbosity=0)
        U = get_user_model()
        cls.hr, cls.mgr, cls.staff = (U.objects.get(username=n) for n in ("shukie.sabr", "atu.gilbo", "nagie.shadia"))

    def test_csv_export_neutralises_spreadsheet_formulas(self):
        app = LeaveApplication.objects.filter(employee=self.staff.employee).first()
        app.reason = '=HYPERLINK("http://evil.example","click")'
        app.save()
        self.client.force_login(self.hr)
        r = self.client.get(reverse("leave:application_export"))
        body = r.content.decode("utf-8-sig")
        self.assertNotIn(",=HYPERLINK", body)
        self.assertIn("'=HYPERLINK", body)
        self.assertIn("leave_applications_", r["Content-Disposition"])

    def test_denied_page_is_branded(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse("leave:employee_list"))
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "don", status_code=403)
        self.assertContains(r, "have access to this page", status_code=403)

    def test_unknown_page_is_branded(self):
        self.client.force_login(self.staff)
        r = self.client.get("/no/such/page/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "find that page", status_code=404)

    def test_dashboard_balance_meters(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse("leave:home"))
        balances = {b["type"].name: b for b in r.context["balances"]}
        self.assertNotIn("Paternity", balances)            # male-only type hidden from a female employee
        self.assertIn(balances["Annual"]["level"], {"ok", "low", "out"})
        self.assertTrue(0 <= balances["Annual"]["pct"] <= 100)
        self.assertContains(r, 'role="progressbar"')

    def test_apply_form_offers_only_allowed_leave_types(self):
        self.client.force_login(self.staff)                  # female employee
        r = self.client.get(reverse("leave:application_add"))
        names = {t.name for t in r.context["form"].fields["leave_type"].queryset}
        self.assertIn("Maternity", names)
        self.assertNotIn("Paternity", names)
        self.assertContains(r, 'id="leaveForm"')
        self.assertContains(r, 'id="estimate"')

    def test_holiday_list_matches_server_rules(self):
        days = holidays_for_years([2027])
        self.assertIn("2027-10-09", days)
        self.assertIn("2027-12-25", days)
        self.assertEqual(days, sorted(days))

    def test_list_pages_keep_filters_when_paging(self):
        self.client.force_login(self.hr)
        r = self.client.get(reverse("leave:application_list"), {"status": "Approved"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["filtered"])
        self.assertTrue(all(a.status == "Approved" for a in r.context["page"]))

    def test_login_page_renders_for_anonymous(self):
        r = self.client.get(reverse("login"))
        self.assertContains(r, "Sign in")
        self.assertNotContains(r, "Log out")
