from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q

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

class ManagerAuthorityViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ManagerAuthoritySerializer

    def get_queryset(self):

        authorities = (
            Authority.objects
            .prefetch_related(
                "reviews",
                "grids",
            )
        )

        return authorities

    def get_serializer_class(self):

        if self.action == "retrieve":
            return ManagerAuthorityDetailSerializer

        return ManagerAuthoritySerializer

    def _calculate_authority_data(self, authority):

        grids = list(
            authority.grids
            .select_related("assigned_to")
        )

        # --------------------------------------------------
        # Calculate grid street lengths
        # --------------------------------------------------

        total_km = 0.0

        grid_km = {}

        for grid in grids:

            streets = (
                Street.objects
                .filter(
                    geom__intersects=grid.geom
                )
                .annotate(
                    intersection_length=Length(
                        Intersection(
                            "geom",
                            grid.geom
                        )
                    )
                )
            )

            km = sum(
                (
                    street.intersection_length.m
                    for street in streets
                    if street.intersection_length
                ),
                0
            ) / 1000

            grid_km[grid.pk] = km

            total_km += km

        return grid_km, total_km

    def retrieve(self, request, *args, **kwargs):

        authority = self.get_object()

        grid_km, total_km = (
            self._calculate_authority_data(
                authority
            )
        )

        grids = list(
            authority.grids.all()
        )

        completed_km = sum(
            grid.km_completed or 0
            for grid in grids
        )

        reviewed_km = sum(
            review.total_km_reviewed or 0
            for review in authority.reviews.all()
        )

        estimated_hours = sum(
            grid.estimated_time_to_capture or 0
            for grid in grids
        )

        # --------------------------------------------------
        # Attach calculated values
        # --------------------------------------------------

        authority.no_grids = len(grids)

        authority.total_km = total_km

        authority.total_completed_km = completed_km

        authority.km_reviewed = reviewed_km

        authority.estimated_time_to_complete = (
            estimated_hours
        )

        authority.completion_percentage = (
            (completed_km / total_km * 100)
            if total_km
            else 0
        )

        authority.review_percentage = (
            (reviewed_km / total_km * 100)
            if total_km
            else 0
        )

        authority.remaining_km = max(
            total_km - completed_km,
            0
        )

        serializer = self.get_serializer(
            authority,
            context={
                "grid_km": grid_km,
                "total_km": total_km,
            }
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
                "assigned_to"
            )
            .annotate(
                geom_json=AsGeoJSON(
                    "geom",
                    precision=6
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

class ManagerReviewViewSet(
    viewsets.ModelViewSet
):

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


# ==========================================================
# EMPLOYEE VIEWSET
# ==========================================================

class ManagerEmployeeViewSet(
    viewsets.ReadOnlyModelViewSet
):
    """
    Manager Employee / Workload API.

    Endpoints:

        GET /api/v1/manager/employees/

        GET /api/v1/manager/employees/<id>/

        GET /api/v1/manager/employees/<id>/grids/

    """

    serializer_class = ManagerEmployeeSerializer

    queryset = User.objects.all()

    def get_queryset(self):

        return (
            User.objects
            .filter(
                assigned_grids__isnull=False
            )
            .distinct()
            .order_by(
                "username"
            )
        )

    # ======================================================
    # EMPLOYEE GRIDS
    # ======================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="grids"
    )
    def grids(self, request, pk=None):

        user = self.get_object()

        queryset = (
            Grid.objects
            .filter(
                assigned_to=user
            )
            .select_related(
                "authority"
            )
            .order_by("id")
        )

        serializer = ManagerGridSerializer(
            queryset,
            many=True,
            context={
                "request": request
            }
        )

        return Response(
            serializer.data
        )

