# Loaders package for data loading abstraction
from .base import DataLoader, DataSchema
from .fred_loader import FREDLoader
from .yfinance_loader import YFinanceLoader
from .csv_loader import CSVLoader
from .sample_data import SampleDataLoader, generate_sample_data

__all__ = [
    'DataLoader',
    'DataSchema', 
    'FREDLoader',
    'YFinanceLoader',
    'CSVLoader',
    'SampleDataLoader',
    'generate_sample_data',
]
