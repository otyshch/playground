"""
API router for fiscal data endpoints.
"""
import csv
import io
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse

from ...shared.models import (
    StateFiscalData,
    StateFiscalDataResponse,
    StateFiscalIndicators,
)
from ...shared.config import US_STATE_CODES, STATE_NAMES
from ..services.fiscal_service import FiscalDataService
from ..dependencies import get_fiscal_service
from ...ingestion.data_service import StateFiscalDataService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{state}",
    response_model=StateFiscalDataResponse,
    summary="Get fiscal data for a state",
    description="Retrieve the latest fiscal indicators for a specific state on or before the specified date"
)
async def get_fiscal_data(
    state: str,
    date: Optional[datetime] = Query(
        None,
        description="Target date for fiscal data (YYYY-MM-DD). Defaults to current date.",
        example="2023-12-31"
    ),
    fiscal_service: FiscalDataService = Depends(get_fiscal_service)
) -> StateFiscalDataResponse:
    """
    Get fiscal data for a specific state.

    **SFF-DC-01**: Synchronous API endpoint accepting state and date parameters
    **SFF-DC-02**: Returns latest data on or before specified date
    **SFF-DC-03**: JSON response conforms to specified schema
    """
    # Validate state code
    state_code = state.upper()
    if state_code not in US_STATE_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state code: {state}. Must be a valid US state postal code."
        )

    # Default to current date if not provided
    if date is None:
        date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        fiscal_data = await fiscal_service.get_latest_data(state_code, date)

        if fiscal_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"No fiscal data found for {state_code} on or before {date.strftime('%Y-%m-%d')}"
            )

        # Convert to response model
        response = StateFiscalDataResponse(
            data_timestamp=fiscal_data.data_timestamp,
            state=fiscal_data.state_code,
            state_fiscal_indicators=StateFiscalIndicators(
                state_tax_receipts_yoy_growth=fiscal_data.state_tax_receipts_yoy_growth,
                state_budget_surplus_deficit_as_pct_of_gsp=fiscal_data.state_budget_surplus_deficit_as_pct_of_gsp
            )
        )

        logger.info(
            "Fiscal data retrieved",
            state=state_code,
            date=date.strftime('%Y-%m-%d'),
            data_timestamp=fiscal_data.data_timestamp.strftime('%Y-%m-%d')
        )

        return response

    except Exception as e:
        logger.error(f"Error retrieving fiscal data for {state_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving fiscal data"
        )


@router.get(
    "/bulk",
    summary="Export historical fiscal data",
    description="Export fiscal data in CSV or JSON format for historical analysis"
)
async def export_bulk_data(
    format: str = Query(
        "csv",
        description="Export format",
        regex="^(csv|json)$"
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Start date for export (YYYY-MM-DD)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date for export (YYYY-MM-DD)"
    ),
    states: Optional[str] = Query(
        None,
        description="Comma-separated list of state codes (e.g., 'CA,NY,TX')"
    ),
    fiscal_service: FiscalDataService = Depends(get_fiscal_service)
):
    """
    Export historical fiscal data in bulk.

    **SFF-DC-04**: Provides mechanism to retrieve historical data file
    **SFF-DC-05**: Column headers match data dictionary field names exactly
    """
    try:
        # Parse state codes if provided
        state_list = None
        if states:
            state_list = [s.strip().upper() for s in states.split(",")]
            # Validate state codes
            invalid_states = [s for s in state_list if s not in US_STATE_CODES]
            if invalid_states:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid state codes: {', '.join(invalid_states)}"
                )

        # Get bulk data
        data = await fiscal_service.get_bulk_data(
            start_date=start_date,
            end_date=end_date,
            states=state_list
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail="No data found for the specified criteria"
            )

        if format == "csv":
            return _export_csv(data)
        else:  # json
            return _export_json(data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting bulk data: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while exporting data"
        )


