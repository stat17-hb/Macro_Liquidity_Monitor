"""
Data transformation functions for indicators.
지표 변환 함수들

각 지표에 대해 다음 변환을 제공:
- level: 원본 값
- YoY: 전년 대비 변화율
- 3M annualized: 3개월 연율화
- 1M change: 1개월 변화
- z-score: 표준화 점수 (3Y, 5Y 윈도우)
- change in z-score: Z-score 변화량
- acceleration: 2차 미분 (가속도)
- inflection: 변곡점 탐지
"""
from typing import Optional, Tuple, List
import pandas as pd
import numpy as np
from scipy import stats


def calc_yoy(
    series: pd.Series,
    periods: int = 252,  # Trading days in a year
) -> pd.Series:
    """
    Calculate Year-over-Year change.
    전년 대비 변화율
    
    Args:
        series: Input time series
        periods: Number of periods in a year (252 for daily, 52 for weekly, 12 for monthly)
        
    Returns:
        YoY change as percentage
    """
    return series.pct_change(periods=periods) * 100


def calc_3m_annualized(
    series: pd.Series,
    periods_3m: int = 63,  # Trading days in 3 months
) -> pd.Series:
    """
    Calculate 3-month change annualized.
    3개월 변화율 연율화
    
    Args:
        series: Input time series
        periods_3m: Number of periods in 3 months
        
    Returns:
        3M change annualized as percentage
    """
    change_3m = series.pct_change(periods=periods_3m)
    # Annualize: (1 + 3m_return)^4 - 1
    annualized = ((1 + change_3m) ** 4 - 1) * 100
    return annualized


def calc_1m_change(
    series: pd.Series,
    periods_1m: int = 21,  # Trading days in 1 month
) -> pd.Series:
    """
    Calculate 1-month change.
    1개월 변화
    
    Args:
        series: Input time series
        periods_1m: Number of periods in 1 month
        
    Returns:
        1M change as percentage
    """
    return series.pct_change(periods=periods_1m) * 100


def calc_zscore(
    series: pd.Series,
    window_years: int = 3,
    periods_per_year: int = 252,
    min_periods: Optional[int] = None,
) -> pd.Series:
    """
    Calculate rolling z-score.
    롤링 Z-score 계산
    
    Args:
        series: Input time series
        window_years: Window size in years
        periods_per_year: Number of periods per year
        min_periods: Minimum periods required (default: half of window)
        
    Returns:
        Z-score series
    """
    window = window_years * periods_per_year
    if min_periods is None:
        min_periods = window // 2
    
    rolling_mean = series.rolling(window=window, min_periods=min_periods).mean()
    rolling_std = series.rolling(window=window, min_periods=min_periods).std()
    
    # Avoid division by zero
    rolling_std = rolling_std.replace(0, np.nan)
    
    zscore = (series - rolling_mean) / rolling_std
    return zscore


def calc_zscore_change(
    series: pd.Series,
    window_years: int = 3,
    change_periods: int = 21,  # 1 month default
    periods_per_year: int = 252,
) -> pd.Series:
    """
    Calculate change in z-score.
    Z-score 변화량
    
    Args:
        series: Input time series
        window_years: Window for z-score calculation
        change_periods: Periods to calculate change over
        periods_per_year: Number of periods per year
        
    Returns:
        Change in z-score
    """
    zscore = calc_zscore(series, window_years, periods_per_year)
    return zscore.diff(change_periods)


def calc_acceleration(
    series: pd.Series,
    first_diff_periods: int = 21,
    second_diff_periods: int = 21,
) -> pd.Series:
    """
    Calculate acceleration (2nd derivative).
    가속도 (2차 미분)
    
    This measures if the rate of change is increasing or decreasing.
    
    Args:
        series: Input time series
        first_diff_periods: Periods for first derivative
        second_diff_periods: Periods for second derivative
        
    Returns:
        Acceleration series
    """
    # First derivative: rate of change
    velocity = series.diff(first_diff_periods)
    # Second derivative: acceleration
    acceleration = velocity.diff(second_diff_periods)
    return acceleration


