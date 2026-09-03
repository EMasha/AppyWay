import math

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import (
    Intersection,
    Length,
    Transform,
)
from django.db.models import (
    Count,
    F,
    Q,
    Sum,
)
from django.utils import timezone


# ==========================================================
# AUTHORITY
# ==========================================================

class Authority(models.Model):

    name = models.CharField(
        max_length=255,
        unique=True
    )

    geom = models.PolygonField(
        srid=4326
    )

    # ==========================================================
    # GRID / PROJECT STATISTICS
    # ==========================================================

    @property
    def no_grids(self):
        """
        Number of grids belonging to this Authority.

        Uses COUNT() rather than loading all Grid objects.
        """

        return self.grids.count()

    @property
    def total_km(self):
        """
        Total kilometers that need to be digitized.

        Uses the cached km_to_digitize field on Grid.

        IMPORTANT:
        km_to_digitize must be recalculated when grids/
        streets are imported or their geometry changes.
        """

        return round(
            self.grids.aggregate(
                total=Sum("km_to_digitize")
            )["total"] or 0.0,
            2
        )

    @property
    def total_completed_km(self):
        """
        Total kilometers completed.
        """

        return round(
            self.grids.aggregate(
                total=Sum("km_completed")
            )["total"] or 0.0,
            2
        )

    @property
    def remaining_km(self):
        """
        Remaining kilometers to digitize.
        """

        remaining = (
            self.total_km
            - self.total_completed_km
        )

        return round(
            max(remaining, 0.0),
            2
        )

    @property
    def completion_percentage(self):
        """
        Percentage of digitization completed.
        """

        total = self.total_km

        if total <= 0:
            return 0.0

        return round(
            (
                self.total_completed_km
                / total
            ) * 100,
            2
        )

    # ==========================================================
    # REVIEW STATISTICS
    # ==========================================================

    @property
    def km_reviewed(self):
        """
        Total kilometers reviewed.
        """

        return round(
            self.reviews.aggregate(
                total=Sum("total_km_reviewed")
            )["total"] or 0.0,
            2
        )

    @property
    def review_percentage(self):
        """
        Percentage of total Authority KM reviewed.
        """

        total = self.total_km

        if total <= 0:
            return 0.0

        return round(
            (
                self.km_reviewed
                / total
            ) * 100,
            2
        )

    # ==========================================================
    # ESTIMATED TIMES
    # ==========================================================

    @property
    def estimated_time_to_complete(self):
        """
        Estimated digitization duration in working days.

        10 digitizers
        7.5 hours per day per digitizer
        """

        total_hours = (
            self.grids.aggregate(
                total=Sum(
                    "estimated_time_to_capture"
                )
            )["total"] or 0.0
        )

        daily_capacity = (
            Grid.NUM_DIGITIZERS
            * Grid.WORKING_HOURS_PER_DAY
        )

        if daily_capacity <= 0:
            return 0.0

        return round(
            total_hours / daily_capacity,
            2
        )

    @property
    def estimated_time_to_review(self):
        """
        Estimated review duration in working days.

        5 minutes per grid
        7.5 working hours per day
        """

        number_of_grids = self.no_grids

        total_hours = (
            number_of_grids * 5
        ) / 60

        return round(
            total_hours
            / Grid.WORKING_HOURS_PER_DAY,
            2
        )

    # ==========================================================
    # REVIEW SCHEDULE
    # ==========================================================

    def sync_review_days(self):
        """
        Synchronize Review records with the estimated
        review duration.

        Existing Review records are NEVER deleted.

        Missing future review days are created.

        Excess future days are marked inactive.
        """

        estimated_days = math.ceil(
            self.estimated_time_to_review
        )

        # ------------------------------------------------------
        # CREATE MISSING DAYS
        # ------------------------------------------------------

        for day in range(
            1,
            estimated_days + 1
        ):

            review, created = (
                Review.objects.get_or_create(
                    authority=self,
                    day=day,
                    defaults={
                        "is_active": True
                    }
                )
            )

            # Reactivate if duration increased again.
            if (
                not created
                and not review.is_active
            ):

                review.is_active = True

                review.save(
                    update_fields=[
                        "is_active"
                    ]
                )

        # ------------------------------------------------------
        # NEVER DELETE EXISTING REVIEWS
        # ------------------------------------------------------

        self.reviews.filter(
            day__gt=estimated_days,
            is_active=True
        ).update(
            is_active=False
        )

    # ==========================================================
    # CURRENT REVIEW
    # ==========================================================

    @property
    def current_review(self):
        """
        Latest active Review containing actual data.
        """

        return (
            self.reviews
            .filter(
                is_active=True
            )
            .exclude(
                total_km_reviewed=0
            )
            .order_by("-day")
            .first()
        )

    # ==========================================================
    # DAYS AHEAD / BEHIND
    # ==========================================================

    @property
    def days_ahead_behind_schedule(self):
        """
        Indicates how far ahead/behind the review schedule
        the Authority currently is.

        Uses Review burndown information.
        """

        current_review = self.current_review

        if not current_review:
            return 0.0

        estimated_days = math.ceil(
            self.estimated_time_to_review
        )

        if estimated_days <= 0:
            return 0.0

        ideal_reviewed_percentage = (
            current_review.day
            / estimated_days
        )

        actual_reviewed_percentage = (
            self.review_percentage
            / 100
        )

        difference = (
            actual_reviewed_percentage
            - ideal_reviewed_percentage
        )

        return round(
            difference,
            4
        )

    # ==========================================================
    # STRING
    # ==========================================================

    def __str__(self):
        return self.name


