"""
Yahoo Finance data loader.
yfinance 데이터 로더

VIX, MOVE, S&P 500 등 시장 데이터 로딩
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pandas as pd

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from .base import DataLoader, DataSchema


class YFinanceLoader(DataLoader):
    """
    Yahoo Finance data loader using yfinance.
    
    Supports:
        - ^VIX: CBOE Volatility Index
        - ^GSPC: S&P 500
        - ^MOVE: MOVE Index (if available)
        - HYG: High Yield ETF (proxy for HY market)
        - LQD: IG Bond ETF (proxy for IG market)
    """
    
    # Ticker to name mapping
    TICKER_NAMES: Dict[str, str] = {
        '^VIX': 'VIX',
        '^GSPC': 'S&P 500',
        '^MOVE': 'MOVE',
        'HYG': 'HY ETF',
        'LQD': 'IG ETF',
        'SPY': 'SPY',
        'TLT': 'TLT',
        '^TNX': '10Y Yield',
    }
    
    def __init__(self, schema: Optional[DataSchema] = None):
        """Initialize yfinance loader."""
        super().__init__(schema)
        
        if not YFINANCE_AVAILABLE:
            print("Warning: yfinance not available. Install with: pip install yfinance")
    
    def load(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        field: str = 'Close',
    ) -> pd.DataFrame:
        """
        Load Yahoo Finance data.
        
        Args:
            ticker: Yahoo Finance ticker (e.g., '^VIX', '^GSPC')
            start_date: Start date (default: 5 years ago)
            end_date: End date (default: today)
            field: Price field to use ('Close', 'Adj Close', 'Open', 'High', 'Low')
            
        Returns:
            DataFrame with columns: date, value, indicator
        """
        if not YFINANCE_AVAILABLE:
            raise RuntimeError("yfinance not available")
        
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 5)
        
        # Check cache
        cache_key = self._get_cache_key(ticker, start_date, end_date)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Download data
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
            )
            
            if data.empty:
                raise ValueError(f"No data returned for {ticker}")
            
            # Handle multi-level columns from yfinance
            if isinstance(data.columns, pd.MultiIndex):
                # Get the first level (price type)
                data.columns = data.columns.get_level_values(0)
            
            # Get the specified field
            if field not in data.columns:
                field = 'Close'  # Fallback to Close
            
            values = data[field]
            
            # Convert to DataFrame with standard schema
            indicator_name = self.TICKER_NAMES.get(ticker, ticker)
            df = pd.DataFrame({
                'date': values.index,
                'value': values.values,
                'indicator': indicator_name,
            })
            
            # Handle missing values
            df = self.handle_missing_values(df, method='ffill')
            
            # Cache and return
            self._set_cache(cache_key, df)
            return df
            
        except Exception as e:
            raise RuntimeError(f"Failed to load {ticker} from yfinance: {e}")
    
    def load_all_minimum_set(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load all minimum set yfinance indicators.
        
        Returns:
            Combined DataFrame in long format
        """
        yf_tickers = [
            '^VIX',   # Volatility
            '^GSPC',  # S&P 500
        ]
        
        return self.load_multiple(yf_tickers, start_date, end_date)
    
    def load_with_returns(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load data with calculated returns.
        
        Returns:
            DataFrame with columns: date, value, indicator, return_1d, return_1w, return_1m
        """
        df = self.load(ticker, start_date, end_date)
        
        if df.empty:
            return df
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calculate returns
        df['return_1d'] = df['value'].pct_change(1) * 100
        df['return_1w'] = df['value'].pct_change(5) * 100
        df['return_1m'] = df['value'].pct_change(21) * 100
        
        return df
    
    def is_available(self) -> bool:
        """Check if yfinance is available."""
        return YFINANCE_AVAILABLE
