"""Unit tests for transforms module."""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.transforms import (
    calc_yoy, calc_3m_annualized, calc_1m_change,
    calc_zscore, calc_zscore_change, calc_acceleration,
    detect_inflection, calc_percentile,
)

@pytest.fixture
def sample_series():
    dates = pd.date_range('2020-01-01', periods=300, freq='W')
    values = 100 + np.cumsum(np.random.randn(300))
    return pd.Series(values, index=dates)

def test_calc_yoy(sample_series):
    result = calc_yoy(sample_series, periods=52)
    assert len(result) == len(sample_series)
    assert result.iloc[:52].isna().all()
    assert not result.iloc[52:].isna().all()

def test_calc_3m_annualized(sample_series):
    result = calc_3m_annualized(sample_series, periods_3m=13)
    assert len(result) == len(sample_series)
    assert result.iloc[:13].isna().all()

def test_calc_zscore(sample_series):
    result = calc_zscore(sample_series, window_years=1, periods_per_year=52)
    assert len(result) == len(sample_series)
    valid = result.dropna()
    assert valid.mean() < 0.5  # Should be approximately 0
    assert 0.5 < valid.std() < 1.5  # Should be approximately 1

def test_calc_percentile(sample_series):
    result = calc_percentile(sample_series, window_years=1, periods_per_year=52)
    valid = result.dropna()
    assert valid.min() >= 0
    assert valid.max() <= 100

def test_detect_inflection(sample_series):
    result = detect_inflection(sample_series, lookback=10)
    assert set(result.unique()).issubset({-1, 0, 1})

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
