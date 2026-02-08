"""
FRED (Federal Reserve Economic Data) loader.
FRED 데이터 로더

Fed Total Assets, Bank Credit, M2, Credit Spreads 등 매크로 지표 로딩
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import pandas as pd

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False

try:
    import pandas_datareader as pdr
    PDR_AVAILABLE = True
except ImportError:
    PDR_AVAILABLE = False

from .base import DataLoader, DataSchema


class FREDLoader(DataLoader):
    """
    FRED data loader using fredapi or pandas-datareader.

    Supports:
        - WALCL: Fed Total Assets
        - WRESBAL: Reserve Balances with Fed
        - RRPONTSYD: Reverse Repo (Treasury)
        - WTREGEN: Treasury General Account
        - WLCFLPCL: Fed Lending (Combined)
        - TOTBKCR: Commercial Bank Credit
        - M2SL: M2 Money Supply
        - BAMLH0A0HYM2: High Yield Spread
        - BAMLC0A0CM: IG Spread
        - DFII10: 10Y Real Yield (TIPS)
        - T10YIE: 10Y Breakeven Inflation
        - NFCI: Financial Conditions Index
    """

    # Ticker to name mapping
    TICKER_NAMES: Dict[str, str] = {
        'WALCL': 'Fed Total Assets',
        'WRESBAL': 'Reserve Balances',
        'RRPONTSYD': 'Reverse Repo',
        'WTREGEN': 'TGA Balance',
        'WLCFLPCL': 'Fed Lending',
        'TOTBKCR': 'Bank Credit',
        'M2SL': 'M2',
        'BAMLH0A0HYM2': 'HY Spread',
        'BAMLC0A0CM': 'IG Spread',
        'DFII10': 'Real Yield 10Y',
        'T10YIE': 'Breakeven 10Y',
        'NFCI': 'FCI',
        'TOTALSL': 'Consumer Credit',
        'SOFR': 'SOFR',
        'WLDWSL': 'Discount Window Lending',
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        schema: Optional[DataSchema] = None,
    ):
        """
        Initialize FRED loader.
        
        Args:
            api_key: FRED API key (optional, uses pandas-datareader if not provided)
            schema: Data schema configuration
        """
        super().__init__(schema)
        self.api_key = api_key
        self._fred = None
        
        if api_key and FRED_AVAILABLE:
            self._fred = Fred(api_key=api_key)
    
    def load(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load FRED series data.
        
        Args:
            ticker: FRED series ID (e.g., 'WALCL', 'M2SL')
            start_date: Start date (default: 5 years ago)
            end_date: End date (default: today)
            
        Returns:
            DataFrame with columns: date, value, indicator
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 5)
        
        # Check cache
        cache_key = self._get_cache_key(ticker, start_date, end_date)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # Try fredapi first, then pandas-datareader
        series_data = None
        
        if self._fred is not None:
            try:
                series_data = self._fred.get_series(
                    ticker,
                    observation_start=start_date,
                    observation_end=end_date,
                )
            except Exception as e:
                print(f"fredapi failed for {ticker}: {e}")
        
        if series_data is None and PDR_AVAILABLE:
            try:
                series_data = pdr.DataReader(
                    ticker,
                    'fred',
                    start=start_date,
                    end=end_date,
                )[ticker]
            except Exception as e:
                raise RuntimeError(f"Failed to load {ticker} from FRED: {e}")
        
        if series_data is None:
            raise RuntimeError(
                f"Cannot load {ticker}: neither fredapi nor pandas-datareader available"
            )
        
        # Convert to DataFrame with standard schema
        indicator_name = self.TICKER_NAMES.get(ticker, ticker)
        df = pd.DataFrame({
            'date': series_data.index,
            'value': series_data.values,
            'indicator': indicator_name,
        })
        
        # Handle missing values
        df = self.handle_missing_values(df, method='ffill')
        
        # Cache and return
        self._set_cache(cache_key, df)
        return df
    
    def load_all_minimum_set(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load all minimum set FRED indicators including Fed balance sheet.

        Returns:
            Combined DataFrame in long format
        """
        fred_tickers = [
            'WALCL',           # Fed Total Assets
            'WRESBAL',         # Reserve Balances
            'RRPONTSYD',       # Reverse Repo
            'WTREGEN',         # TGA Balance
            'WLCFLPCL',        # Fed Lending
            'TOTBKCR',         # Bank Credit
            'M2SL',            # M2
            'BAMLH0A0HYM2',    # HY Spread
            'BAMLC0A0CM',      # IG Spread
            'DFII10',          # Real Yield
            'T10YIE',          # Breakeven
        ]

        return self.load_multiple(fred_tickers, start_date, end_date)

    def load_fed_balance_sheet(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load all Fed balance sheet indicators (FED_BALANCE_SHEET_INDICATORS).

        Loads the identity: Δ Reserves = Δ SOMA Assets + Δ Lending - Δ Reverse Repo - Δ TGA

        Args:
            start_date: Start date (default: 5 years ago)
            end_date: End date (default: today)

        Returns:
            Combined DataFrame in long format with all 6 Fed balance sheet indicators
        """
        fed_balance_sheet_tickers = [
            'WALCL',      # Fed SOMA Assets (Total Assets proxy)
            'WRESBAL',    # Fed Reserve Balances
            'RRPONTSYD',  # Reverse Repo Agreements
            'WTREGEN',    # Treasury General Account (TGA)
            'WLCFLPCL',   # Fed Lending Facilities (Total)
            'WLDWSL',     # Discount Window Lending
        ]

        return self.load_multiple(fed_balance_sheet_tickers, start_date, end_date)
    
    def is_available(self) -> bool:
        """Check if FRED data loading is available."""
        return FRED_AVAILABLE or PDR_AVAILABLE
