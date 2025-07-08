"""
FastAPI dependencies for dependency injection.
"""

from .services.fiscal_service import FiscalDataService

# Cache for service instances
_fiscal_service: FiscalDataService = None


def get_fiscal_service() -> FiscalDataService:
    """
    Dependency to get the fiscal data service instance.

    Returns:
        FiscalDataService instance
    """
    global _fiscal_service
    if _fiscal_service is None:
        _fiscal_service = FiscalDataService()
    return _fiscal_service
