from django.contrib import admin
from django.urls import include, path
from .views import *

urlpatterns = [

    # ------------------------------------------------------
    # HTML PAGES
    # ------------------------------------------------------

    path(
        "dashboard/",
        project_progress,
        name="manager-project-progress"
    ),

    path(
        "employees/",
        employee_workload,
        name="manager-employee-workload"
    ),

]