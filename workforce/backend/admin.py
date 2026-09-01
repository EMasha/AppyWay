from django.contrib import admin

from .models import (
    Authority,
    Street,
    Grid,
    Review,
)


# ==========================================================
# AUTHORITY ADMIN
# ==========================================================

@admin.register(Authority)
class AuthorityAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "no_grids",
        "total_km",
        "total_completed_km",
        "km_reviewed",
        "estimated_time_to_complete",
        "estimated_time_to_review",
        "days_ahead_behind_schedule",
    )

    search_fields = (
        "name",
        "global_id",
    )

    readonly_fields = (
        "no_grids",
        "total_km",
        "total_completed_km",
        "km_reviewed",
        "estimated_time_to_complete",
        "estimated_time_to_review",
        "days_ahead_behind_schedule",
    )

    list_filter = ()

    ordering = (
        "name",
    )


# ==========================================================
# STREET ADMIN
# ==========================================================

@admin.register(Street)
class StreetAdmin(admin.ModelAdmin):

    list_display = (
        "name_section",
        "id",
    )

    search_fields = (
        "name_section",
    )


# ==========================================================
# GRID ADMIN
# ==========================================================

@admin.register(Grid)
class GridAdmin(admin.ModelAdmin):

    list_display = (
        "grid_id",
        "area_name",
        "authority",
        "status",
        "assigned_to",

        # Calculated properties
        "km_to_digitize",
        "estimated_time_to_capture",
        "estimated_completion_day",
        "percentage_of_total_streets",
        "complete_time",

        # Database fields
        "km_completed",
        "start_date",
        "complete_date",
    )

    list_filter = (
        "status",
        "authority",
        "assigned_to",
    )

    search_fields = (
        "grid_id",
        "area_name",
        "authority__name",
        "assigned_to__username",
    )

    readonly_fields = (
        "km_to_digitize",
        "complete_time",
        "percentage_of_total_streets",
        "estimated_completion_day",
    )

    autocomplete_fields = (
        "authority",
        "assigned_to",
    )

    ordering = (
        "authority",
        "grid_id",
    )


# ==========================================================
# REVIEW ADMIN
# ==========================================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = (
        "authority",
        "day",
        "total_km_reviewed",

        # Calculated properties
        "percentage_of_total_km_reviewed",
        "actual_burndown_rate",
        "ideal_burndown_rate",
        "burndown_difference",
    )

    list_filter = (
        "authority",
    )

    search_fields = (
        "authority__name",
    )

    readonly_fields = (
        "percentage_of_total_km_reviewed",
        "actual_burndown_rate",
        "ideal_burndown_rate",
        "burndown_difference",
    )

    ordering = (
        "authority",
        "day",
    )