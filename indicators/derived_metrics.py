"""
Derived metrics calculations for Fed balance sheet and liquidity analysis.
연준 대차대조표 및 유동성 분석을 위한 파생 지표 계산

Implements calculations defined in config.py DERIVED_METRICS:
1. QT pace (monthly % change in Fed assets)
2. Reserve regime classification (Abundant/Ample/Scarce)
3. Balance sheet identity verification
4. Money market stress detection
5. Fed lending stress measurement
6. TGA reserve drag calculation
7. Reserve demand proxy (crisis indicator)

All functions follow pandas convention with proper error handling and NaN propagation.
"""
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np


def calculate_qt_pace(
    fed_assets: pd.Series,
    periods_1m: int = 21,
) -> pd.Series:
    """
    Calculate monthly QT (Quantitative Tightening) pace.
    월간 양적긴축 진행도 계산

    Measures the month-over-month change in Fed's total assets (WALCL).
    Used to track intensity of QT vs QE periods.

    Args:
        fed_assets: Fed total assets (WALCL) in billions USD
        periods_1m: Trading days in 1 month (default: 21)

    Returns:
        Monthly percentage change in Fed assets
        - Negative values indicate QT (contraction)
        - Positive values indicate QE (expansion)

    Example:
        >>> qt_pace = calculate_qt_pace(fed_assets)
        >>> qt_pace.iloc[-1]  # Latest month's pace
    """
    if fed_assets is None or len(fed_assets) < 2:
        return pd.Series(dtype=float)

    # Percentage change over 1 month
    return fed_assets.pct_change(periods=periods_1m) * 100


def classify_reserve_regime(
    reserves: pd.Series,
    reverse_repo: Optional[pd.Series] = None,
    abundant_threshold: float = 2500.0,
    ample_threshold: float = 1500.0,
    tight_threshold: float = 500.0,
) -> pd.Series:
    """
    Classify reserve regime: Abundant, Ample, Tight, or Scarce.
    준비금 체계 분류: 충분함(Abundant) / 적절(Ample) / 긴축(Tight) / 부족(Scarce)

    Reserve thresholds are calibrated to post-2020 levels where:
    - Abundant (>2500B): Excess reserves, rate floor risk
    - Ample (1500-2500B): Normal operating range for Fed
    - Tight (500-1500B): Pre-crisis normal range
    - Scarce (<500B): Severe tightness, potential stress

    Args:
        reserves: Reserve Balances with Fed (WRESBAL) in billions USD
        reverse_repo: Optional RRP series to adjust for actual liquidity
        abundant_threshold: Level for "Abundant" classification
        ample_threshold: Level for "Ample" classification
        tight_threshold: Level for "Tight" classification

    Returns:
        Series with string classifications: 'Abundant', 'Ample', 'Tight', 'Scarce'

    Example:
        >>> regime = classify_reserve_regime(reserves)
        >>> regime.value_counts()
    """
    if reserves is None or len(reserves) == 0:
        return pd.Series(dtype=object)

    # Compute effective liquidity available to banks
    effective_reserves = reserves.copy()
    if reverse_repo is not None and len(reverse_repo) == len(reserves):
        # RRP represents alternative to reserves; adjust for availability
        effective_reserves = reserves - reverse_repo * 0.1  # Dampened impact

    regime = pd.Series('Scarce', index=reserves.index, dtype=object)
    regime[effective_reserves >= abundant_threshold] = 'Abundant'
    regime[(effective_reserves >= ample_threshold) & (effective_reserves < abundant_threshold)] = 'Ample'
    regime[(effective_reserves >= tight_threshold) & (effective_reserves < ample_threshold)] = 'Tight'
    regime[effective_reserves < tight_threshold] = 'Scarce'

    return regime


