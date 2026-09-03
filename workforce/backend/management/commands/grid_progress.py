from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Calculate and permanently store "
        "estimated_completion_day for all grids."
    )

    def handle(self, *args, **options):

        self.stdout.write(
            "Calculating grid completion days..."
        )

        with connection.cursor() as cursor:

            cursor.execute(
                """
                WITH cumulative AS (
                    SELECT
                        id,

                        CASE
                            WHEN assigned_to_id IS NULL
                                OR estimated_time_to_capture IS NULL
                                OR estimated_time_to_capture <= 0
                            THEN NULL

                            ELSE CEIL(
                                SUM(
                                    estimated_time_to_capture
                                ) OVER (
                                    PARTITION BY assigned_to_id
                                    ORDER BY id
                                    ROWS BETWEEN
                                        UNBOUNDED PRECEDING
                                        AND CURRENT ROW
                                ) / 7.5
                            )::integer
                        END AS completion_day

                    FROM backend_grid
                )

                UPDATE backend_grid AS g

                SET estimated_completion_day =
                    cumulative.completion_day

                FROM cumulative

                WHERE g.id = cumulative.id;
                """
            )

            updated = cursor.rowcount

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {updated} grids."
            )
        )
