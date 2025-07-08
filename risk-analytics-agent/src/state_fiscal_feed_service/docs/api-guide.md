# State Fiscal Data Feed API Guide

## Overview

The State Fiscal Data Feed API provides programmatic access to state-level fiscal indicators for analyzing municipal securities and economic health. This RESTful API follows the OpenAPI 3.0 specification and provides consistent, reliable access to fiscal data.

## Base URL

```
https://api.statefiscalfeed.com/api/v1
```

For local development:
```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication for public fiscal data endpoints. Rate limiting is applied to ensure fair usage.

## Rate Limiting

- **Rate Limit**: 100 requests per minute per IP address
- **Burst Limit**: 10 requests per second per IP address

Rate limit information is provided in response headers:
- `X-RateLimit-Limit`: Request limit per minute
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Reset time as Unix timestamp

## Response Format

All API responses follow a consistent JSON format:

### Success Response
```json
{
  "data_timestamp": "2023-12-31T00:00:00",
  "state": "CA",
  "state_fiscal_indicators": {
    "state_tax_receipts_yoy_growth": 3.5,
    "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
  }
}
```

### Error Response
```json
{
  "error": "Error description",
  "message": "Detailed error message",
  "status_code": 400,
  "path": "/api/v1/fiscal-data/INVALID"
}
```

## Endpoints

### Get Fiscal Data for State

Retrieve the latest fiscal indicators for a specific state.

**Endpoint**: `GET /fiscal-data/{state}`

**Parameters**:
- `state` (path, required): Two-letter state postal code (e.g., "CA", "NY", "TX")
- `date` (query, optional): Target date in YYYY-MM-DD format. Returns latest data on or before this date.

**Example Request**:
```bash
curl "https://api.statefiscalfeed.com/api/v1/fiscal-data/CA?date=2023-12-31"
```

**Example Response**:
```json
{
  "data_timestamp": "2023-12-31T00:00:00",
  "state": "CA",
  "state_fiscal_indicators": {
    "state_tax_receipts_yoy_growth": 3.5,
    "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
  }
}
```

**Status Codes**:
- `200`: Success
- `400`: Invalid state code
- `404`: No data found for the specified criteria
- `429`: Rate limit exceeded

### Get Historical Data for State

Retrieve historical fiscal data for a specific state within a date range.

**Endpoint**: `GET /fiscal-data/{state}/history`

**Parameters**:
- `state` (path, required): Two-letter state postal code
- `start_date` (query, optional): Start date in YYYY-MM-DD format
- `end_date` (query, optional): End date in YYYY-MM-DD format
- `limit` (query, optional): Maximum records to return (1-1000, default: 100)

**Example Request**:
```bash
curl "https://api.statefiscalfeed.com/api/v1/fiscal-data/CA/history?start_date=2023-01-01&end_date=2023-12-31&limit=50"
```

**Example Response**:
```json
{
  "state": "CA",
  "state_name": "California",
  "start_date": "2023-01-01T00:00:00",
  "end_date": "2023-12-31T00:00:00",
  "records": [
    {
      "data_timestamp": "2023-12-31T00:00:00",
      "state_tax_receipts_yoy_growth": 3.5,
      "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
    }
  ],
  "record_count": 1
}
```

### Export Bulk Data

Export historical fiscal data in CSV or JSON format for multiple states.

**Endpoint**: `GET /fiscal-data/bulk`

**Parameters**:
- `format` (query, optional): Export format - "csv" or "json" (default: "csv")
- `start_date` (query, optional): Start date in YYYY-MM-DD format
- `end_date` (query, optional): End date in YYYY-MM-DD format
- `states` (query, optional): Comma-separated list of state codes (e.g., "CA,NY,TX")

**Example Request**:
```bash
curl "https://api.statefiscalfeed.com/api/v1/fiscal-data/bulk?format=csv&states=CA,NY,TX&start_date=2023-01-01"
```

**CSV Response Headers**:
```
timestamp,state,state_tax_receipts_yoy_growth,state_budget_surplus_deficit_as_pct_of_gsp
```

**CSV Response Example**:
```
2023-12-31,CA,3.5,-1.2
2023-12-31,NY,2.8,0.5
2023-12-31,TX,4.1,1.8
```

### List Available States

Get a list of all available US state codes and names.

**Endpoint**: `GET /fiscal-data/states`

**Example Request**:
```bash
curl "https://api.statefiscalfeed.com/api/v1/fiscal-data/states"
```

**Example Response**:
```json
{
  "states": [
    {
      "code": "AL",
      "name": "Alabama"
    },
    {
      "code": "AK",
      "name": "Alaska"
    }
  ],
  "total_count": 50
}
```

## Data Dictionary

### State Fiscal Indicators

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `state_tax_receipts_yoy_growth` | float | Year-over-year growth in total tax receipts for the state (percentage) |
| `state_budget_surplus_deficit_as_pct_of_gsp` | float | State budget surplus (positive) or deficit (negative) as percentage of Gross State Product |

### Response Metadata

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `data_timestamp` | datetime | Timestamp when the fiscal data was recorded (ISO 8601 format) |
| `state` | string | Two-letter state postal code |
| `state_name` | string | Full state name (in history endpoints) |

## Health Check Endpoints

### Basic Health Check

**Endpoint**: `GET /health`

Check if the API service is running.

**Example Response**:
```json
{
  "status": "healthy",
  "timestamp": "2023-12-31T10:00:00Z",
  "service": "State Fiscal Data Feed API",
  "version": "1.0.0"
}
```

### Detailed Health Check

**Endpoint**: `GET /health/detailed`

Comprehensive health check including database connectivity.

**Example Response**:
```json
{
  "status": "healthy",
  "timestamp": "2023-12-31T10:00:00Z",
  "service": "State Fiscal Data Feed API",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "configuration": {
      "status": "healthy",
      "message": "Configuration loaded successfully",
      "database_configured": true,
      "redis_configured": true,
      "external_apis_configured": true
    }
  }
}
```

### Readiness Probe

**Endpoint**: `GET /health/readiness`

Kubernetes readiness probe endpoint.

### Liveness Probe

**Endpoint**: `GET /health/liveness`

Kubernetes liveness probe endpoint.

## Metrics Endpoints

### Prometheus Metrics

**Endpoint**: `GET /metrics`

Prometheus-formatted metrics for monitoring.

**Example Response**:
```
state_fiscal_data_total_records 12500
state_fiscal_data_states_count 50
state_fiscal_data_records_by_state{state="CA"} 250
state_fiscal_data_latest_timestamp 1703980800
state_fiscal_data_freshness_days 1
```

### Detailed Statistics

**Endpoint**: `GET /metrics/stats`

Comprehensive statistics about the fiscal data.

### Data Quality Metrics

**Endpoint**: `GET /metrics/data-quality`

Data quality and completeness metrics.

## Error Handling

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request - Invalid parameters or state code
- `404`: Not Found - No data available for the requested criteria
- `422`: Validation Error - Invalid request format
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - Unexpected server error

### Error Response Format

All error responses follow this format:

```json
{
  "error": "Brief error description",
  "message": "Detailed error message",
  "status_code": 400,
  "path": "/api/v1/fiscal-data/INVALID"
}
```

## Best Practices

### Caching

- The API implements server-side caching with a 5-minute TTL
- Clients should implement their own caching for frequently accessed data
- Use ETags when available for conditional requests

### Pagination

- Use the `limit` parameter to control response size
- For large datasets, use the bulk export endpoints instead of pagination

### Date Handling

- All dates use ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
- Timezone is UTC
- Date-only parameters use YYYY-MM-DD format

### State Codes

- Always use uppercase two-letter postal codes
- Refer to the `/fiscal-data/states` endpoint for valid codes

## SDKs and Libraries

### Python

```python
import requests

class StateFiscalFeedClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def get_fiscal_data(self, state, date=None):
        url = f"{self.base_url}/api/v1/fiscal-data/{state}"
        params = {"date": date} if date else {}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_history(self, state, start_date=None, end_date=None, limit=100):
        url = f"{self.base_url}/api/v1/fiscal-data/{state}/history"
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

# Usage
client = StateFiscalFeedClient()
ca_data = client.get_fiscal_data("CA", "2023-12-31")
ca_history = client.get_history("CA", "2023-01-01", "2023-12-31")
```

### JavaScript/TypeScript

```typescript
interface FiscalData {
  data_timestamp: string;
  state: string;
  state_fiscal_indicators: {
    state_tax_receipts_yoy_growth: number;
    state_budget_surplus_deficit_as_pct_of_gsp: number;
  };
}

class StateFiscalFeedClient {
  constructor(private baseUrl = "http://localhost:8000") {}
  
  async getFiscalData(state: string, date?: string): Promise<FiscalData> {
    const url = new URL(`/api/v1/fiscal-data/${state}`, this.baseUrl);
    if (date) url.searchParams.set("date", date);
    
    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    return response.json();
  }
  
  async getHistory(state: string, options: {
    startDate?: string;
    endDate?: string;
    limit?: number;
  } = {}): Promise<any> {
    const url = new URL(`/api/v1/fiscal-data/${state}/history`, this.baseUrl);
    Object.entries(options).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, value.toString());
      }
    });
    
    const response = await fetch(url.toString());
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    return response.json();
  }
}

// Usage
const client = new StateFiscalFeedClient();
const caData = await client.getFiscalData("CA", "2023-12-31");
const caHistory = await client.getHistory("CA", {
  startDate: "2023-01-01",
  endDate: "2023-12-31"
});
```

## Support and Resources

- **API Documentation**: [Interactive Swagger UI](http://localhost:8000/docs)
- **ReDoc Documentation**: [ReDoc Interface](http://localhost:8000/redoc)
- **OpenAPI Specification**: [JSON Schema](http://localhost:8000/openapi.json)
- **GitHub Repository**: [Source Code and Issues](https://github.com/example/state-fiscal-feed)

## Changelog

### Version 1.0.0
- Initial release
- Basic fiscal data endpoints
- Health check and metrics endpoints
- CSV and JSON export formats
- Rate limiting and error handling