def verify_balance_sheet_identity(
    reserves: pd.Series,
    soma_assets: pd.Series,
    fed_lending: pd.Series,
    reverse_repo: pd.Series,
    tga: pd.Series,
    tolerance: float = 50.0,
) -> Dict[str, pd.Series]:
    """
    Verify Fed balance sheet identity: ΔReserves = ΔSOMA + ΔLending - ΔRRP - ΔTGA
    연준 대차대조표 항등식 검증

    The Federal Reserve's balance sheet must balance according to:
    Change in Reserves = Change in SOMA Assets + Change in Lending
                         - Change in Reverse Repo - Change in TGA

    Args:
        reserves: Reserve Balances with Fed (WRESBAL) in billions USD
        soma_assets: Fed SOMA Assets (WALCL proxy) in billions USD
        fed_lending: Fed lending facilities (WLCFLPCL) in billions USD
        reverse_repo: Overnight reverse repo (RRPONTSYD) in billions USD
        tga: Treasury General Account balance (WTREGEN) in billions USD
        tolerance: Acceptable deviation in billions USD (default: 50)

    Returns:
        Dictionary with:
        - 'identity_lhs': Observed change in reserves (LHS)
        - 'identity_rhs': Calculated RHS (SOMA + Lending - RRP - TGA changes)
        - 'residual': Difference (LHS - RHS), should be near zero
        - 'is_balanced': Boolean series indicating balanced periods
        - 'imbalance_magnitude': Absolute residual

    Example:
        >>> result = verify_balance_sheet_identity(reserves, soma, lending, rrp, tga)
        >>> result['is_balanced'].sum() / len(result['is_balanced'])  # % balanced
    """
    if any(s is None or len(s) == 0 for s in [reserves, soma_assets, fed_lending, reverse_repo, tga]):
        return {
            'identity_lhs': pd.Series(dtype=float),
            'identity_rhs': pd.Series(dtype=float),
            'residual': pd.Series(dtype=float),
            'is_balanced': pd.Series(dtype=bool),
            'imbalance_magnitude': pd.Series(dtype=float),
        }

    # Calculate changes (first differences)
    dr_reserves = reserves.diff()  # LHS: change in reserves

    # RHS: change in SOMA + change in Lending - change in RRP - change in TGA
    d_soma = soma_assets.diff()
    d_lending = fed_lending.diff()
    d_rrp = reverse_repo.diff()
    d_tga = tga.diff()

    # Identity: LHS = RHS
    rhs = d_soma + d_lending - d_rrp - d_tga

    # Residual shows imbalance
    residual = dr_reserves - rhs
    imbalance = residual.abs()

    is_balanced = imbalance <= tolerance

    return {
        'identity_lhs': dr_reserves,
        'identity_rhs': rhs,
        'residual': residual,
        'is_balanced': is_balanced,
        'imbalance_magnitude': imbalance,
    }


