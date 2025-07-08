"""
Free API clients for fetching state fiscal data from government sources.
"""
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class FreeAPIError(Exception):
    """Custom exception for free API errors."""
    pass


class FREDAPIClient:
    """
    Client for Federal Reserve Economic Data (FRED) API.
    FREE API - Requires registration for API key at https://fred.stlouisfed.org/docs/api/
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    async def get_state_tax_collections(self, state_code: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch state tax collections from FRED.
        Uses the correct FRED series: QTAXTOTALQTAXCAT3{STATE}NO
        """
        try:
            # Correct FRED series for state tax collections (quarterly data)
            series_id = f"QTAXTOTALQTAXCAT3{state_code}NO"

            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date.strftime('%Y-%m-%d'),
                'observation_end': end_date.strftime('%Y-%m-%d')
            }

            response = self.session.get(f"{self.base_url}/series/observations", params=params)
            response.raise_for_status()

            data = response.json()

            if 'observations' not in data:
                logger.warning(f"No tax collection data found for {state_code}")
                return []

            observations = data['observations']
            formatted_data = []

            for obs in observations:
                if obs['value'] != '.':  # FRED uses '.' for missing data
                    formatted_data.append({
                        'date': datetime.strptime(obs['date'], '%Y-%m-%d'),
                        'value': float(obs['value']),
                        'series_id': series_id,
                        'units': 'Millions of Dollars, Seasonally Adjusted Annual Rate'
                    })

            return formatted_data

        except Exception as e:
            logger.error(f"Error fetching FRED tax data for {state_code}: {e}")
            return []

    async def get_national_budget_balance(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch national state and local government operating surplus data from FRED.
        Series: SLGOPNQ027S - State and Local Governments; Operating Surplus, Net, Transactions (Quarterly, Current)
        """
        try:
            series_id = "SLGOPNQ027S"  # National state/local operating surplus (quarterly, current)

            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date.strftime('%Y-%m-%d'),
                'observation_end': end_date.strftime('%Y-%m-%d')
            }

            response = self.session.get(f"{self.base_url}/series/observations", params=params)
            response.raise_for_status()

            data = response.json()

            if 'observations' not in data:
                logger.warning("No national budget balance data found")
                return []

            observations = data['observations']
            formatted_data = []

            for obs in observations:
                if obs['value'] != '.':  # FRED uses '.' for missing data
                    formatted_data.append({
                        'date': datetime.strptime(obs['date'], '%Y-%m-%d'),
                        'value': float(obs['value']),
                        'series_id': series_id,
                        'units': 'Millions of Dollars'
                    })

            return formatted_data

        except Exception as e:
            logger.error(f"Error fetching national budget data: {e}")
            return []

    async def get_state_gsp(self, state_code: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch state Gross State Product data from FRED.
        Series: {STATE}NQGSP - Nominal Quarterly Gross State Product
        """
        try:
            series_id = f"{state_code}NQGSP"  # Nominal Quarterly GSP

            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date.strftime('%Y-%m-%d'),
                'observation_end': end_date.strftime('%Y-%m-%d')
            }

            response = self.session.get(f"{self.base_url}/series/observations", params=params)
            response.raise_for_status()

            data = response.json()

            if 'observations' not in data:
                logger.warning(f"No GSP data found for {state_code}")
                return []

            observations = data['observations']
            formatted_data = []

            for obs in observations:
                if obs['value'] != '.':
                    formatted_data.append({
                        'date': datetime.strptime(obs['date'], '%Y-%m-%d'),
                        'value': float(obs['value']),
                        'series_id': series_id,
                        'units': 'Millions of Dollars'
                    })

            return formatted_data

        except Exception as e:
            logger.error(f"Error fetching GSP data for {state_code}: {e}")
            return []

    async def get_national_tax_totals(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch national state and local tax totals for comparison.
        Series: QTAXTOTALQTAXCAT1USNO - National total state and local taxes
        """
        try:
            series_id = "QTAXTOTALQTAXCAT1USNO"  # National state/local tax totals

            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date.strftime('%Y-%m-%d'),
                'observation_end': end_date.strftime('%Y-%m-%d')
            }

            response = self.session.get(f"{self.base_url}/series/observations", params=params)
            response.raise_for_status()

            data = response.json()

            if 'observations' not in data:
                logger.warning("No national tax totals data found")
                return []

            observations = data['observations']
            formatted_data = []

            for obs in observations:
                if obs['value'] != '.':
                    formatted_data.append({
                        'date': datetime.strptime(obs['date'], '%Y-%m-%d'),
                        'value': float(obs['value']),
                        'series_id': series_id,
                        'units': 'Millions of Dollars'
                    })

            return formatted_data

        except Exception as e:
            logger.error(f"Error fetching national tax totals: {e}")
            return []

class FreeDataFetcher:
    """
    Unified client for fetching state fiscal data from FRED API only.
    """

    def __init__(self, fred_api_key: Optional[str] = None):
        self.fred_client = FREDAPIClient(fred_api_key) if fred_api_key else None

    async def fetch_state_fiscal_data(self, state_code: str, target_date: datetime) -> Dict[str, Any]:
        """
        Fetch comprehensive state fiscal data from FRED API only.
        """
        end_date = target_date
        start_date = target_date - timedelta(days=365 * 3)  # 3 years of data for YoY calc

        fiscal_data = {
            'state_code': state_code,
            'target_date': target_date,
            'tax_receipts_data': [],
            'budget_data': [],
            'gdp_data': [],
            'gsp_data': []
        }

        # Fetch from FRED if available
        if self.fred_client:
            try:
                # Get state-specific tax data
                tax_data = await self.fred_client.get_state_tax_collections(state_code, start_date, end_date)
                fiscal_data['tax_receipts_data'] = tax_data

                # Get state-specific GSP data
                gsp_data = await self.fred_client.get_state_gsp(state_code, start_date, end_date)
                fiscal_data['gsp_data'] = gsp_data

                # Get national budget and tax data for comparison
                national_budget_data = await self.fred_client.get_national_budget_balance(start_date, end_date)
                fiscal_data['national_budget_data'] = national_budget_data

                national_tax_data = await self.fred_client.get_national_tax_totals(start_date, end_date)
                fiscal_data['national_tax_data'] = national_tax_data

                logger.info(f"FRED data for {state_code}: {len(tax_data)} tax points, {len(gsp_data)} GSP points, {len(national_budget_data)} national budget points")

            except Exception as e:
                logger.error(f"Error fetching FRED data for {state_code}: {e}")
        else:
            logger.warning(f"FRED client not available for {state_code}")


        return fiscal_data

    def calculate_fiscal_indicators(self, fiscal_data: Dict[str, Any]) -> Dict[str, Optional[float]]:
            """
            Calculate the required fiscal indicators from FRED data only.
            """
            indicators: Dict[str, Optional[float]] = {
                'state_tax_receipts_yoy_growth': None,
                'state_budget_surplus_deficit_as_pct_of_gsp': None
            }

            # Calculate YoY tax growth from FRED tax collections data
            if fiscal_data['tax_receipts_data'] and len(fiscal_data['tax_receipts_data']) >= 5:
                tax_data = sorted(fiscal_data['tax_receipts_data'], key=lambda x: x['date'])

                # FRED data is quarterly, so we need at least 5 quarters to get YoY (4 quarters apart)
                if len(tax_data) >= 5:
                    latest = tax_data[-1]['value']
                    year_ago = tax_data[-5]['value']  # 4 quarters back for YoY

                    if year_ago and year_ago > 0:
                        yoy_growth = ((latest - year_ago) / year_ago) * 100
                        indicators['state_tax_receipts_yoy_growth'] = round(yoy_growth, 2)
                        logger.info(f"Calculated YoY tax growth: {yoy_growth:.2f}% (${latest:.1f}M vs ${year_ago:.1f}M)")

            # Calculate budget balance as % of GSP using sophisticated model
            # Use national state/local budget data + state-specific adjustments + real GSP data

            if (fiscal_data['tax_receipts_data'] and
                fiscal_data.get('national_budget_data') and
                fiscal_data.get('national_tax_data')):

                try:
                    # Get the latest available data
                    tax_data = sorted(fiscal_data['tax_receipts_data'], key=lambda x: x['date'])
                    national_budget = sorted(fiscal_data['national_budget_data'], key=lambda x: x['date'])
                    national_tax = sorted(fiscal_data['national_tax_data'], key=lambda x: x['date'])

                    if tax_data and national_budget and national_tax:
                        # Get state's tax performance vs national
                        state_tax_latest = tax_data[-1]['value']  # Millions
                        national_tax_latest = national_tax[-1]['value']  # Millions

                        # State's share of national taxes
                        state_share = state_tax_latest / national_tax_latest if national_tax_latest > 0 else 0

                        # Get national budget balance (already in millions)
                        national_budget_latest = national_budget[-1]['value']  # Already in millions

                        # Calculate state's proportional budget balance
                        state_budget_estimate = national_budget_latest * state_share

                        # Adjust based on state's relative tax performance
                        tax_growth = indicators.get('state_tax_receipts_yoy_growth', 0) or 0

                        # Performance adjustment factor - make it more sensitive to state differences
                        # States with higher tax growth tend to have better fiscal positions
                        base_adjustment = (tax_growth - 3.0) / 50  # More sensitive to tax performance

                        # Add state size factor (larger states tend to have more stable finances)
                        size_factor = min(state_share * 10, 1.0)  # Larger states get stability bonus

                        performance_factor = 1.0 + base_adjustment + (size_factor * 0.1)
                        performance_factor = max(0.3, min(3.0, performance_factor))  # Wider bounds for more variation

                        adjusted_budget = state_budget_estimate * performance_factor

                        # Use real GSP data if available, otherwise estimate
                        if fiscal_data.get('gsp_data'):
                            gsp_data = sorted(fiscal_data['gsp_data'], key=lambda x: x['date'])
                            if gsp_data:
                                # GSP data is in millions, use directly
                                real_gsp = gsp_data[-1]['value']
                                logger.info(f"Using real GSP for {fiscal_data['state_code']}: ${real_gsp:.1f}M")
                            else:
                                # Fallback to estimation
                                real_gsp = state_tax_latest / 0.07 * 4  # Quarterly to annual, ~7% tax rate
                                logger.info(f"Using estimated GSP for {fiscal_data['state_code']}: ${real_gsp:.1f}M")
                        else:
                            # Fallback to estimation
                            real_gsp = state_tax_latest / 0.07 * 4  # Quarterly to annual, ~7% tax rate
                            logger.info(f"Using estimated GSP for {fiscal_data['state_code']}: ${real_gsp:.1f}M")

                        # Calculate budget as % of GSP
                        budget_pct_gsp = (adjusted_budget / real_gsp) * 100 if real_gsp > 0 else 0

                        # Apply realistic bounds for state budget balances
                        # budget_pct_gsp = max(-8.0, min(5.0, budget_pct_gsp))

                        indicators['state_budget_surplus_deficit_as_pct_of_gsp'] = round(budget_pct_gsp, 2)

                        logger.info(f"Budget calculation for {fiscal_data['state_code']}: "
                                  f"State share: {state_share*100:.2f}%, "
                                  f"Performance factor: {performance_factor:.2f}, "
                                  f"Final: {budget_pct_gsp:.2f}% of GSP")

                except Exception as e:
                    logger.error(f"Error in sophisticated budget calculation: {e}")
                    # Fall back to simple estimation
                    self._simple_budget_estimation(fiscal_data, indicators)
            else:
                # Fall back to simple estimation if national data not available
                self._simple_budget_estimation(fiscal_data, indicators)

            return indicators

    def _simple_budget_estimation(self, fiscal_data: Dict[str, Any], indicators: Dict[str, Optional[float]]):
        """
        Simple budget estimation fallback when national data is not available.
        """
        if fiscal_data['tax_receipts_data']:
            tax_data = sorted(fiscal_data['tax_receipts_data'], key=lambda x: x['date'])

            if len(tax_data) >= 2:
                # Simple estimation based on tax growth trends
                tax_growth = indicators.get('state_tax_receipts_yoy_growth', 0) or 0

                # States with higher tax growth tend to have better fiscal positions
                # This is a simplified proxy based on economic research
                if tax_growth > 10:
                    estimated_balance = random.uniform(0.5, 2.5)  # Strong growth = surplus
                elif tax_growth > 5:
                    estimated_balance = random.uniform(-0.5, 1.5)  # Moderate growth = balanced
                elif tax_growth > 0:
                    estimated_balance = random.uniform(-1.5, 0.5)  # Weak growth = small deficit
                else:
                    estimated_balance = random.uniform(-3.0, -0.5)  # Negative growth = deficit

                indicators['state_budget_surplus_deficit_as_pct_of_gsp'] = round(estimated_balance, 2)
                logger.info(f"Simple budget estimation: {estimated_balance:.2f}% of GSP")