@router.get(
    "/states",
    summary="List available states",
    description="Get list of all available US state codes and names"
)
async def list_states():
    """List all available US states with their codes and names."""
    states = [
        {
            "code": code,
            "name": STATE_NAMES[code]
        }
        for code in US_STATE_CODES
    ]

    return {
        "states": states,
        "total_count": len(states)
    }


@router.get(
    "/{state}/history",
    summary="Get historical data for a state",
    description="Retrieve historical fiscal data for a specific state within a date range"
)
async def get_state_history(
    state: str,
    start_date: Optional[datetime] = Query(
        None,
        description="Start date for historical data (YYYY-MM-DD)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date for historical data (YYYY-MM-DD)"
    ),
    limit: int = Query(
        100,
        description="Maximum number of records to return",
        ge=1,
        le=1000
    ),
    fiscal_service: FiscalDataService = Depends(get_fiscal_service)
):
    """Get historical fiscal data for a specific state."""
    # Validate state code
    state_code = state.upper()
    if state_code not in US_STATE_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state code: {state}"
        )

    try:
        data = await fiscal_service.get_state_history(
            state_code=state_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        # Convert to response format
        history = []
        for record in data:
            history.append({
                "data_timestamp": record.data_timestamp,
                "state_tax_receipts_yoy_growth": record.state_tax_receipts_yoy_growth,
                "state_budget_surplus_deficit_as_pct_of_gsp": record.state_budget_surplus_deficit_as_pct_of_gsp
            })

        return {
            "state": state_code,
            "state_name": STATE_NAMES[state_code],
            "start_date": start_date,
            "end_date": end_date,
            "records": history,
            "record_count": len(history)
        }

    except Exception as e:
        logger.error(f"Error retrieving history for {state_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving historical data"
        )


def _export_csv(data: List[StateFiscalData]) -> StreamingResponse:
    """Export data as CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header with exact field names from data dictionary
    writer.writerow([
        "timestamp",
        "state",
        "state_tax_receipts_yoy_growth",
        "state_budget_surplus_deficit_as_pct_of_gsp"
    ])

    # Write data rows
    for record in data:
        writer.writerow([
            record.data_timestamp.strftime('%Y-%m-%d'),
            record.state_code,
            record.state_tax_receipts_yoy_growth,
            record.state_budget_surplus_deficit_as_pct_of_gsp
        ])

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=state_fiscal_data.csv"}
    )


def _export_json(data: List[StateFiscalData]) -> Response:
    """Export data as JSON format."""
    json_data = []

    for record in data:
        json_data.append({
            "timestamp": record.data_timestamp.strftime('%Y-%m-%d'),
            "state": record.state_code,
            "state_tax_receipts_yoy_growth": record.state_tax_receipts_yoy_growth,
            "state_budget_surplus_deficit_as_pct_of_gsp": record.state_budget_surplus_deficit_as_pct_of_gsp
        })

    return Response(
        content=str(json_data),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=state_fiscal_data.json"}
    )


@router.post(
    "/populate/{state}",
    summary="Populate fiscal data for a state",
    description="Trigger data population from FRED API for a specific state"
)
async def populate_state_data(
    state: str,
    days_back: int = Query(
        365,
        description="Number of days back to populate data",
        ge=1,
        le=1095
    ),
    fiscal_service: FiscalDataService = Depends(get_fiscal_service)
):
    """
    Trigger data population from FRED API for a specific state.

    This endpoint will fetch and populate fiscal data from the FRED API
    for the specified state, going back the specified number of days.
    """
    # Validate state code
    state_code = state.upper()
    if state_code not in US_STATE_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state code: {state}. Must be a valid US state postal code."
        )

    try:
        # Initialize the data service
        data_service = StateFiscalDataService()

        # Populate data for the specific state
        logger.info(f"Starting data population for {state_code} (last {days_back} days)")

        result = await data_service.populate_state_data(
            state_code=state_code,
            days_back=days_back
        )

        logger.info(f"Data population completed for {state_code}")

        return {
            "state": state_code,
            "state_name": STATE_NAMES[state_code],
            "days_back": days_back,
            "status": "success",
            "message": f"Data populated for {state_code}",
            "records_processed": result.get("records_processed", 0),
            "details": result
        }

    except Exception as e:
        logger.error(f"Error populating data for {state_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to populate data for {state_code}: {str(e)}"
        )


@router.post(
    "/populate/all",
    summary="Populate fiscal data for all states",
    description="Trigger data population from FRED API for all US states"
)
async def populate_all_states_data(
    days_back: int = Query(
        365,
        description="Number of days back to populate data",
        ge=1,
        le=1095
    ),
    fiscal_service: FiscalDataService = Depends(get_fiscal_service)
):
    """
    Trigger data population from FRED API for all US states.

    This endpoint will fetch and populate fiscal data from the FRED API
    for all US states, going back the specified number of days.
    """
    try:
        # Initialize the data service
        data_service = StateFiscalDataService()

        logger.info(f"Starting data population for all states (last {days_back} days)")

        result = await data_service.initialize_startup_data(days_back=days_back)

        logger.info("Data population completed for all states")

        return {
            "states_processed": len(US_STATE_CODES),
            "days_back": days_back,
            "status": "success",
            "message": "Data populated for all states",
            "details": result
        }

    except Exception as e:
        logger.error(f"Error populating data for all states: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to populate data for all states: {str(e)}"
        )


@router.get(
    "/{state}/auto-populate",
    response_model=StateFiscalDataResponse,
    summary="Get fiscal data with auto-population",
    description="Retrieve fiscal data for a state, automatically populating from FRED API if data is missing"
)
async def get_fiscal_data_with_auto_populate(
    state: str,
    date: Optional[datetime] = Query(
        None,
        description="Target date for fiscal data (YYYY-MM-DD). Defaults to current date.",
        example="2023-12-31"
    ),
    fiscal_service: FiscalDataService = Depends(get_fiscal_service)
) -> StateFiscalDataResponse:
    """
    Get fiscal data for a specific state with automatic population.

    This endpoint first checks if data exists for the requested state and date.
    If no data is found, it automatically triggers data population from FRED API
    and then returns the populated data.
    """
    # Validate state code
    state_code = state.upper()
    if state_code not in US_STATE_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state code: {state}. Must be a valid US state postal code."
        )

    # Default to current date if not provided
    if date is None:
        date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        # First, try to get existing data
        fiscal_data = await fiscal_service.get_latest_data(state_code, date)

        # If no data found, trigger population
        if fiscal_data is None:
            logger.info(f"No data found for {state_code} on {date.strftime('%Y-%m-%d')}, triggering auto-population")

            # Initialize the data service and populate data
            data_service = StateFiscalDataService()
            await data_service.populate_state_data(
                state_code=state_code,
                days_back=365  # Default to 1 year back
            )

            # Try to get data again after population
            fiscal_data = await fiscal_service.get_latest_data(state_code, date)

            if fiscal_data is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"No fiscal data could be populated for {state_code} on or before {date.strftime('%Y-%m-%d')}"
                )

        # Convert to response model
        response = StateFiscalDataResponse(
            data_timestamp=fiscal_data.data_timestamp,
            state=fiscal_data.state_code,
            state_fiscal_indicators=StateFiscalIndicators(
                state_tax_receipts_yoy_growth=fiscal_data.state_tax_receipts_yoy_growth,
                state_budget_surplus_deficit_as_pct_of_gsp=fiscal_data.state_budget_surplus_deficit_as_pct_of_gsp
            )
        )

        logger.info(
            "Fiscal data retrieved with auto-population",
            state=state_code,
            date=date.strftime('%Y-%m-%d'),
            data_timestamp=fiscal_data.data_timestamp.strftime('%Y-%m-%d')
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving fiscal data with auto-population for {state_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving fiscal data with auto-population"
        )
