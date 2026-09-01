from django.core.management.base import BaseCommand

from backend.models import Grid


class Command(BaseCommand):

    help = (
        "Recalculate cached spatial statistics "
        "for all grids."
    )

    def handle(self, *args, **options):

        grids = Grid.objects.all()

        total = grids.count()

        self.stdout.write(
            f"Recalculating {total} grids..."
        )

        for index, grid in enumerate(
            grids.iterator(),
            start=1
        ):

            grid.recalculate_spatial_statistics(
                save=True
            )

            if index % 100 == 0:

                self.stdout.write(
                    f"Processed {index}/{total}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed. "
                f"{total} grids recalculated."
            )
        )