"""
CSV file loader for user-uploaded data.
사용자 CSV 파일 로더

사용자가 자신의 데이터를 업로드할 수 있도록 표준 스키마로 매핑
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd
import io

from .base import DataLoader, DataSchema


class CSVLoader(DataLoader):
    """
    CSV file loader with automatic schema mapping.
    
    Supports various CSV formats and maps them to the standard schema.
    """
    
    # Common date column names
    DATE_COLUMNS = ['date', 'Date', 'DATE', 'datetime', 'Datetime', 'timestamp', 'time', 'Time']
    
    # Common value column names
    VALUE_COLUMNS = ['value', 'Value', 'VALUE', 'close', 'Close', 'CLOSE', 'price', 'Price', 'level', 'Level']
    
    def __init__(self, schema: Optional[DataSchema] = None):
        """Initialize CSV loader."""
        super().__init__(schema)
    
    def load(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load data from a CSV file path.
        
        Args:
            ticker: Path to CSV file
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            DataFrame with columns: date, value, indicator
        """
        return self.load_from_path(ticker, start_date, end_date)
    
    def load_from_path(
        self,
        file_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        indicator_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Load data from a CSV file path.
        
        Args:
            file_path: Path to CSV file
            start_date: Start date filter
            end_date: End date filter
            indicator_name: Name for the indicator (default: derived from filename)
            
        Returns:
            DataFrame with columns: date, value, indicator
        """
        df = pd.read_csv(file_path)
        
        if indicator_name is None:
            # Derive from filename
            indicator_name = file_path.split('/')[-1].split('\\')[-1].replace('.csv', '')
        
        return self._process_dataframe(df, indicator_name, start_date, end_date)
    
    def load_from_upload(
        self,
        uploaded_file: Any,
        indicator_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load data from a Streamlit uploaded file.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            indicator_name: Name for the indicator
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            DataFrame with columns: date, value, indicator
        """
        # Read file content
        content = uploaded_file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        return self._process_dataframe(df, indicator_name, start_date, end_date)
    
    def load_from_dataframe(
        self,
        df: pd.DataFrame,
        indicator_name: str,
        date_col: Optional[str] = None,
        value_col: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Convert an arbitrary DataFrame to standard schema.
        
        Args:
            df: Input DataFrame
            indicator_name: Name for the indicator
            date_col: Column name for dates (auto-detect if None)
            value_col: Column name for values (auto-detect if None)
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            DataFrame with columns: date, value, indicator
        """
        df = df.copy()
        
        # Auto-detect columns if not specified
        if date_col is None:
            date_col = self._detect_date_column(df)
        if value_col is None:
            value_col = self._detect_value_column(df)
        
        return self._process_dataframe(
            df, indicator_name, start_date, end_date,
            date_col=date_col, value_col=value_col
        )
    
    def _detect_date_column(self, df: pd.DataFrame) -> str:
        """Auto-detect date column."""
        for col in self.DATE_COLUMNS:
            if col in df.columns:
                return col
        
        # Try to find a datetime column
        for col in df.columns:
            try:
                pd.to_datetime(df[col].head(10))
                return col
            except Exception:
                continue
        
        # Use index if it looks like dates
        if df.index.name or hasattr(df.index, 'to_datetime'):
            return '__index__'
        
        raise ValueError("Could not detect date column. Please specify date_col parameter.")
    
    def _detect_value_column(self, df: pd.DataFrame) -> str:
        """Auto-detect value column."""
        for col in self.VALUE_COLUMNS:
            if col in df.columns:
                return col
        
        # Find first numeric column that's not the date
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            return numeric_cols[0]
        
        raise ValueError("Could not detect value column. Please specify value_col parameter.")
    
    def _process_dataframe(
        self,
        df: pd.DataFrame,
        indicator_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_col: Optional[str] = None,
        value_col: Optional[str] = None,
    ) -> pd.DataFrame:
        """Process and standardize a DataFrame."""
        df = df.copy()
        
        # Auto-detect columns
        if date_col is None:
            date_col = self._detect_date_column(df)
        if value_col is None:
            value_col = self._detect_value_column(df)
        
        # Handle index as date column
        if date_col == '__index__':
            df = df.reset_index()
            date_col = df.columns[0]
        
        # Standardize
        result = self.standardize_output(df, indicator_name, date_col, value_col)
        
        # Filter by date range
        if start_date:
            result = result[result['date'] >= pd.Timestamp(start_date)]
        if end_date:
            result = result[result['date'] <= pd.Timestamp(end_date)]
        
        # Handle missing values
        result = self.handle_missing_values(result, method='ffill')
        
        return result.reset_index(drop=True)
    
    def validate_upload(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate uploaded CSV and return diagnostics.
        
        Returns:
            Dict with validation results and detected columns
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'detected_date_col': None,
            'detected_value_col': None,
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': df.columns.tolist(),
        }
        
        try:
            result['detected_date_col'] = self._detect_date_column(df)
        except ValueError as e:
            result['valid'] = False
            result['errors'].append(str(e))
        
        try:
            result['detected_value_col'] = self._detect_value_column(df)
        except ValueError as e:
            result['valid'] = False
            result['errors'].append(str(e))
        
        # Check for missing values
        missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100
        if missing_pct > 10:
            result['warnings'].append(f"High missing value rate: {missing_pct:.1f}%")
        
        return result
