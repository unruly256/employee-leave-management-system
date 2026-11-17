from django.urls import path

from . import views

app_name = "leave"

urlpatterns = [
    path("", views.home, name="home"),
    path("applications/", views.application_list, name="application_list"),
    path("applications/new/", views.application_add, name="application_add"),
    path("applications/export/", views.application_export, name="application_export"),
    path("applications/<int:pk>/cancel/", views.application_cancel, name="application_cancel"),
    path("applications/<int:pk>/process/", views.application_process, name="application_process"),
    path("records/", views.record_list, name="record_list"),
]

# department_*, employee_*, teamsize_*, leavetype_* : list / add / edit / delete
for _key in views.MASTERS:
    urlpatterns += [
        path(f"{_key}s/", views.master_list, {"key": _key}, name=f"{_key}_list"),
        path(f"{_key}s/add/", views.master_form, {"key": _key}, name=f"{_key}_add"),
        path(f"{_key}s/<int:pk>/edit/", views.master_form, {"key": _key}, name=f"{_key}_edit"),
        path(f"{_key}s/<int:pk>/delete/", views.master_delete, {"key": _key}, name=f"{_key}_delete"),
    ]
