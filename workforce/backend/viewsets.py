from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from math import ceil



from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.gis.db.models.functions import AsGeoJSON

import math
from backend.models import (
    Authority,
    Grid,
    Review,
)

from .serializers import *


User = get_user_model()


# ==========================================================
# AUTHORITY
# ==========================================================


class ManagerAuthorityViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = ManagerAuthoritySerializer

    # ======================================================
    # QUERYSET
    # ======================================================

    def get_queryset(self):

        return Authority.objects.all()

    # ======================================================
    # SERIALIZER
    # ======================================================

    def get_serializer_class(self):

        if self.action == "retrieve":

            return ManagerAuthorityDetailSerializer

        return ManagerAuthoritySerializer

    # ======================================================
    # AUTHORITY DATA
    # ======================================================

    def get_authority_data(
        self,
        authority
    ):

        # --------------------------------------------------
        # GRID STATISTICS
        # --------------------------------------------------

        grid_stats = (
            Grid.objects
            .filter(
                authority_id=authority.id
            )
            .aggregate(

                no_grids=Count("id"),

                total_km=Sum(
                    "km_to_digitize"
                ),

                total_completed_km=Sum(
                    "km_completed"
                ),

                estimated_hours=Sum(
                    "estimated_time_to_capture"
                ),

            )
        )

        no_grids = (
            grid_stats["no_grids"]
            or 0
        )

        total_km = float(
            grid_stats["total_km"]
            or 0
        )

        completed_km = float(
            grid_stats["total_completed_km"]
            or 0
        )

        estimated_hours = float(
            grid_stats["estimated_hours"]
            or 0
        )

        # --------------------------------------------------
        # REVIEW STATISTICS
        # --------------------------------------------------

        review_stats = (
            Review.objects
            .filter(
                authority_id=authority.id,
                is_active=True,
            )
            .aggregate(
                reviewed_km=Sum(
                    "total_km_reviewed"
                )
            )
        )

        reviewed_km = float(
            review_stats["reviewed_km"]
            or 0
        )

        # --------------------------------------------------
        # CALCULATIONS
        # --------------------------------------------------

        remaining_km = max(
            total_km - completed_km,
            0
        )

        completion_percentage = (

            (
                completed_km /
                total_km
            ) * 100

            if total_km > 0

            else 0.0

        )

        review_percentage = (

            (
                reviewed_km /
                total_km
            ) * 100

            if total_km > 0

            else 0.0

        )

        # --------------------------------------------------
        # DIGITIZATION TIME
        # --------------------------------------------------

        daily_digitization_capacity = (

            Grid.NUM_DIGITIZERS
            *
            Grid.WORKING_HOURS_PER_DAY

        )

        estimated_time_to_complete = (

            estimated_hours /
            daily_digitization_capacity

            if daily_digitization_capacity > 0

            else 0.0

        )

        # --------------------------------------------------
        # REVIEW TIME
        # --------------------------------------------------

        estimated_time_to_review = (

            (
                no_grids * 5
            ) / 60

        ) / Grid.WORKING_HOURS_PER_DAY

        # --------------------------------------------------
        # CURRENT REVIEW
        # --------------------------------------------------

        current_review = (
            Review.objects
            .filter(
                authority_id=authority.id,
                is_active=True,
                total_km_reviewed__gt=0,
            )
            .order_by("-day")
            .first()
        )

        # --------------------------------------------------
        # SCHEDULE
        # --------------------------------------------------

        days_ahead_behind_schedule = 0.0

        if current_review:

            estimated_days = ceil(
                estimated_time_to_review
            )

            if estimated_days > 0:

                ideal_percentage = (
                    current_review.day /
                    estimated_days
                )

                actual_percentage = (
                    review_percentage /
                    100
                )

                days_ahead_behind_schedule = round(
                    actual_percentage -
                    ideal_percentage,
                    4
                )

        # --------------------------------------------------
        # RETURN
        # --------------------------------------------------

        return {

            "no_grids":
                no_grids,

            "total_km":
                total_km,

            "total_completed_km":
                completed_km,

            "remaining_km":
                remaining_km,

            "completion_percentage":
                completion_percentage,

            "km_reviewed":
                reviewed_km,

            "review_percentage":
                review_percentage,

            "estimated_time_to_complete":
                float(
                    estimated_time_to_complete
                ),

            "estimated_time_to_review":
                float(
                    estimated_time_to_review
                ),

            "days_ahead_behind_schedule":
                float(
                    days_ahead_behind_schedule
                ),

        }

    # ======================================================
    # LIST
    # ======================================================

    def list(
        self,
        request,
        *args,
        **kwargs
    ):

        queryset = self.get_queryset()

        # --------------------------------------------------
        # Build serialized results one authority at a time.
        # This is important because authority_data is
        # different for every authority.
        # --------------------------------------------------

        results = []

        for authority in queryset:

            authority_data = (
                self.get_authority_data(
                    authority
                )
            )

            serializer = (
                ManagerAuthoritySerializer(
                    authority,
                    context={
                        **self.get_serializer_context(),

                        "authority_data":
                            authority_data,
                    }
                )
            )

            results.append(
                serializer.data
            )

        return Response(
            results
        )

    # ======================================================
    # RETRIEVE
    # ======================================================

    def retrieve(
        self,
        request,
        *args,
        **kwargs
    ):

        authority = self.get_object()

        authority_data = (
            self.get_authority_data(
                authority
            )
        )

        serializer = (
            ManagerAuthorityDetailSerializer(
                authority,
                context={
                    **self.get_serializer_context(),

                    "authority_data":
                        authority_data,
                }
            )
        )

        return Response(
            serializer.data
        )
# ==========================================================
# GRID VIEWSET
# ==========================================================

class ManagerGridViewSet(viewsets.ModelViewSet):

    serializer_class = ManagerGridSerializer

    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]

    def get_queryset(self):

        queryset = (
            Grid.objects
            .select_related(
                "authority",
                "assigned_to",
            )
            .annotate(
                geom_json=AsGeoJSON(
                    "geom",
                    precision=5,
                )
            )
            .order_by("id")
        )

        authority_id = (
            self.request.query_params.get(
                "authority"
            )
        )

        if authority_id:

            queryset = queryset.filter(
                authority_id=authority_id
            )

        status = (
            self.request.query_params.get(
                "status"
            )
        )

        if status:

            queryset = queryset.filter(
                status=status
            )

        assigned_to = (
            self.request.query_params.get(
                "assigned_to"
            )
        )

        if assigned_to:

            queryset = queryset.filter(
                assigned_to_id=assigned_to
            )

        return queryset

# ==========================================================
# REVIEW VIEWSET
# ==========================================================

class ManagerReviewViewSet(viewsets.ModelViewSet):

    serializer_class = ManagerReviewSerializer

    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]

    def get_queryset(self):

        queryset = (
            Review.objects
            .select_related(
                "authority"
            )
            .filter(
                is_active=True
            )
            .order_by(
                "authority",
                "day"
            )
        )

        authority_id = (
            self.request.query_params.get(
                "authority"
            )
        )

        if authority_id:

            queryset = queryset.filter(
                authority_id=authority_id
            )

        return queryset


