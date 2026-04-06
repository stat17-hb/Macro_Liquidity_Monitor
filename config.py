"""
Configuration module for Liquidity Monitoring Dashboard.
유동성 모니터링 대시보드 설정 모듈

핵심 철학:
1) 유동성 = 대차대조표 확장/수축 (고정된 돈의 총량 X)
2) 가격 = 한계 투자자(marginal buyer)의 신념
3) 목표 = 취약 지점 탐지 (가격 설명 X)
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import os


def _get_fred_api_key() -> Optional[str]:
    """
    FRED API 키를 가져옵니다.
    우선순위: Streamlit Secrets > 환경 변수
    """
    # 1. Streamlit Secrets 확인 (Streamlit Cloud용)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'FRED_API_KEY' in st.secrets:
            return st.secrets['FRED_API_KEY']
    except Exception:
        pass
    
    # 2. 환경 변수 확인 (로컬 개발용)
    return os.environ.get('FRED_API_KEY')


class Regime(Enum):
    """Market regime classification."""
    EXPANSION = "Expansion"
    LATE_CYCLE = "Late-cycle"
    CONTRACTION = "Contraction"
    STRESS = "Stress"


class AlertLevel(Enum):
    """Alert severity levels."""
    GREEN = "Green"
    YELLOW = "Yellow"
    RED = "Red"


@dataclass
class IndicatorConfig:
    """Configuration for a single indicator."""
    name: str
    description: str
    source: str  # 'fred', 'yfinance', 'csv'
    ticker: str
    category: str  # 'balance_sheet', 'collateral', 'belief', 'leverage', 'spread'
    invert: bool = False  # True if lower value = more risk
    
    
@dataclass
class ThresholdConfig:
    """Threshold configuration for alerts."""
    zscore_high: float = 2.0
    zscore_low: float = -2.0
    percentile_high: float = 90.0
    percentile_low: float = 10.0
    vix_stress: float = 30.0
    spread_stress_percentile: float = 75.0
    equity_drawdown_threshold: float = -5.0  # 1M return threshold


@dataclass
class AppConfig:
    """Main application configuration."""
    # Data settings
    cache_ttl_hours: int = 6
    default_lookback_years: int = 5
    zscore_window_years: int = 3
    
    # FRED API key (Streamlit Secrets 또는 환경변수 FRED_API_KEY에서 로드)
    fred_api_key: Optional[str] = field(default_factory=_get_fred_api_key)
    
    # Regime scoring weights
    regime_weights: Dict[str, float] = field(default_factory=lambda: {
        'credit_growth': 0.25,
        'spread': 0.25,
        'volatility': 0.20,
        'valuation_vs_earnings': 0.15,
        'real_yield': 0.15,
    })
    
    # Thresholds
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)


# ============================================================================
# INDICATOR DEFINITIONS - Minimum Set (최소 세트)
# ============================================================================

MINIMUM_INDICATORS: Dict[str, IndicatorConfig] = {
    # Balance Sheet Expansion
    'fed_assets': IndicatorConfig(
        name='Fed Total Assets',
        description='중앙은행 대차대조표 프록시 - 시스템 유동성의 근원',
        source='fred',
        ticker='WALCL',
        category='balance_sheet'
    ),
    'reserve_balances': IndicatorConfig(
        name='Reserve Balances with Fed',
        description='연방준비제도 예비금 - 은행 시스템 유동성',
        source='fred',
        ticker='WRESBAL',
        category='balance_sheet'
    ),
    'reverse_repo': IndicatorConfig(
        name='Overnight Reverse Repo (Treasury)',
        description='야간 역레포 - 단기 유동성 공급/흡수',
        source='fred',
        ticker='RRPONTSYD',
        category='balance_sheet'
    ),
    'tga_balance': IndicatorConfig(
        name='Treasury General Account',
        description='재무부 일반계좌 잔액 - 재정정책 수정자',
        source='fred',
        ticker='WTREGEN',
        category='balance_sheet',
        invert=True  # Higher TGA = less reserves in system
    ),
    'fed_lending': IndicatorConfig(
        name='Fed Lending (Combined)',
        description='연준 대출 - 신용창출 압박 지표',
        source='fred',
        ticker='WLCFLPCL',
        category='balance_sheet'
    ),
    'bank_credit': IndicatorConfig(
        name='Commercial Bank Credit',
        description='상업은행 신용 - 민간 신용창출 규모',
        source='fred',
        ticker='TOTBKCR',
        category='balance_sheet'
    ),
    'm2': IndicatorConfig(
        name='M2 Money Supply',
        description='광의통화 - 시스템 내 유통되는 화폐량',
        source='fred',
        ticker='M2SL',
        category='balance_sheet'
    ),
    
    # Credit Spreads
    'hy_spread': IndicatorConfig(
        name='High Yield Spread',
        description='하이일드 스프레드 - 신용위험 프리미엄',
        source='fred',
        ticker='BAMLH0A0HYM2',
        category='spread',
        invert=True
    ),
    'ig_spread': IndicatorConfig(
        name='Investment Grade Spread',
        description='투자등급 스프레드 - 기업 신용 비용',
        source='fred',
        ticker='BAMLC0A0CM',
        category='spread',
        invert=True
    ),
    
    # Volatility
    'vix': IndicatorConfig(
        name='VIX',
        description='주식시장 내재변동성 - 공포 지수',
        source='yfinance',
        ticker='^VIX',
        category='collateral',
        invert=True
    ),
    
    # Real Yield
    'real_yield_10y': IndicatorConfig(
        name='10Y Real Yield',
        description='실질금리 - 위험자산 할인율',
        source='fred',
        ticker='DFII10',
        category='belief',
        invert=True
    ),
    
    # Equity Index
    'sp500': IndicatorConfig(
        name='S&P 500',
        description='미국 대형주 지수 - 위험자산 대표',
        source='yfinance',
        ticker='^GSPC',
        category='collateral'
    ),
    
    # Breakeven Inflation
    'breakeven_10y': IndicatorConfig(
        name='10Y Breakeven Inflation',
        description='기대인플레이션 - 시장의 인플레 전망',
        source='fred',
        ticker='T10YIE',
        category='belief'
    ),
}


# ============================================================================
# INDICATOR DEFINITIONS - Extended Set (확장 세트)
# ============================================================================

EXTENDED_INDICATORS: Dict[str, IndicatorConfig] = {
    # MOVE Index (bond volatility)
    'move': IndicatorConfig(
        name='MOVE Index',
        description='채권시장 변동성 - 금리 불확실성',
        source='yfinance',
        ticker='^MOVE',
        category='collateral',
        invert=True
    ),

    # Financial Conditions
    'fci': IndicatorConfig(
        name='Financial Conditions Index',
        description='금융여건지수 - 종합 유동성 여건',
        source='fred',
        ticker='NFCI',
        category='balance_sheet',
        invert=True
    ),

    # Consumer Credit
    'consumer_credit': IndicatorConfig(
        name='Consumer Credit',
        description='소비자신용 - 가계 레버리지',
        source='fred',
        ticker='TOTALSL',
        category='leverage'
    ),

    # Repo Rate
    'repo_rate': IndicatorConfig(
        name='Repo Rate',
        description='레포금리 - 단기자금 조달비용',
        source='fred',
        ticker='SOFR',
        category='balance_sheet'
    ),
}


# ============================================================================
# FED BALANCE SHEET IDENTITY TRACKING
# ============================================================================
# Identity: Δ Reserves = Δ SOMA Assets + Δ Lending - Δ Reverse Repo - Δ TGA
#
# SOMA = System Open Market Account (Fed's securities holdings)
# Reverse Repo (RRPONTSYD) = Cash provided via RRPs (reduces reserves)
# TGA = Treasury General Account (safe asset that absorbs reserves)
#
# This framework tracks:
# 1. QT pace (monthly change in assets)
# 2. Reserve regime (abundant vs ample)
# 3. Money market stress (implied via reverse repo demand)
# ============================================================================

FED_BALANCE_SHEET_INDICATORS: Dict[str, IndicatorConfig] = {
    # Core identity components (duplicated from MINIMUM for reference)
    'fed_soma_assets': IndicatorConfig(
        name='Fed SOMA Assets (Total Assets proxy)',
        description='연준 증권 보유 - QT/QE 추적',
        source='fred',
        ticker='WALCL',
        category='balance_sheet'
    ),
    'fed_reserves': IndicatorConfig(
        name='Fed Reserve Balances',
        description='은행 준비금 - 중추 유동성 지표',
        source='fred',
        ticker='WRESBAL',
        category='balance_sheet'
    ),
    'reverse_repo_rrp': IndicatorConfig(
        name='Reverse Repo Agreements',
        description='역레포 - 유동성 흡수 메커니즘',
        source='fred',
        ticker='RRPONTSYD',
        category='balance_sheet'
    ),
    'treasury_general_acct': IndicatorConfig(
        name='Treasury General Account (TGA)',
        description='재무부 일반계좌 - 유동성 스폰지',
        source='fred',
        ticker='WTREGEN',
        category='balance_sheet',
        invert=True
    ),
    'fed_lending_total': IndicatorConfig(
        name='Fed Lending Facilities (Total)',
        description='연준 신용창출 - 스트레스 지표',
        source='fred',
        ticker='WLCFLPCL',
        category='balance_sheet'
    ),
    'fed_lending_net': IndicatorConfig(
        name='Fed Lending Net',
        description='연준 총 대출(순) - 은행 스트레스 종합 지표',
        source='fred',
        ticker='H41RESPPALDNNWW',
        category='balance_sheet',
        invert=True  # High lending = distress
    ),
}


# ============================================================================
# DERIVED METRICS DEFINITIONS
# ============================================================================
# Calculated from base indicators to track regime and risks
# ============================================================================

DERIVED_METRICS: Dict[str, Dict] = {
    'qt_pace_monthly': {
        'name': 'QT Pace (Monthly)',
        'description': '월간 연준 자산 변화율 - 양적긴축 진행도',
        'calculation': 'MoM change in WALCL',
        'alert_threshold': {
            'normal': (-50, 50),  # Billion USD
            'aggressive': (-100, 100),
            'stress': (-150, 150),
        },
        'category': 'balance_sheet'
    },
    'reserve_regime': {
        'name': 'Reserve Regime Classification',
        'description': '준비금 충분성 - Abundant vs Ample',
        'calculation': 'WRESBAL vs historical baseline',
        'thresholds': {
            'abundant': 2500,  # Billion USD (post-2020 level)
            'ample': 1500,
            'tight': 500,
        },
        'category': 'balance_sheet'
    },
    'reserve_balance_identity': {
        'name': 'Reserve Balance Identity Check',
        'description': '대차대조표 항등식: Δ Reserves = Δ SOMA + Δ Lending - Δ RRP - Δ TGA',
        'calculation': 'Verify balance sheet identity holds',
        'category': 'balance_sheet'
    },
    'money_market_stress': {
        'name': 'Money Market Stress (Implicit)',
        'description': '역레포 수요 → 단기자금 경색 신호',
        'calculation': 'RRPONTSYD level and change',
        'alert_threshold': {
            'normal': (0, 500),  # Billion USD
            'elevated': (500, 1500),
            'stress': (1500, 2200),  # 2023 crisis levels
        },
        'category': 'balance_sheet'
    },
    'fed_lending_stress': {
        'name': 'Fed Lending Stress Index',
        'description': '신용창출 압박 - 은행 시스템 안정성',
        'calculation': 'WLCFLPCL level and YoY change',
        'alert_threshold': {
            'normal': (0, 100),  # Billion USD
            'elevated': (100, 300),
            'stress': (300, 1000),  # GFC/COVID levels
        },
        'category': 'balance_sheet'
    },
    'tga_reserve_drag': {
        'name': 'TGA Reserve Drag',
        'description': 'TGA 잔액이 준비금에 미치는 영향 - 재정정책 수정자',
        'calculation': 'WTREGEN / (WRESBAL + WTREGEN)',
        'alert_threshold': {
            'normal': (0.05, 0.15),  # 5-15% of liquid assets
            'elevated': (0.15, 0.25),
            'stress': (0.25, 1.0),
        },
        'category': 'balance_sheet'
    },
    'reserve_demand_proxy': {
        'name': 'Reserve Demand Proxy',
        'description': '역레포 수요가 부족한 준비금 규모 반영',
        'calculation': 'RRPONTSYD / (WRESBAL + RRPONTSYD)',
        'alert_threshold': {
            'normal': (0.0, 0.3),   # <30% RRP/total overnight liquidity
            'elevated': (0.3, 0.5),
            'stress': (0.5, 1.0),   # >50% indicates liquidity crisis
        },
        'category': 'balance_sheet'
    },
}


# ============================================================================
# REGIME CLASSIFICATION RULES
# ============================================================================

REGIME_DESCRIPTIONS: Dict[Regime, str] = {
    Regime.EXPANSION: "신용/대차대조표 확장 중, 스프레드 축소, 변동성 안정 - 위험선호 환경",
    Regime.LATE_CYCLE: "신용 성장 지속이나 밸류에이션 확장이 이익개선을 앞서감 - 신념 과열 주의",
    Regime.CONTRACTION: "신용 성장 둔화/역전, 스프레드 확대, 변동성 상승 - 대차대조표 수축 시작",
    Regime.STRESS: "변동성 급등 + 스프레드 급확대 + 위험자산 급락 - 담보가치 훼손, 신용경색 위험",
}


# ============================================================================
# ALERT RULE DEFINITIONS
# ============================================================================

ALERT_RULES = {
    'belief_overheating': {
        'name': '신념 과열',
        'description': '밸류에이션 z-score 상승속도가 이익추정 z-score 상승속도를 초과',
        'check_indicators': ['valuation_zscore_change', 'earnings_zscore_change'],
        'threshold_diff': 0.5,
    },
    'collateral_stress': {
        'name': '담보 스트레스',
        'description': 'VIX 90p + 스프레드 75p + 지수 1M 수익률 < 임계치',
        'check_indicators': ['vix', 'hy_spread', 'sp500_1m_return'],
        'vix_percentile': 90,
        'spread_percentile': 75,
        'equity_return_threshold': -5.0,
    },
    'balance_sheet_contraction': {
        'name': '대차대조표 수축',
        'description': 'Bank Credit 3M 연율 < 0 + 스프레드 확대 동반',
        'check_indicators': ['bank_credit_3m_ann', 'hy_spread_change'],
        'credit_threshold': 0,
        'spread_widening': True,
    },
}


# ============================================================================
# UI CONFIGURATION
# ============================================================================

PAGE_CONFIG = {
    'page_title': '유동성 모니터링 대시보드',
    'page_icon': '📊',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded',
}

# Colors defined directly to avoid circular imports
# These values should match components/styles.py COLOR_PALETTE
REGIME_COLORS = {
    Regime.EXPANSION: '#22c55e',      # Green (success)
    Regime.LATE_CYCLE: '#f59e0b',     # Amber (warning)
    Regime.CONTRACTION: '#ef4444',    # Red (danger)
    Regime.STRESS: '#7f1d1d',         # Dark Red (danger_darker)
}

ALERT_COLORS = {
    AlertLevel.GREEN: '#22c55e',
    AlertLevel.YELLOW: '#f59e0b',
    AlertLevel.RED: '#ef4444',
}


# ============================================================================
# DEFAULT CONFIG INSTANCE
# ============================================================================

config = AppConfig()
