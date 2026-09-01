from django.core.management.base import BaseCommand
from django.db.models import Count

from backend.models import Street


class Command(BaseCommand):

    help = (
        "Remove duplicate Street records based on "
        "name_section. Keeps one record for each name_section."
    )

    def handle(self, *args, **options):

        # ==========================================================
        # FIND DUPLICATE NAME_SECTION VALUES
        # ==========================================================

        duplicates = (
            Street.objects
            .values("name_section")
            .annotate(
                count=Count("id")
            )
            .filter(
                count__gt=1
            )
            .order_by("name_section")
        )

        duplicate_groups = duplicates.count()

        if duplicate_groups == 0:

            self.stdout.write(
                self.style.SUCCESS(
                    "No duplicate streets found."
                )
            )

            return

        self.stdout.write(
            f"Found {duplicate_groups} "
            f"duplicate NAME_SECTION groups."
        )

        total_deleted = 0

        # ==========================================================
        # REMOVE DUPLICATES
        # ==========================================================

        for duplicate in duplicates:

            name_section = duplicate["name_section"]

            streets = (
                Street.objects
                .filter(
                    name_section=name_section
                )
                .order_by("id")
            )

            # Keep the first record
            keep = streets.first()

            # Delete all remaining records
            duplicates_to_delete = streets.exclude(
                pk=keep.pk
            )

            delete_count = duplicates_to_delete.count()

            duplicates_to_delete.delete()

            total_deleted += delete_count

            self.stdout.write(
                f"'{name_section}': "
                f"kept ID {keep.pk}, "
                f"deleted {delete_count}"
            )

        # ==========================================================
        # RESULT
        # ==========================================================

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted."
                f"\nDuplicate groups: {duplicate_groups}"
                f"\nRecords deleted: {total_deleted}"
            )
        )