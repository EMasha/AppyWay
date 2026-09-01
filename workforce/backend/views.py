


# manager/views.py

from django.shortcuts import render


def project_progress(request):

    return render(
        request,
        "manager/project_progress.html"
    )


def employee_workload(request):

    return render(
        request,
        "manager/employee_workload.html"
    )