# ==========================================================
# STREET
# ==========================================================

class Street(models.Model):

    name_section = models.CharField(
        max_length=255,
        db_column="NAME_SECTION"
    )

    geom = models.MultiLineStringField(
        srid=4326
    )

    # ==========================================================
    # STRING
    # ==========================================================

    def __str__(self):
        return self.name_section


# ==========================================================
# GRID
# ==========================================================

class Grid(models.Model):

    class Status(models.TextChoices):

        TO_DO = (
            "to_do",
            "To Do"
        )

        BLOCKED = (
            "blocked",
            "Blocked"
        )

        IN_PROGRESS = (
            "in_progress",
            "In Progress"
        )

        DONE = (
            "done",
            "Done"
        )

    # ==========================================================
    # WORKING PARAMETERS
    # ==========================================================

    WORKING_HOURS_PER_DAY = 7.5

    NUM_DIGITIZERS = 10

    # ==========================================================
    # BASIC INFORMATION
    # ==========================================================

    grid_id = models.CharField(
        max_length=100,
        unique=True
    )

    area_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    authority = models.ForeignKey(
        Authority,
        on_delete=models.CASCADE,
        related_name="grids"
    )

    # ==========================================================
    # STATUS
    # ==========================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TO_DO
    )

    # ==========================================================
    # ASSIGNMENT
    # ==========================================================

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_grids"
    )

    # ==========================================================
    # GEOMETRY
    # ==========================================================

    geom = models.PolygonField(
        srid=4326
    )

    # ==========================================================
    # DIGITIZATION ESTIMATION
    # ==========================================================

    estimated_time_to_capture = models.FloatField(
        null=True,
        blank=True,
        help_text="Estimated capture time in hours"
    )

    # ==========================================================
    # CACHED SPATIAL STATISTICS
    # ==========================================================

    km_to_digitize = models.FloatField(
        default=0.0,
        help_text=(
            "Cached street length inside this grid "
            "in kilometers."
        )
    )

    percentage_of_total_streets = models.FloatField(
        default=0.0,
        help_text=(
            "Percentage of Authority street length "
            "represented by this grid."
        )
    )
    estimated_completion_day = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    # ==========================================================
    # ACTUAL DATES
    # ==========================================================

    start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    complete_date = models.DateTimeField(
        null=True,
        blank=True
    )

    # ==========================================================
    # PROGRESS
    # ==========================================================

    km_completed = models.FloatField(
        default=0.0
    )



    # ==========================================================
    # COMPLETE TIME
    # ==========================================================

    @property
    def complete_time(self):
        """
        Number of hours between start_date
        and complete_date.
        """

        if (
            not self.start_date
            or not self.complete_date
        ):
            return 0.0

        seconds = (
            self.complete_date
            - self.start_date
        ).total_seconds()

        return round(
            seconds / 3600,
            2
        )

    # ==========================================================
    # ESTIMATED COMPLETION DAY
    # ==========================================================

    # ==========================================================
    # SAVE
    # ==========================================================

    def save(
        self,
        *args,
        **kwargs
    ):

        old_status = None

        if self.pk:

            old_status = (
                Grid.objects
                .filter(
                    pk=self.pk
                )
                .values_list(
                    "status",
                    flat=True
                )
                .first()
            )

        now = timezone.now()

        # ------------------------------------------------------
        # TO_DO -> IN_PROGRESS
        # ------------------------------------------------------

        if (
            old_status == self.Status.TO_DO
            and self.status == self.Status.IN_PROGRESS
        ):

            self.start_date = now

        # ------------------------------------------------------
        # IN_PROGRESS -> DONE
        # ------------------------------------------------------

        if (
            old_status == self.Status.IN_PROGRESS
            and self.status == self.Status.DONE
        ):

            self.complete_date = now

        # ------------------------------------------------------
        # IMPORTANT
        #
        # Do NOT calculate spatial statistics here.
        #
        # Otherwise every normal update from the dashboard
        # would execute expensive GIS queries.
        # ------------------------------------------------------

        super().save(
            *args,
            **kwargs
        )

        # ------------------------------------------------------
        # Synchronize review schedule
        # ------------------------------------------------------

        if self.authority_id:

            self.authority.sync_review_days()

    # ==========================================================
    # STRING
    # ==========================================================

    def __str__(self):
        return self.grid_id


