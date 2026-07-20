from .common import router as common_router
from .download import router as download_router
from .stats import router as stats_router

routers = (common_router, stats_router, download_router)

__all__ = ["routers"]