def detect_money_market_stress(
    reverse_repo: pd.Series,
    reserves: Optional[pd.Series] = None,
    normal_threshold: Tuple[float, float] = (0, 500),
    elevated_threshold: Tuple[float, float] = (500, 1500),
    stress_threshold: Tuple[float, float] = (1500, 2200),
) -> Dict[str, pd.Series]:
    """
    Detect money market stress via reverse repo demand.
    역레포 수요를 통한 단기자금시장 스트레스 탐지

    High RRP levels indicate:
    - Money market participants (MMFs, banks) need safe assets
    - Fed is absorbing excess liquidity at its facility
    - Potential underlying funding stress being masked

    Args:
        reverse_repo: Overnight RRP (RRPONTSYD) in billions USD
        reserves: Optional reserve balances for contextualization
        normal_threshold: Normal RRP range (billions)
        elevated_threshold: Elevated stress range
        stress_threshold: Acute stress range (2023 crisis ~1500-2200B)

    Returns:
        Dictionary with:
        - 'rrp_level': Raw RRP series
        - 'stress_regime': Categorical classification ('Normal', 'Elevated', 'Stress')
        - 'stress_score': Normalized 0-100 score within current regime
        - 'rrp_change_1m': 1-month change in RRP
        - 'rrp_acceleration': 2nd derivative (rate of change acceleration)

    Example:
        >>> stress = detect_money_market_stress(rrp, reserves)
        >>> stress['stress_regime'].value_counts()
    """
    if reverse_repo is None or len(reverse_repo) == 0:
        return {
            'rrp_level': pd.Series(dtype=float),
            'stress_regime': pd.Series(dtype=object),
            'stress_score': pd.Series(dtype=float),
            'rrp_change_1m': pd.Series(dtype=float),
            'rrp_acceleration': pd.Series(dtype=float),
        }

    # Initialize classification
    stress_regime = pd.Series('Normal', index=reverse_repo.index, dtype=object)

    # Assign regimes based on RRP level
    stress_regime[reverse_repo >= stress_threshold[0]] = 'Stress'
    stress_regime[(reverse_repo >= elevated_threshold[0]) & (reverse_repo < stress_threshold[0])] = 'Elevated'
    stress_regime[(reverse_repo >= normal_threshold[0]) & (reverse_repo < elevated_threshold[0])] = 'Normal'

    # Stress score: normalized within current regime (0-100)
    stress_score = pd.Series(np.nan, index=reverse_repo.index)

    # Score for Normal regime
    norm_mask = stress_regime == 'Normal'
    if norm_mask.any():
        normal_range = normal_threshold[1] - normal_threshold[0]
        stress_score[norm_mask] = ((reverse_repo[norm_mask] - normal_threshold[0]) / normal_range * 100).clip(0, 100)

    # Score for Elevated regime
    elev_mask = stress_regime == 'Elevated'
    if elev_mask.any():
        elev_range = elevated_threshold[1] - elevated_threshold[0]
        stress_score[elev_mask] = ((reverse_repo[elev_mask] - elevated_threshold[0]) / elev_range * 100).clip(0, 100)

    # Score for Stress regime
    stress_mask = stress_regime == 'Stress'
    if stress_mask.any():
        stress_range = stress_threshold[1] - stress_threshold[0]
        stress_score[stress_mask] = ((reverse_repo[stress_mask] - stress_threshold[0]) / stress_range * 100).clip(0, 100)

    # 1-month change
    rrp_change_1m = reverse_repo.pct_change(periods=21) * 100

    # Acceleration: 2nd derivative
    velocity = reverse_repo.diff(21)
    rrp_acceleration = velocity.diff(21)

    return {
        'rrp_level': reverse_repo,
        'stress_regime': stress_regime,
        'stress_score': stress_score,
        'rrp_change_1m': rrp_change_1m,
        'rrp_acceleration': rrp_acceleration,
    }


