"""
URL configuration for workforce project.
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [

    # ==========================================================
    # DJANGO ADMIN
    # ==========================================================

    path(
        "admin/",
        admin.site.urls
    ),


    # ==========================================================
    # MANAGER API
    # ==========================================================

    path(
        "api/v1/manager/",
        include("backend.urls")
    ),


    # ==========================================================
    # MANAGER WEB INTERFACE
    # ==========================================================

    path(
        "manager/",
        include("backend.manager_urls")
    ),

]