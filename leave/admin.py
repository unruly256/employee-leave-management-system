from django.contrib import admin

from .models import Department, Employee, LeaveApplication, LeaveRecord, LeaveType, TeamSize


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "gender", "email", "department", "manager", "user")
    list_filter = ("department", "gender")
    search_fields = ("full_name", "email")


@admin.register(TeamSize)
class TeamSizeAdmin(admin.ModelAdmin):
    list_display = ("manager", "size")


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "days_allowed", "gender_restriction", "description")


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "leave_type", "start_date", "end_date", "days", "status")
    list_filter = ("status", "leave_type")
    search_fields = ("employee__full_name",)


@admin.register(LeaveRecord)
class LeaveRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "decision", "processed_by", "date_logged")
