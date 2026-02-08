"""
Abstract base class for data loaders.
데이터 로더 추상 클래스

모든 데이터 소스(FRED, yfinance, CSV)는 이 인터페이스를 구현합니다.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


@dataclass
class DataSchema:
    """
    Standard schema for all data.
    모든 데이터의 표준 스키마
    
    Attributes:
        date: 날짜 (index)
        value: 값
        indicator_name: 지표명
    """
    date_column: str = 'date'
    value_column: str = 'value'
    indicator_column: str = 'indicator'


class DataLoader(ABC):
    """
    Abstract base class for all data loaders.
    데이터 로더 추상 클래스
    """
    
    def __init__(self, schema: Optional[DataSchema] = None):
        self.schema = schema or DataSchema()
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl_hours: int = 6
    
    @abstractmethod
    def load(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load data for a single ticker.
        
        Args:
            ticker: Ticker symbol or series ID
            start_date: Start date (default: 5 years ago)
            end_date: End date (default: today)
            
        Returns:
            DataFrame with columns: date, value, indicator
        """
        pass
    
    def load_multiple(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load data for multiple tickers and combine.
        
        Includes small delay between calls to avoid rate limit bursts.
        
        Returns:
            DataFrame with columns: date, value, indicator (long format)
        """
        import time
        
        dfs = []
        for i, ticker in enumerate(tickers):
            try:
                df = self.load(ticker, start_date, end_date)
                dfs.append(df)
                
                # Small delay between successful loads to avoid bursts
                # (rate limiter handles main throttling, this is extra protection)
                if i < len(tickers) - 1:
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Warning: Failed to load {ticker}: {e}")
                # Small delay after failures too
                time.sleep(0.5)
        
        if not dfs:
            return pd.DataFrame()
        
        return pd.concat(dfs, ignore_index=True)
    
    def _get_cache_key(self, ticker: str, start_date: datetime, end_date: datetime) -> str:
        """Generate cache key."""
        return f"{ticker}_{start_date.isoformat()}_{end_date.isoformat()}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        elapsed = datetime.now() - self._cache_timestamps[cache_key]
        return elapsed < timedelta(hours=self._cache_ttl_hours)
    
    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get data from cache if valid."""
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        return None
    
    def _set_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """Store data in cache."""
        self._cache[cache_key] = data.copy()
        self._cache_timestamps[cache_key] = datetime.now()
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, schema: DataSchema) -> bool:
        """
        Validate DataFrame against schema.
        
        Returns:
            True if valid, raises ValueError if not
        """
        required_cols = [schema.date_column, schema.value_column, schema.indicator_column]
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Check date column is datetime-like
        if not pd.api.types.is_datetime64_any_dtype(df[schema.date_column]):
            # Try to convert
            try:
                df[schema.date_column] = pd.to_datetime(df[schema.date_column])
            except Exception:
                raise ValueError(f"Column {schema.date_column} cannot be converted to datetime")
        
        # Check value column is numeric
        if not pd.api.types.is_numeric_dtype(df[schema.value_column]):
            raise ValueError(f"Column {schema.value_column} must be numeric")
        
        return True
    
    @staticmethod
    def handle_missing_values(
        df: pd.DataFrame,
        method: str = 'ffill',
        winsorize_percentile: float = 0.01,
    ) -> pd.DataFrame:
        """
        Handle missing values and outliers.
        
        Args:
            df: Input DataFrame
            method: Fill method ('ffill', 'bfill', 'interpolate', 'drop')
            winsorize_percentile: Percentile for winsorization (0 to disable)
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        
        # Handle missing values
        if method == 'ffill':
            df = df.ffill()
        elif method == 'bfill':
            df = df.bfill()
        elif method == 'interpolate':
            df = df.interpolate(method='time')
        elif method == 'drop':
            df = df.dropna()
        
        # Forward fill any remaining NaN at the start
        df = df.ffill().bfill()
        
        # Winsorize extreme values
        if winsorize_percentile > 0:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                lower = df[col].quantile(winsorize_percentile)
                upper = df[col].quantile(1 - winsorize_percentile)
                df[col] = df[col].clip(lower=lower, upper=upper)
        
        return df
    
    @staticmethod
    def standardize_output(
        df: pd.DataFrame,
        indicator_name: str,
        date_col: str = 'date',
        value_col: str = 'value',
    ) -> pd.DataFrame:
        """
        Standardize output to match expected schema.
        
        Args:
            df: Input DataFrame (may have various column names)
            indicator_name: Name to assign to indicator column
            date_col: Name of date column in input
            value_col: Name of value column in input
            
        Returns:
            Standardized DataFrame with columns: date, value, indicator
        """
        result = pd.DataFrame({
            'date': pd.to_datetime(df[date_col]),
            'value': df[value_col].astype(float),
            'indicator': indicator_name,
        })
        return result.dropna(subset=['value'])