# ==========================================================
# REVIEW
# ==========================================================

class Review(models.Model):

    authority = models.ForeignKey(
        Authority,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    day = models.PositiveIntegerField()

    total_km_reviewed = models.FloatField(
        default=0.0
    )

    is_active = models.BooleanField(
        default=True
    )

    # ==========================================================
    # PERCENTAGE REVIEWED
    # ==========================================================

    @property
    def percentage_of_total_km_reviewed(self):
        """
        Percentage of Authority KM reviewed.
        """

        total_km = self.authority.total_km

        if total_km <= 0:
            return 0.0

        return round(
            (
                self.total_km_reviewed
                / total_km
            ) * 100,
            2
        )

    # ==========================================================
    # ACTUAL BURNDOWN
    # ==========================================================

    @property
    def actual_burndown_rate(self):
        """
        Remaining percentage of work.
        """

        return round(
            100
            - self.percentage_of_total_km_reviewed,
            2
        )

    # ==========================================================
    # IDEAL BURNDOWN
    # ==========================================================

    @property
    def ideal_burndown_rate(self):
        """
        Ideal remaining percentage based on
        estimated review duration.
        """

        estimated_days = math.ceil(
            self.authority.estimated_time_to_review
        )

        if estimated_days <= 0:
            return 0.0

        remaining = (
            1
            - (
                self.day
                / estimated_days
            )
        )

        return round(
            max(
                remaining * 100,
                0
            ),
            2
        )

    # ==========================================================
    # BURNDOWN DIFFERENCE
    # ==========================================================

    @property
    def burndown_difference(self):
        """
        Difference between actual and ideal
        burndown percentage.

        Positive:
            Ahead

        Negative:
            Behind
        """

        actual_remaining = (
            self.actual_burndown_rate
        )

        ideal_remaining = (
            self.ideal_burndown_rate
        )

        return round(
            ideal_remaining
            - actual_remaining,
            2
        )

    # ==========================================================
    # META
    # ==========================================================

    class Meta:

        ordering = [
            "authority",
            "day"
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "authority",
                    "day"
                ],
                name=(
                    "unique_authority_review_day"
                )
            )

        ]

    # ==========================================================
    # STRING
    # ==========================================================

    def __str__(self):

        return (
            f"{self.authority.name}"
            f" - Day {self.day}"
        )