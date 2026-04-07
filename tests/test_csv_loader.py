"""Tests for CSV loader UTF-8 handling and standardization."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loaders.base import DataLoader
from loaders.csv_loader import CSVLoader


class FakeUploadedFile:
    def __init__(self, content: bytes):
        self._content = content

    def getvalue(self):
        return self._content


def test_load_from_path_uses_utf8_encoding(monkeypatch, tmp_path):
    captured = {}

    def fake_read_csv(file_path, **kwargs):
        captured['file_path'] = file_path
        captured['encoding'] = kwargs.get('encoding')
        return pd.DataFrame({
            'date': ['2024-01-01'],
            'value': [1.0],
        })

    monkeypatch.setattr(pd, 'read_csv', fake_read_csv)

    loader = CSVLoader()
    result = loader.load_from_path(str(tmp_path / "테스트.csv"), indicator_name="테스트")

    assert captured['encoding'] == 'utf-8'
    assert result['indicator'].iloc[0] == "테스트"


def test_load_from_upload_standardizes_dataframe():
    loader = CSVLoader()
    uploaded_file = FakeUploadedFile(
        b"date,value\n2024-01-01,1.5\n2024-01-02,2.5\n"
    )

    result = loader.load_from_upload(uploaded_file, "Custom Metric")

    assert list(result.columns) == ['date', 'value', 'indicator']
    assert pd.api.types.is_datetime64_any_dtype(result['date'])
    assert result['indicator'].unique().tolist() == ['Custom Metric']
    assert result['value'].tolist() == [1.5, 2.5]


def test_loader_preserves_extreme_values_by_default():
    loader = CSVLoader()
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5, freq='D'),
        'value': [1.0, 2.0, 3.0, 4.0, 1000.0],
    })

    result = loader.load_from_dataframe(df, "Stress Tail")

    assert result['value'].max() == 1000.0


def test_handle_missing_values_still_supports_opt_in_winsorization():
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5, freq='D'),
        'value': [1.0, 2.0, 3.0, 4.0, 1000.0],
        'indicator': ['Stress Tail'] * 5,
    })

    cleaned = DataLoader.handle_missing_values(df, winsorize_percentile=0.2)

    assert cleaned['value'].max() < 1000.0
