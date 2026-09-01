import csv
import json
import math
import os
import tempfile
from pathlib import Path

import geopandas as gpd
import requests
from django.db.models import (
    Count,
    F,
    Q,
    Sum,
)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import (
    GEOSGeometry,
    LineString,
    MultiLineString,
)
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import (
    Authority,
    Street,
    Grid,
    Review,
)


User = get_user_model()


class Command(BaseCommand):

    help = """
    Import Authority, Street, Grid and Review data.

    Supported spatial sources:
        - GeoJSON
        - Shapefile
        - ArcGIS Feature Service

    Review supports:
        - CSV
        - JSON
        - GeoJSON

    Import order:
        1. Authority
        2. Street
        3. Grid
        4. Review
    """

    # ==========================================================
    # COMMAND ARGUMENTS
    # ==========================================================

    def add_arguments(self, parser):

        parser.add_argument(
            "--authority",
            help=(
                "Authority source: GeoJSON, Shapefile "
                "or ArcGIS FeatureServer URL"
            )
        )

        parser.add_argument(
            "--streets",
            help=(
                "Street source: GeoJSON, Shapefile "
                "or ArcGIS FeatureServer URL"
            )
        )

        parser.add_argument(
            "--grids",
            help=(
                "Grid source: GeoJSON, Shapefile "
                "or ArcGIS FeatureServer URL"
            )
        )

        parser.add_argument(
            "--reviews",
            help=(
                "Review source: CSV, JSON or GeoJSON"
            )
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Database batch size. Default: 500"
        )

        parser.add_argument(
            "--update",
            action="store_true",
            help=(
                "Update existing Authority, Grid and "
                "Review records instead of skipping them."
            )
        )

    # ==========================================================
    # HANDLE
    # ==========================================================

    def handle(self, *args, **options):

        authority_source = options.get(
            "authority"
        )

        streets_source = options.get(
            "streets"
        )

        grids_source = options.get(
            "grids"
        )

        reviews_source = options.get(
            "reviews"
        )

        self.batch_size = options.get(
            "batch_size",
            500
        )

        self.update_existing = options.get(
            "update",
            False
        )

        if not any([
            authority_source,
            streets_source,
            grids_source,
            reviews_source,
        ]):

            raise CommandError(
                "You must provide at least one "
                "import source."
            )

        # ======================================================
        # 1. AUTHORITY
        # ======================================================

        if authority_source:

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "\n========================================"
                )
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "1. IMPORTING AUTHORITIES"
                )
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "========================================"
                )
            )

            self.import_authorities(
                authority_source
            )

        # ======================================================
        # 2. STREETS
        # ======================================================

        if streets_source:

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "\n========================================"
                )
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "2. IMPORTING STREETS"
                )
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "========================================"
                )
            )

            self.import_streets(
                streets_source
            )

        # ======================================================
        # 3. GRIDS
        # ======================================================

        if grids_source:

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "\n========================================"
                )
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "3. IMPORTING GRIDS"
                )
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "========================================"
                )
            )

            self.import_grids(
                grids_source
            )

        # ======================================================
        # 4. REVIEWS
        # ======================================================

        if reviews_source:

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "\n========================================"
                )
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "4. IMPORTING REVIEWS"
                )
            )

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    "========================================"
                )
            )

            self.import_reviews(
                reviews_source
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\n========================================"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "IMPORT COMPLETED"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "========================================"
            )
        )

    # ==========================================================
    # SOURCE READER
    # ==========================================================

    def read_source(self, source):

        """
        Read a spatial source.

        Supported:
            GeoJSON
            Shapefile
            ArcGIS Feature Service
        """

        if self.is_arcgis_service(source):

            self.stdout.write(
                f"Reading ArcGIS Feature Service:\n"
                f"{source}"
            )

            return self.read_arcgis_service(
                source
            )

        path = Path(source)

        if not path.exists():

            raise CommandError(
                f"Source does not exist:\n{source}"
            )

        self.stdout.write(
            f"Reading file:\n{path}"
        )

        try:

            gdf = gpd.read_file(
                path
            )

        except Exception as exc:

            raise CommandError(
                f"Could not read source:\n"
                f"{source}\n\n"
                f"Error: {exc}"
            )

        return gdf

    # ==========================================================
    # ARCGIS SERVICE DETECTION
    # ==========================================================

    @staticmethod
    def is_arcgis_service(source):

        source_lower = source.lower()

        return (
            "featureserver" in source_lower
            or "mapserver" in source_lower
        )

    # ==========================================================
    # ARCGIS FEATURE SERVICE
    # ==========================================================

    def read_arcgis_service(self, url):

        """
        Download an ArcGIS Feature Service as GeoJSON.

        Handles pagination using resultOffset and
        resultRecordCount.
        """

        url = url.rstrip("/")

        # ------------------------------------------------------
        # If the URL points to the FeatureServer root,
        # automatically use the first layer.
        # ------------------------------------------------------

        if url.lower().endswith(
            "featureserver"
        ):

            metadata_response = requests.get(
                url,
                params={
                    "f": "json"
                },
                timeout=120
            )

            metadata_response.raise_for_status()

            metadata = metadata_response.json()

            if "error" in metadata:

                raise CommandError(
                    f"ArcGIS error:\n"
                    f"{metadata['error']}"
                )

            layers = metadata.get(
                "layers",
                []
            )

            if not layers:

                raise CommandError(
                    "No layers were found in the "
                    "Feature Service."
                )

            layer_id = layers[0]["id"]

            url = (
                f"{url}/{layer_id}"
            )

            self.stdout.write(
                f"Using Feature Service layer "
                f"{layer_id}"
            )

        query_url = (
            f"{url.rstrip('/')}/query"
        )

        all_features = []

        offset = 0

        # ------------------------------------------------------
        # Ask the service for its maximum record count.
        # ------------------------------------------------------

        try:

            metadata_response = requests.get(
                url,
                params={
                    "f": "json"
                },
                timeout=120
            )

            metadata_response.raise_for_status()

            metadata = (
                metadata_response.json()
            )

            batch_size = metadata.get(
                "maxRecordCount",
                2000
            )

        except Exception:

            batch_size = 2000

        while True:

            self.stdout.write(
                f"Downloading features "
                f"{offset + 1}..."
            )

            params = {

                "where": "1=1",

                "outFields": "*",

                "returnGeometry": "true",

                "outSR": "4326",

                "resultOffset": offset,

                "resultRecordCount": batch_size,

                "f": "geojson",
            }

            response = requests.get(
                query_url,
                params=params,
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            if "error" in data:

                raise CommandError(
                    f"ArcGIS error:\n"
                    f"{data['error']}"
                )

            features = data.get(
                "features",
                []
            )

            if not features:
                break

            all_features.extend(
                features
            )

            self.stdout.write(
                f"  Downloaded "
                f"{len(all_features)} features"
            )

            exceeded = data.get(
                "exceededTransferLimit",
                False
            )

            if not exceeded:
                break

            offset += batch_size

        if not all_features:

            raise CommandError(
                "No features were returned from "
                f"{url}"
            )

        geojson = {
            "type": "FeatureCollection",
            "features": all_features
        }

        with tempfile.NamedTemporaryFile(
            suffix=".geojson",
            delete=False,
            mode="w",
            encoding="utf-8"
        ) as temp_file:

            json.dump(
                geojson,
                temp_file
            )

            temp_path = temp_file.name

        try:

            gdf = gpd.read_file(
                temp_path
            )

        finally:

            os.unlink(
                temp_path
            )

        return gdf

    # ==========================================================
    # NORMALIZE CRS
    # ==========================================================

    @staticmethod
    def normalize_crs(gdf):

        if gdf.crs is None:

            raise CommandError(
                "Input dataset does not contain "
                "a coordinate reference system."
            )

        return gdf.to_crs(
            epsg=4326
        )

    # ==========================================================
    # GEOMETRY CONVERSION
    # ==========================================================

    @staticmethod
    def convert_geometry(geometry):

        if geometry is None:
            return None

        try:
            if geometry.is_empty:
                return None
        except Exception:
            return None

        try:
            geos_geometry = GEOSGeometry(
                geometry.wkt,
                srid=4326
            )
        except Exception:
            return None

        # ----------------------------------------------------------
        # POLYGON
        # ----------------------------------------------------------

        if geos_geometry.geom_type == "Polygon":

            return geos_geometry

        # ----------------------------------------------------------
        # MULTIPOLYGON
        # ----------------------------------------------------------

        if geos_geometry.geom_type == "MultiPolygon":

            return geos_geometry

        # ----------------------------------------------------------
        # LINESTRING -> MULTILINESTRING
        # ----------------------------------------------------------

        if geos_geometry.geom_type == "LineString":

            return MultiLineString(
                geos_geometry,
                srid=4326
            )

        # ----------------------------------------------------------
        # MULTILINESTRING
        # ----------------------------------------------------------

        if geos_geometry.geom_type == "MultiLineString":

            return geos_geometry

        # ----------------------------------------------------------
        # Unsupported geometry
        # ----------------------------------------------------------

        return None
    
    # ==========================================================
    # FIELD LOOKUP
    # ==========================================================

    @staticmethod
    def get_field(
        row,
        *field_names,
        default=None
    ):

        """
        Case-insensitive field lookup.

        Example:

            get_field(
                row,
                "GRID_ID",
                "grid_id"
            )
        """

        # GeoPandas Series
        if hasattr(row, "index"):

            fields = {
                str(field).lower(): field
                for field in row.index
            }

        # Dictionary
        elif isinstance(
            row,
            dict
        ):

            fields = {
                str(field).lower(): field
                for field in row.keys()
            }

        else:

            return default

        for field_name in field_names:

            actual_field = fields.get(
                field_name.lower()
            )

            if actual_field is None:
                continue

            value = row[actual_field]

            if value is None:
                return default

            # Handle NaN
            try:

                if value != value:
                    return default

            except Exception:
                pass

            return value

        return default

    # ==========================================================
    # AUTHORITY IMPORT
    # ==========================================================

    @transaction.atomic
    def import_authorities(
        self,
        source
    ):

        gdf = self.read_source(
            source
        )

        gdf = self.normalize_crs(
            gdf
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        # ------------------------------------------------------
        # IMPORTANT:
        #
        # We only import:
        #
        #     name
        #     geometry
        #
        # global_id is NOT imported.
        # ------------------------------------------------------

        for _, row in gdf.iterrows():

            name = self.get_field(
                row,
                "name",
                "NAME",
                "AuthorityName",
                "AUTHORITY_NAME"
            )

            geometry = self.convert_geometry(
                row.geometry
            )

            if not name:

                self.stdout.write(
                    self.style.WARNING(
                        "Skipping Authority without name."
                    )
                )

                skipped_count += 1
                continue

            if geometry is None:

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping Authority "
                        f"'{name}' without geometry."
                    )
                )

                skipped_count += 1
                continue

            if self.update_existing:

                authority, created = (
                    Authority.objects.update_or_create(
                        name=name,
                        defaults={
                            "geom": geometry
                        }
                    )
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            else:

                if Authority.objects.filter(
                    name=name
                ).exists():

                    skipped_count += 1
                    continue

                Authority.objects.create(
                    name=name,
                    geom=geometry
                )

                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Authorities: "
                f"{created_count} created, "
                f"{updated_count} updated, "
                f"{skipped_count} skipped."
            )
        )

    # ==========================================================
    # STREET IMPORT
    # ==========================================================

    @transaction.atomic
    def import_streets(
        self,
        source
    ):

        gdf = self.read_source(
            source
        )

        gdf = self.normalize_crs(
            gdf
        )

        objects = []

        skipped_count = 0

        # ------------------------------------------------------
        # Only import:
        #
        #     NAME_SECTION
        #     geometry
        # ------------------------------------------------------

        for _, row in gdf.iterrows():

            name_section = self.get_field(
                row,
                "NAME_SECTION",
                "name_section",
                "name_secti",
                "NAME_SECTI",
                "NAME"
            )

            geometry = self.convert_geometry(
                row.geometry
            )

            if geometry is None:

                skipped_count += 1
                continue

            objects.append(
                Street(
                    name_section=(
                        str(name_section)
                        if name_section is not None
                        else ""
                    ),
                    geom=geometry
                )
            )

        if objects:

            Street.objects.bulk_create(
                objects,
                batch_size=self.batch_size
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Streets: "
                f"{len(objects)} imported, "
                f"{skipped_count} skipped."
            )
        )

    # ==========================================================
    # GRID IMPORT
    # ==========================================================

    @transaction.atomic
    def import_grids(
        self,
        source
    ):

        gdf = self.read_source(
            source
        )

        gdf = self.normalize_crs(
            gdf
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        affected_authorities = set()

        # ==========================================================
        # IMPORT GRIDS
        # ==========================================================

        for _, row in gdf.iterrows():

            # ------------------------------------------------------
            # GRID ID
            # ------------------------------------------------------

            grid_id = self.get_field(
                row,
                "GRID_ID",
                "grid_id",
                "GridID"
            )

            # ------------------------------------------------------
            # AREA NAME
            # ------------------------------------------------------

            area_name = self.get_field(
                row,
                "areaName",
                "AREA_NAME",
                "area_name",
                "AreaName"
            )

            # ------------------------------------------------------
            # AUTHORITY
            # ------------------------------------------------------

            authority_name = self.get_field(
                row,
                "Authority",
                "AuthorityName",
                "AUTHORITY",
                "AUTHORITY_NAME",
                "authority_name"
            )

            # ------------------------------------------------------
            # ESTIMATED CAPTURE TIME
            # ------------------------------------------------------

            estimated_time = self.get_field(
                row,
                "estimated_time_to_capture",
                "estimatedTimeToCapture",
                "ESTIMATED_TIME_TO_CAPTURE"
            )

            # ------------------------------------------------------
            # KM
            #
            # IMPORTANT:
            #
            # The GeoJSON already contains the total KM
            # for this grid in the field:
            #
            #     km
            #
            # We store this directly in:
            #
            #     Grid.km_to_digitize
            #
            # We DO NOT recalculate it using GIS.
            # ------------------------------------------------------

            km = self.get_field(
                row,
                "km",
                "KM"
            )

            # ------------------------------------------------------
            # ASSIGNED USER
            # ------------------------------------------------------

            assigned_to_value = self.get_field(
                row,
                "assigned_to",
                "assignedTo",
                "ASSIGNED_TO",
                "username",
                "USERNAME"
            )

            # ------------------------------------------------------
            # GEOMETRY
            # ------------------------------------------------------

            geometry = self.convert_geometry(
                row.geometry
            )

            # ======================================================
            # VALIDATE GRID ID
            # ======================================================

            if not grid_id:

                self.stdout.write(
                    self.style.WARNING(
                        "Skipping Grid without GRID_ID."
                    )
                )

                skipped_count += 1
                continue

            grid_id = str(
                grid_id
            ).strip()

            # ======================================================
            # VALIDATE AUTHORITY
            # ======================================================

            if not authority_name:

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping Grid "
                        f"'{grid_id}': "
                        f"Authority is missing."
                    )
                )

                skipped_count += 1
                continue

            authority_name = str(
                authority_name
            ).strip()

            authority = (
                Authority.objects
                .filter(
                    name=authority_name
                )
                .first()
            )

            if not authority:

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping Grid "
                        f"'{grid_id}': "
                        f"Authority "
                        f"'{authority_name}' "
                        f"does not exist."
                    )
                )

                skipped_count += 1
                continue

            # ======================================================
            # VALIDATE GEOMETRY
            # ======================================================

            if geometry is None:

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping Grid "
                        f"'{grid_id}': "
                        f"geometry is missing."
                    )
                )

                skipped_count += 1
                continue

            # ======================================================
            # ESTIMATED TIME
            # ======================================================

            if estimated_time is not None:

                try:

                    estimated_time = float(
                        estimated_time
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    self.stdout.write(
                        self.style.WARNING(
                            f"Grid '{grid_id}' has "
                            f"invalid estimated time "
                            f"'{estimated_time}'. "
                            f"Setting to NULL."
                        )
                    )

                    estimated_time = None

            # ======================================================
            # KM
            # ======================================================

            if km is not None:

                try:

                    km = float(
                        km
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    self.stdout.write(
                        self.style.WARNING(
                            f"Grid '{grid_id}' has "
                            f"invalid km value "
                            f"'{km}'. "
                            f"Setting to 0."
                        )
                    )

                    km = 0.0

            else:

                self.stdout.write(
                    self.style.WARNING(
                        f"Grid '{grid_id}' has no "
                        f"'km' value. "
                        f"Setting km_to_digitize to 0."
                    )
                )

                km = 0.0

            # ------------------------------------------------------
            # Prevent negative KM
            # ------------------------------------------------------

            if km < 0:

                self.stdout.write(
                    self.style.WARNING(
                        f"Grid '{grid_id}' has "
                        f"negative km value "
                        f"'{km}'. "
                        f"Setting to 0."
                    )
                )

                km = 0.0

            # ======================================================
            # ASSIGNED USER
            # ======================================================

            assigned_user = None

            if assigned_to_value not in [
                None,
                "",
            ]:

                try:

                    # --------------------------------------------------
                    # Convert values such as:
                    #
                    # "0" -> 0
                    # "1" -> 1
                    # "9" -> 9
                    #
                    # Then add 1 because the GIS assignment
                    # is zero-based.
                    # --------------------------------------------------

                    assigned_to_number = int(
                        str(
                            assigned_to_value
                        ).strip()
                    )

                    user_id = (
                        assigned_to_number + 1
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    self.stdout.write(
                        self.style.WARNING(
                            f"Grid '{grid_id}': "
                            f"invalid assigned_to value "
                            f"'{assigned_to_value}'. "
                            f"Grid will remain unassigned."
                        )
                    )

                    user_id = None

                if user_id is not None:

                    assigned_user = (
                        User.objects
                        .filter(
                            id=user_id
                        )
                        .first()
                    )

                    if not assigned_user:

                        self.stdout.write(
                            self.style.WARNING(
                                f"Grid '{grid_id}': "
                                f"Django user with ID "
                                f"'{user_id}' does not exist. "
                                f"Grid will remain unassigned."
                            )
                        )

            # ======================================================
            # CREATE / UPDATE
            # ======================================================

            if self.update_existing:

                grid, created = (
                    Grid.objects.update_or_create(
                        grid_id=grid_id,
                        defaults={
                            "area_name": area_name,
                            "authority": authority,
                            "geom": geometry,
                            "estimated_time_to_capture":
                                estimated_time,
                            "assigned_to":
                                assigned_user,

                            # --------------------------------------
                            # GeoJSON km -> Grid km_to_digitize
                            # --------------------------------------

                            "km_to_digitize":
                                round(
                                    km,
                                    2
                                ),
                        }
                    )
                )

                if created:

                    created_count += 1

                else:

                    updated_count += 1

            else:

                if Grid.objects.filter(
                    grid_id=grid_id
                ).exists():

                    skipped_count += 1
                    continue

                Grid.objects.create(
                    grid_id=grid_id,
                    area_name=area_name,
                    authority=authority,
                    geom=geometry,
                    estimated_time_to_capture=
                        estimated_time,
                    assigned_to=
                        assigned_user,

                    # ------------------------------------------
                    # GeoJSON km -> Grid km_to_digitize
                    # ------------------------------------------

                    km_to_digitize=
                        round(
                            km,
                            2
                        )
                )

                created_count += 1

            # ======================================================
            # TRACK AFFECTED AUTHORITY
            # ======================================================

            affected_authorities.add(
                authority.pk
            )

        # ==========================================================
        # RECALCULATE PERCENTAGE OF TOTAL STREETS
        #
        # We use the imported km values.
        #
        # Example:
        #
        # Grid A = 10 km
        # Grid B = 20 km
        # Grid C = 70 km
        #
        # Total = 100 km
        #
        # A = 10%
        # B = 20%
        # C = 70%
        #
        # No spatial calculation is required.
        # ==========================================================

        self.stdout.write(
            "Calculating grid street percentages..."
        )

        for authority_id in affected_authorities:

            authority = (
                Authority.objects
                .get(
                    pk=authority_id
                )
            )

            grids = (
                Grid.objects
                .filter(
                    authority=authority
                )
            )

            total_km = (
                grids.aggregate(
                    total=Sum(
                        "km_to_digitize"
                    )
                )["total"] or 0.0
            )

            if total_km <= 0:

                grids.update(
                    percentage_of_total_streets=0.0
                )

                continue

            # ------------------------------------------------------
            # Update each grid percentage
            # ------------------------------------------------------

            for grid in grids:

                percentage = (
                    grid.km_to_digitize
                    / total_km
                ) * 100

                percentage = round(
                    percentage,
                    2
                )

                if (
                    grid.percentage_of_total_streets
                    != percentage
                ):

                    Grid.objects.filter(
                        pk=grid.pk
                    ).update(
                        percentage_of_total_streets=
                            percentage
                    )

        # ==========================================================
        # SYNCHRONIZE REVIEW DAYS
        # ==========================================================

        self.stdout.write(
            "Synchronizing Review schedule..."
        )

        for authority_id in affected_authorities:

            authority = (
                Authority.objects
                .get(
                    pk=authority_id
                )
            )

            authority.sync_review_days()

        # ==========================================================
        # OUTPUT
        # ==========================================================

        self.stdout.write(
            self.style.SUCCESS(
                f"Grids: "
                f"{created_count} created, "
                f"{updated_count} updated, "
                f"{skipped_count} skipped."
            )
        )

    # ==========================================================
    # REVIEW SOURCE READER
    # ==========================================================

    def read_review_source(
        self,
        source
    ):

        path = Path(source)

        if not path.exists():

            raise CommandError(
                f"Review source does not exist:\n"
                f"{source}"
            )

        suffix = path.suffix.lower()

        # ------------------------------------------------------
        # CSV
        # ------------------------------------------------------

        if suffix == ".csv":

            with open(
                path,
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                return list(
                    csv.DictReader(file)
                )

        # ------------------------------------------------------
        # JSON
        # ------------------------------------------------------

        if suffix == ".json":

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )

            if isinstance(
                data,
                dict
            ):

                if data.get(
                    "type"
                ) == "FeatureCollection":

                    rows = []

                    for feature in data.get(
                        "features",
                        []
                    ):

                        rows.append(
                            feature.get(
                                "properties",
                                {}
                            )
                        )

                    return rows

                return [
                    data
                ]

            return data

        # ------------------------------------------------------
        # GeoJSON
        # ------------------------------------------------------

        if suffix == ".geojson":

            gdf = gpd.read_file(
                path
            )

            return gdf.drop(
                columns="geometry",
                errors="ignore"
            ).to_dict(
                orient="records"
            )

        raise CommandError(
            "Unsupported Review format. "
            "Use CSV, JSON or GeoJSON."
        )

    # ==========================================================
    # REVIEW IMPORT
    # ==========================================================

    @transaction.atomic
    def import_reviews(
        self,
        source
    ):

        rows = self.read_review_source(
            source
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for row in rows:

            authority_name = self.get_field(
                row,
                "Authority",
                "AuthorityName",
                "AUTHORITY",
                "AUTHORITY_NAME",
                "authority_name"
            )

            day = self.get_field(
                row,
                "day",
                "DAY"
            )

            total_km_reviewed = self.get_field(
                row,
                "total_km_reviewed",
                "totalKmReviewed",
                "TOTAL_KM_REVIEWED",
                default=0
            )

            # --------------------------------------------------
            # Validate Authority
            # --------------------------------------------------

            if not authority_name:

                skipped_count += 1
                continue

            authority = (
                Authority.objects
                .filter(
                    name=str(
                        authority_name
                    ).strip()
                )
                .first()
            )

            if not authority:

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping Review Day "
                        f"{day}: Authority "
                        f"'{authority_name}' "
                        f"does not exist."
                    )
                )

                skipped_count += 1
                continue

            # --------------------------------------------------
            # Validate day
            # --------------------------------------------------

            try:

                day = int(
                    day
                )

            except (
                TypeError,
                ValueError
            ):

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping Review for "
                        f"Authority "
                        f"'{authority_name}': "
                        f"invalid day '{day}'."
                    )
                )

                skipped_count += 1
                continue

            if day <= 0:

                skipped_count += 1
                continue

            # --------------------------------------------------
            # Validate reviewed km
            # --------------------------------------------------

            try:

                total_km_reviewed = float(
                    total_km_reviewed or 0
                )

            except (
                TypeError,
                ValueError
            ):

                total_km_reviewed = 0.0

            # --------------------------------------------------
            # Create / update
            # --------------------------------------------------

            if self.update_existing:

                review, created = (
                    Review.objects.update_or_create(
                        authority=authority,
                        day=day,
                        defaults={
                            "total_km_reviewed":
                                total_km_reviewed,
                            "is_active": True,
                        }
                    )
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            else:

                review_exists = (
                    Review.objects.filter(
                        authority=authority,
                        day=day
                    ).exists()
                )

                if review_exists:

                    skipped_count += 1
                    continue

                Review.objects.create(
                    authority=authority,
                    day=day,
                    total_km_reviewed=
                        total_km_reviewed,
                    is_active=True
                )

                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Reviews: "
                f"{created_count} created, "
                f"{updated_count} updated, "
                f"{skipped_count} skipped."
            )
        )