def calculate_fed_lending_stress(
    fed_lending: pd.Series,
    normal_threshold: Tuple[float, float] = (0, 100),
    elevated_threshold: Tuple[float, float] = (100, 300),
    stress_threshold: Tuple[float, float] = (300, 1000),
) -> Dict[str, pd.Series]:
    """
    Calculate Fed lending stress index from total lending facilities.
    연준 신용창출 스트레스 지수 계산

    Fed lending facilities usage indicates:
    - Bank stress when facilities are heavily used
    - Credit system dysfunction (e.g., 2008 GFC, 2020 COVID)
    - Discredit window becomes stigmatized during acute stress

    Args:
        fed_lending: Fed lending facilities total (WLCFLPCL) in billions USD
        normal_threshold: Normal usage range
        elevated_threshold: Elevated stress range
        stress_threshold: Acute stress range (GFC peak ~900B, COVID ~600B)

    Returns:
        Dictionary with:
        - 'lending_level': Raw lending series
        - 'stress_regime': Classification ('Normal', 'Elevated', 'Stress')
        - 'stress_score': 0-100 normalized score
        - 'lending_yoy': Year-over-year change
        - 'lending_percentile_3y': Rolling percentile (0-100)

    Example:
        >>> lending_stress = calculate_fed_lending_stress(fed_lending)
        >>> lending_stress['stress_score'].tail()
    """
    if fed_lending is None or len(fed_lending) == 0:
        return {
            'lending_level': pd.Series(dtype=float),
            'stress_regime': pd.Series(dtype=object),
            'stress_score': pd.Series(dtype=float),
            'lending_yoy': pd.Series(dtype=float),
            'lending_percentile_3y': pd.Series(dtype=float),
        }

    # Initialize classification
    stress_regime = pd.Series('Normal', index=fed_lending.index, dtype=object)

    # Assign regimes
    stress_regime[fed_lending >= stress_threshold[0]] = 'Stress'
    stress_regime[(fed_lending >= elevated_threshold[0]) & (fed_lending < stress_threshold[0])] = 'Elevated'
    stress_regime[(fed_lending >= normal_threshold[0]) & (fed_lending < elevated_threshold[0])] = 'Normal'

    # Stress score: normalized within regime
    stress_score = pd.Series(np.nan, index=fed_lending.index)

    # Normal regime scoring
    norm_mask = stress_regime == 'Normal'
    if norm_mask.any():
        normal_range = normal_threshold[1] - normal_threshold[0]
        if normal_range > 0:
            stress_score[norm_mask] = ((fed_lending[norm_mask] - normal_threshold[0]) / normal_range * 100).clip(0, 100)

    # Elevated regime scoring
    elev_mask = stress_regime == 'Elevated'
    if elev_mask.any():
        elev_range = elevated_threshold[1] - elevated_threshold[0]
        if elev_range > 0:
            stress_score[elev_mask] = ((fed_lending[elev_mask] - elevated_threshold[0]) / elev_range * 100).clip(0, 100)

    # Stress regime scoring
    stress_mask = stress_regime == 'Stress'
    if stress_mask.any():
        stress_range = stress_threshold[1] - stress_threshold[0]
        if stress_range > 0:
            stress_score[stress_mask] = ((fed_lending[stress_mask] - stress_threshold[0]) / stress_range * 100).clip(0, 100)

    # YoY change (252 trading days = 1 year)
    lending_yoy = fed_lending.pct_change(periods=252) * 100

    # Rolling percentile (3-year window)
    window_252 = 3 * 252
    percentile_rank = fed_lending.rolling(window=window_252, min_periods=window_252//2).apply(
        lambda x: (x.iloc[-1] >= x.dropna()).sum() / len(x.dropna()) * 100 if len(x.dropna()) > 0 else np.nan
    )

    return {
        'lending_level': fed_lending,
        'stress_regime': stress_regime,
        'stress_score': stress_score,
        'lending_yoy': lending_yoy,
        'lending_percentile_3y': percentile_rank,
    }


