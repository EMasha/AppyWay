from django.contrib.auth import get_user_model
from rest_framework import serializers

from backend.models import (
    Authority,
    Grid,
    Review,
)


User = get_user_model()


# ==========================================================
# GRID TABLE SERIALIZER
# ==========================================================

class ManagerGridSerializer(serializers.ModelSerializer):

    geom = serializers.SerializerMethodField()

    authority_name = serializers.CharField(
        source="authority.name",
        read_only=True
    )

    assigned_to_name = (
        serializers.SerializerMethodField()
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )

    km_to_digitize = serializers.FloatField(
        read_only=True
    )

    percentage_of_total_streets = (
        serializers.FloatField(
            read_only=True
        )
    )

    estimated_completion_day = (
        serializers.IntegerField(
            read_only=True,
            allow_null=True
        )
    )

    complete_time = serializers.FloatField(
        read_only=True
    )

    class Meta:

        model = Grid

        fields = [
            "id",
            "grid_id",
            "area_name",

            "authority",
            "authority_name",

            "status",
            "status_display",

            "assigned_to",
            "assigned_to_name",

            "estimated_time_to_capture",
            "estimated_completion_day",

            "start_date",
            "complete_date",
            "complete_time",

            "km_to_digitize",
            "km_completed",
            "percentage_of_total_streets",

            "geom",
        ]

        read_only_fields = [
            "id",
            "grid_id",
            "area_name",

            "authority",
            "authority_name",

            "assigned_to_name",

            "status_display",

            "estimated_completion_day",
            "complete_time",

            "km_to_digitize",
            "percentage_of_total_streets",
            "geom",
        ]

    def get_geom(self, obj):

        return obj.geom_json

    def get_assigned_to_name(self, obj):

        if not obj.assigned_to:
            return None

        return (
            obj.assigned_to.get_full_name()
            or obj.assigned_to.username
        )

    def validate_km_completed(self, value):

        if value < 0:

            raise serializers.ValidationError(
                "Completed KM cannot be negative."
            )

        return value

    def validate_estimated_time_to_capture(
        self,
        value
    ):

        if (
            value is not None
            and value < 0
        ):

            raise serializers.ValidationError(
                "Estimated capture time cannot be negative."
            )

        return value


# ==========================================================
# REVIEW SERIALIZER
# ==========================================================

class ManagerReviewSerializer(serializers.ModelSerializer):

    authority_name = serializers.CharField(
        source="authority.name",
        read_only=True
    )

    percentage_of_total_km_reviewed = serializers.FloatField(
        read_only=True
    )

    actual_burndown_rate = serializers.FloatField(
        read_only=True
    )

    ideal_burndown_rate = serializers.FloatField(
        read_only=True
    )

    burndown_difference = serializers.FloatField(
        read_only=True
    )

    class Meta:

        model = Review

        fields = [
            "id",

            "authority",
            "authority_name",

            "day",
            "total_km_reviewed",

            "percentage_of_total_km_reviewed",
            "actual_burndown_rate",
            "ideal_burndown_rate",
            "burndown_difference",

            "is_active",
        ]

        read_only_fields = [
            "id",
            "authority",
            "authority_name",

            "percentage_of_total_km_reviewed",
            "actual_burndown_rate",
            "ideal_burndown_rate",
            "burndown_difference",
        ]

    def validate_total_km_reviewed(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Reviewed KM cannot be negative."
            )

        return value

    def validate_day(self, value):

        if value < 1:
            raise serializers.ValidationError(
                "Review day must be at least 1."
            )

        return value


# ==========================================================
# AUTHORITY SERIALIZER
# ==========================================================

# ==========================================================
# AUTHORITY SERIALIZER
# ==========================================================

class ManagerAuthoritySerializer(
    serializers.ModelSerializer
):

    no_grids = serializers.IntegerField(
        read_only=True
    )

    total_km = serializers.FloatField(
        read_only=True
    )

    total_completed_km = serializers.FloatField(
        read_only=True
    )

    remaining_km = serializers.FloatField(
        read_only=True
    )

    completion_percentage = serializers.FloatField(
        read_only=True
    )

    km_reviewed = serializers.FloatField(
        read_only=True
    )

    review_percentage = serializers.FloatField(
        read_only=True
    )

    estimated_time_to_complete = serializers.FloatField(
        read_only=True
    )

    estimated_time_to_review = serializers.FloatField(
        read_only=True
    )

    days_ahead_behind_schedule = serializers.FloatField(
        read_only=True
    )

    class Meta:

        model = Authority

        fields = [
            "id",
            "name",

            "no_grids",

            "total_km",
            "total_completed_km",
            "remaining_km",
            "completion_percentage",

            "km_reviewed",
            "review_percentage",

            "estimated_time_to_complete",
            "estimated_time_to_review",

            "days_ahead_behind_schedule",
        ]

        read_only_fields = fields


