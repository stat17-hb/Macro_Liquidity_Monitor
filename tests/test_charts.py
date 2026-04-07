"""Tests for chart timeframe helpers."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.charts import filter_dataframe_by_timeframe, filter_series_by_timeframe


def test_filter_series_by_explicit_timeframe_keeps_recent_window():
    dates = pd.date_range('2020-01-01', periods=1200, freq='D')
    series = pd.Series(range(len(dates)), index=dates)

    filtered = filter_series_by_timeframe(series, timeframe='1Y')

    assert filtered.index.max() == series.index.max()
    assert filtered.index.min() >= series.index.max() - pd.DateOffset(years=1)
    assert len(filtered) < len(series)


def test_filter_dataframe_by_explicit_timeframe_keeps_recent_window():
    dates = pd.date_range('2020-01-01', periods=1200, freq='D')
    df = pd.DataFrame({'date': dates, 'value': range(len(dates))})

    filtered = filter_dataframe_by_timeframe(df, date_col='date', timeframe='6M')

    assert filtered['date'].max() == df['date'].max()
    assert filtered['date'].min() >= df['date'].max() - pd.DateOffset(months=6)
    assert len(filtered) < len(df)