def calculate_tga_reserve_drag(
    tga: pd.Series,
    reserves: pd.Series,
    normal_range: Tuple[float, float] = (0.05, 0.15),
    elevated_range: Tuple[float, float] = (0.15, 0.25),
    stress_range: Tuple[float, float] = (0.25, 1.0),
) -> Dict[str, pd.Series]:
    """
    Calculate TGA reserve drag: impact of Treasury account on system liquidity.
    TGA 준비금 드래그: 재정부 계좌의 시스템 유동성 영향

    The Treasury General Account (TGA) acts as a "liquidity sink":
    - High TGA balance = fewer reserves circulating to banking system
    - When Treasury spends, TGA decreases → reserves increase (stimulus effect)
    - When Treasury collects taxes/borrows, TGA increases → reserves decrease

    Ratio = TGA / (TGA + Reserves) measures TGA's share of liquid assets:
    - <5%: Normal, insignificant drag
    - 5-15%: Moderate, typical operating range
    - 15-25%: Elevated, notable liquidity drain
    - >25%: Stress, severe impact on available reserves

    Args:
        tga: Treasury General Account balance (WTREGEN) in billions USD
        reserves: Reserve Balances with Fed (WRESBAL) in billions USD
        normal_range: Normal TGA/Total liquidity ratio
        elevated_range: Elevated impact range
        stress_range: Stress impact range

    Returns:
        Dictionary with:
        - 'tga_ratio': TGA / (TGA + Reserves) ratio
        - 'drag_regime': Classification of drag intensity
        - 'drag_score': 0-100 normalized score
        - 'tga_level': Raw TGA level
        - 'effective_reserves': Adjusted reserves (TGA impact accounted)

    Example:
        >>> drag = calculate_tga_reserve_drag(tga, reserves)
        >>> drag['tga_ratio'].iloc[-1]  # Current TGA impact
    """
    if tga is None or reserves is None or len(tga) != len(reserves):
        return {
            'tga_ratio': pd.Series(dtype=float),
            'drag_regime': pd.Series(dtype=object),
            'drag_score': pd.Series(dtype=float),
            'tga_level': pd.Series(dtype=float),
            'effective_reserves': pd.Series(dtype=float),
        }

    # Total liquid assets available to system
    total_liquid = tga + reserves

    # Avoid division by zero
    total_liquid = total_liquid.replace(0, np.nan)

    # Ratio: TGA's share of total liquid assets
    tga_ratio = tga / total_liquid

    # Classify drag regime
    drag_regime = pd.Series('Normal', index=tga_ratio.index, dtype=object)
    drag_regime[tga_ratio >= stress_range[0]] = 'Stress'
    drag_regime[(tga_ratio >= elevated_range[0]) & (tga_ratio < stress_range[0])] = 'Elevated'
    drag_regime[(tga_ratio >= normal_range[0]) & (tga_ratio < elevated_range[0])] = 'Normal'
    drag_regime[tga_ratio < normal_range[0]] = 'Minimal'

    # Drag score: normalized within regime
    drag_score = pd.Series(np.nan, index=tga_ratio.index)

    # Minimal regime
    minimal_mask = drag_regime == 'Minimal'
    if minimal_mask.any():
        drag_score[minimal_mask] = (tga_ratio[minimal_mask] / normal_range[0] * 50).clip(0, 50)

    # Normal regime
    norm_mask = drag_regime == 'Normal'
    if norm_mask.any():
        normal_span = normal_range[1] - normal_range[0]
        drag_score[norm_mask] = (50 + (tga_ratio[norm_mask] - normal_range[0]) / normal_span * 25).clip(50, 75)

    # Elevated regime
    elev_mask = drag_regime == 'Elevated'
    if elev_mask.any():
        elev_span = elevated_range[1] - elevated_range[0]
        drag_score[elev_mask] = (75 + (tga_ratio[elev_mask] - elevated_range[0]) / elev_span * 15).clip(75, 90)

    # Stress regime
    stress_mask = drag_regime == 'Stress'
    if stress_mask.any():
        stress_span = stress_range[1] - stress_range[0]
        drag_score[stress_mask] = (90 + (tga_ratio[stress_mask] - stress_range[0]) / stress_span * 10).clip(90, 100)

    # Effective reserves: adjust for TGA impact
    # When TGA is high, effective reserves are reduced
    effective_reserves = reserves * (1 - tga_ratio)

    return {
        'tga_ratio': tga_ratio,
        'drag_regime': drag_regime,
        'drag_score': drag_score,
        'tga_level': tga,
        'effective_reserves': effective_reserves,
    }