def detect_inflection(
    series: pd.Series,
    lookback: int = 21,
    sensitivity: float = 0.0,
) -> pd.Series:
    """
    Detect inflection points (peaks and troughs).
    변곡점 탐지 (고점/저점)
    
    Returns a series with:
    - 1: Local peak (top)
    - -1: Local trough (bottom)
    - 0: Neither
    
    Args:
        series: Input time series
        lookback: Periods to look back for comparison
        sensitivity: Minimum % change required to qualify
        
    Returns:
        Series with inflection point indicators
    """
    result = pd.Series(0, index=series.index)
    
    # Rolling max and min
    rolling_max = series.rolling(window=lookback, center=True).max()
    rolling_min = series.rolling(window=lookback, center=True).min()
    
    # Mark peaks (where current equals rolling max)
    is_peak = (series == rolling_max) & (series.shift(1) < series) & (series.shift(-1) < series)
    
    # Mark troughs (where current equals rolling min)
    is_trough = (series == rolling_min) & (series.shift(1) > series) & (series.shift(-1) > series)
    
    if sensitivity > 0:
        # Filter by minimum magnitude
        pct_from_prev = series.pct_change(lookback).abs() * 100
        is_peak = is_peak & (pct_from_prev >= sensitivity)
        is_trough = is_trough & (pct_from_prev >= sensitivity)
    
    result[is_peak] = 1
    result[is_trough] = -1
    
    return result


def calc_percentile(
    series: pd.Series,
    window_years: int = 3,
    periods_per_year: int = 252,
    min_periods: Optional[int] = None,
) -> pd.Series:
    """
    Calculate rolling percentile rank.
    롤링 백분위수 계산
    
    Args:
        series: Input time series
        window_years: Window size in years
        periods_per_year: Number of periods per year
        min_periods: Minimum periods required
        
    Returns:
        Percentile rank (0-100)
    """
    window = window_years * periods_per_year
    if min_periods is None:
        min_periods = window // 2
    
    def percentile_rank(x):
        if len(x.dropna()) < min_periods:
            return np.nan
        return stats.percentileofscore(x.dropna(), x.iloc[-1])
    
    return series.rolling(window=window, min_periods=min_periods).apply(percentile_rank)


def calc_rolling_stats(
    series: pd.Series,
    window: int = 252,
    min_periods: Optional[int] = None,
) -> pd.DataFrame:
    """
    Calculate comprehensive rolling statistics.
    종합 롤링 통계
    
    Args:
        series: Input time series
        window: Rolling window size
        min_periods: Minimum periods required
        
    Returns:
        DataFrame with columns: mean, std, min, max, median, skew, kurt
    """
    if min_periods is None:
        min_periods = window // 2
    
    rolling = series.rolling(window=window, min_periods=min_periods)
    
    result = pd.DataFrame({
        'mean': rolling.mean(),
        'std': rolling.std(),
        'min': rolling.min(),
        'max': rolling.max(),
        'median': rolling.median(),
        'skew': rolling.skew(),
        'kurt': rolling.kurt(),
    }, index=series.index)
    
    return result


def get_latest_values(
    series: pd.Series,
    include_changes: bool = True,
) -> dict:
    """
    Get the latest values with various transformations.
    최신 값들과 각종 변환값 반환
    
    Args:
        series: Input time series
        include_changes: Whether to include change calculations
        
    Returns:
        Dict with latest values for each transformation
    """
    result = {
        'latest': series.iloc[-1] if len(series) > 0 else None,
        'date': series.index[-1] if len(series) > 0 else None,
    }
    
    if include_changes and len(series) > 252:
        result['yoy'] = calc_yoy(series).iloc[-1]
        result['3m_ann'] = calc_3m_annualized(series).iloc[-1]
        result['1m_change'] = calc_1m_change(series).iloc[-1]
        result['zscore_3y'] = calc_zscore(series, window_years=3).iloc[-1]
        result['zscore_5y'] = calc_zscore(series, window_years=5).iloc[-1]
        result['percentile_3y'] = calc_percentile(series, window_years=3).iloc[-1]
    
    return result


def standardize_frequency(
    df: pd.DataFrame,
    target_freq: str = 'W',
    value_col: str = 'value',
    date_col: str = 'date',
    agg_method: str = 'last',
) -> pd.DataFrame:
    """
    Standardize data frequency.
    데이터 주기 표준화
    
    Args:
        df: Input DataFrame
        target_freq: Target frequency ('D', 'W', 'M')
        value_col: Name of value column
        date_col: Name of date column
        agg_method: Aggregation method ('last', 'mean', 'first')
        
    Returns:
        Resampled DataFrame
    """
    df = df.copy()
    df = df.set_index(date_col)
    
    if agg_method == 'last':
        resampled = df[value_col].resample(target_freq).last()
    elif agg_method == 'mean':
        resampled = df[value_col].resample(target_freq).mean()
    elif agg_method == 'first':
        resampled = df[value_col].resample(target_freq).first()
    else:
        resampled = df[value_col].resample(target_freq).last()
    
    result = pd.DataFrame({
        date_col: resampled.index,
        value_col: resampled.values,
    })
    
    return result.dropna().reset_index(drop=True)
