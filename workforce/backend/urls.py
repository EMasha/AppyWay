
from rest_framework.routers import DefaultRouter

from .viewsets import *


router = DefaultRouter()

router.register(
    r"projects",
    ManagerAuthorityViewSet,
    basename="manager-projects"
)

router.register(
    r"grids",
    ManagerGridViewSet,
    basename="manager-grids"
)

router.register(
    r"reviews",
    ManagerReviewViewSet,
    basename="manager-reviews"
)

router.register(
    r"employees",
    ManagerEmployeeViewSet,
    basename="manager-employees"
)


urlpatterns = router.urls