def calculate_reserve_demand_proxy(
    reverse_repo: pd.Series,
    reserves: pd.Series,
    normal_range: Tuple[float, float] = (0.0, 0.3),
    elevated_range: Tuple[float, float] = (0.3, 0.5),
    stress_range: Tuple[float, float] = (0.5, 1.0),
) -> Dict[str, pd.Series]:
    """
    Calculate reserve demand proxy: RRP as % of total overnight liquidity.
    준비금 수요 대리변수: 역레포 비중

    When banks and money market funds prefer Fed's reverse repo facility
    over holding reserves directly, it signals:
    - Shortage of high-quality collateral
    - Preference for ultra-safe Fed facility vs bank reserves
    - Potential reserve scarcity or distribution problems

    Ratio = RRP / (RRP + Reserves) measures:
    - <30%: Normal reserve availability
    - 30-50%: Elevated demand for safe haven (RRP)
    - >50%: Crisis conditions, severe reserve stress

    This metric captures: "What % of overnight liquidity is demanded via
    Fed's RRP rather than held as bank reserves?"

    Args:
        reverse_repo: Overnight RRP (RRPONTSYD) in billions USD
        reserves: Reserve Balances with Fed (WRESBAL) in billions USD
        normal_range: Normal RRP/(RRP+Reserves) ratio
        elevated_range: Elevated stress range
        stress_range: Acute stress range (2023 crisis >50%)

    Returns:
        Dictionary with:
        - 'demand_proxy_ratio': RRP / (RRP + Reserves)
        - 'demand_regime': Classification ('Normal', 'Elevated', 'Stress')
        - 'demand_score': 0-100 normalized score
        - 'total_overnight_liquidity': RRP + Reserves (total available)
        - 'crisis_indicator': Boolean for crisis detection (ratio > 50%)

    Example:
        >>> demand = calculate_reserve_demand_proxy(rrp, reserves)
        >>> demand['demand_proxy_ratio'].iloc[-1]  # Current ratio
        >>> demand['crisis_indicator'].any()  # Any crisis periods?
    """
    if reverse_repo is None or reserves is None or len(reverse_repo) != len(reserves):
        return {
            'demand_proxy_ratio': pd.Series(dtype=float),
            'demand_regime': pd.Series(dtype=object),
            'demand_score': pd.Series(dtype=float),
            'total_overnight_liquidity': pd.Series(dtype=float),
            'crisis_indicator': pd.Series(dtype=bool),
        }

    # Total overnight liquidity available
    total_liquidity = reverse_repo + reserves

    # Avoid division by zero
    total_liquidity = total_liquidity.replace(0, np.nan)

    # Ratio: RRP's share of total overnight liquidity
    demand_ratio = reverse_repo / total_liquidity

    # Classify demand regime
    demand_regime = pd.Series('Normal', index=demand_ratio.index, dtype=object)
    demand_regime[demand_ratio >= stress_range[0]] = 'Stress'
    demand_regime[(demand_ratio >= elevated_range[0]) & (demand_ratio < stress_range[0])] = 'Elevated'
    demand_regime[(demand_ratio >= normal_range[0]) & (demand_ratio < elevated_range[0])] = 'Normal'

    # Demand score: normalized within regime
    demand_score = pd.Series(np.nan, index=demand_ratio.index)

    # Normal regime
    norm_mask = demand_regime == 'Normal'
    if norm_mask.any():
        normal_span = normal_range[1] - normal_range[0]
        if normal_span > 0:
            demand_score[norm_mask] = ((demand_ratio[norm_mask] - normal_range[0]) / normal_span * 50).clip(0, 50)

    # Elevated regime
    elev_mask = demand_regime == 'Elevated'
    if elev_mask.any():
        elev_span = elevated_range[1] - elevated_range[0]
        if elev_span > 0:
            demand_score[elev_mask] = (50 + (demand_ratio[elev_mask] - elevated_range[0]) / elev_span * 40).clip(50, 90)

    # Stress regime
    stress_mask = demand_regime == 'Stress'
    if stress_mask.any():
        stress_span = stress_range[1] - stress_range[0]
        if stress_span > 0:
            demand_score[stress_mask] = (90 + (demand_ratio[stress_mask] - stress_range[0]) / stress_span * 10).clip(90, 100)

    # Crisis indicator: when >50% of overnight liquidity is via RRP
    crisis_indicator = demand_ratio > 0.5

    return {
        'demand_proxy_ratio': demand_ratio,
        'demand_regime': demand_regime,
        'demand_score': demand_score,
        'total_overnight_liquidity': total_liquidity,
        'crisis_indicator': crisis_indicator,
    }
