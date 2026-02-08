"""
Alert system module.
알림 시스템 모듈

룰 기반 알림 규칙:
1. 신념 과열: 밸류에이션 z-score 상승속도 > 이익추정 z-score 상승속도
2. 담보 스트레스: VIX 90p + credit spread 75p + 지수 1M < -X%
3. 대차대조표 수축: bank credit 3M ann < 0 + 스프레드 확대 동반

알림 메시지 형식:
[레벨: Green/Yellow/Red] (무엇이) (어떻게 변했고) (취약한 경로는 무엇인지) (확인할 추가 지표 2개)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AlertLevel, ALERT_COLORS
from .transforms import (
    calc_zscore,
    calc_zscore_change,
    calc_3m_annualized,
    calc_1m_change,
    calc_percentile,
)


@dataclass
class Alert:
    """Single alert instance."""
    level: AlertLevel
    rule_name: str
    title: str
    what_changed: str
    vulnerability_path: str
    additional_checks: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def format_message(self) -> str:
        """Format alert as standard message."""
        checks = ', '.join(self.additional_checks[:2])
        return (
            f"[{self.level.value}] {self.title}: "
            f"{self.what_changed} → "
            f"취약 경로: {self.vulnerability_path}. "
            f"추가 확인: {checks}"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for display."""
        return {
            'level': self.level.value,
            'rule': self.rule_name,
            'title': self.title,
            'what_changed': self.what_changed,
            'vulnerability': self.vulnerability_path,
            'checks': self.additional_checks,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class AlertConfig:
    """Configuration for alert rules."""
    # Belief overheating
    belief_zscore_gap_yellow: float = 0.3
    belief_zscore_gap_red: float = 0.6
    
    # Collateral stress
    vix_percentile_yellow: float = 75
    vix_percentile_red: float = 90
    spread_percentile_yellow: float = 70
    spread_percentile_red: float = 85
    equity_drawdown_yellow: float = -3.0
    equity_drawdown_red: float = -7.0
    
    # Balance sheet contraction
    credit_3m_threshold: float = 0.0
    credit_deceleration_threshold: float = -2.0


class AlertEngine:
    """
    Alert generation engine.
    알림 생성 엔진
    
    모든 알림은 '취약 지점'에 대한 경고로 작성.
    원인 단정이 아닌 모니터링 관점.
    """
    
    def __init__(self, config: Optional[AlertConfig] = None):
        """Initialize alert engine."""
        self.config = config or AlertConfig()
        self.alert_history: List[Alert] = []
    
    def check_all_alerts(
        self,
        data: Dict[str, pd.Series],
        as_of_date: Optional[pd.Timestamp] = None,
    ) -> List[Alert]:
        """
        Check all alert rules and return triggered alerts.
        모든 알림 규칙 체크
        
        Args:
            data: Dict of indicator name -> time series
            as_of_date: Date to check (default: latest)
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        
        # Check each rule
        belief_alert = check_belief_overheating(data, self.config, as_of_date)
        if belief_alert:
            alerts.append(belief_alert)
            self.alert_history.append(belief_alert)
        
        collateral_alert = check_collateral_stress(data, self.config, as_of_date)
        if collateral_alert:
            alerts.append(collateral_alert)
            self.alert_history.append(collateral_alert)
        
        bs_alert = check_balance_sheet_contraction(data, self.config, as_of_date)
        if bs_alert:
            alerts.append(bs_alert)
            self.alert_history.append(bs_alert)
        
        return alerts
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary of active alerts by level."""
        return {
            'Green': sum(1 for a in self.alert_history[-10:] if a.level == AlertLevel.GREEN),
            'Yellow': sum(1 for a in self.alert_history[-10:] if a.level == AlertLevel.YELLOW),
            'Red': sum(1 for a in self.alert_history[-10:] if a.level == AlertLevel.RED),
        }
    
    def get_recent_alerts(self, n: int = 10) -> List[Alert]:
        """Get n most recent alerts."""
        return self.alert_history[-n:][::-1]  # Most recent first


def check_belief_overheating(
    data: Dict[str, pd.Series],
    config: Optional[AlertConfig] = None,
    as_of_date: Optional[pd.Timestamp] = None,
) -> Optional[Alert]:
    """
    Check for belief overheating signal.
    신념 과열 경고 체크
    
    밸류에이션 z-score 상승속도 > 이익추정 z-score 상승속도 + 임계치
    """
    config = config or AlertConfig()
    
    # Get valuation and earnings data
    valuation = data.get('valuation')
    if valuation is None:
        valuation = data.get('pe_ratio')
    earnings = data.get('earnings')
    if earnings is None:
        earnings = data.get('forward_eps')
    
    if valuation is None or earnings is None:
        return None
    
    if len(valuation) < 252 or len(earnings) < 252:
        return None
    
    # Calculate z-score changes (1M)
    val_zscore_change = calc_zscore_change(valuation, window_years=3, change_periods=21)
    earn_zscore_change = calc_zscore_change(earnings, window_years=3, change_periods=21)
    
    # Get latest values
    if as_of_date:
        val_zscore_change = val_zscore_change[val_zscore_change.index <= as_of_date]
        earn_zscore_change = earn_zscore_change[earn_zscore_change.index <= as_of_date]
    
    val_change = val_zscore_change.iloc[-1] if len(val_zscore_change) > 0 else None
    earn_change = earn_zscore_change.iloc[-1] if len(earn_zscore_change) > 0 else None
    
    if val_change is None or earn_change is None or np.isnan(val_change) or np.isnan(earn_change):
        return None
    
    gap = val_change - earn_change
    
    # Determine level
    if gap >= config.belief_zscore_gap_red:
        level = AlertLevel.RED
    elif gap >= config.belief_zscore_gap_yellow:
        level = AlertLevel.YELLOW
    else:
        return None  # No alert
    
    return Alert(
        level=level,
        rule_name='belief_overheating',
        title='신념 과열',
        what_changed=f"밸류에이션 z-score가 이익추정 대비 {gap:.2f}σ 빠르게 상승",
        vulnerability_path="밸류에이션 확장 → 실적 미스 시 급격한 되돌림 위험",
        additional_checks=['Forward EPS 수정 동향', '애널리스트 컨센서스 변화'],
    )


def check_collateral_stress(
    data: Dict[str, pd.Series],
    config: Optional[AlertConfig] = None,
    as_of_date: Optional[pd.Timestamp] = None,
) -> Optional[Alert]:
    """
    Check for collateral stress signal.
    담보 스트레스 경고 체크
    
    VIX 90p + credit spread 75p + 지수 1M < -X%
    """
    config = config or AlertConfig()
    
    vix = data.get('vix')
    spread = data.get('spread')
    if spread is None:
        spread = data.get('hy_spread')
    equity = data.get('equity')
    if equity is None:
        equity = data.get('sp500')
    
    if vix is None or spread is None or equity is None:
        return None
    
    # Calculate metrics
    vix_percentile = None
    spread_percentile = None
    equity_1m = None
    
    if len(vix) > 756:  # 3 years daily
        vix_pct_series = calc_percentile(vix, window_years=3, periods_per_year=252)
        if as_of_date:
            vix_pct_series = vix_pct_series[vix_pct_series.index <= as_of_date]
        vix_percentile = vix_pct_series.iloc[-1] if len(vix_pct_series) > 0 else None
    
    if len(spread) > 156:  # 3 years weekly
        spread_pct_series = calc_percentile(spread, window_years=3, periods_per_year=52)
        if as_of_date:
            spread_pct_series = spread_pct_series[spread_pct_series.index <= as_of_date]
        spread_percentile = spread_pct_series.iloc[-1] if len(spread_pct_series) > 0 else None
    
    if len(equity) > 21:
        equity_1m_series = calc_1m_change(equity)
        if as_of_date:
            equity_1m_series = equity_1m_series[equity_1m_series.index <= as_of_date]
        equity_1m = equity_1m_series.iloc[-1] if len(equity_1m_series) > 0 else None
    
    if vix_percentile is None or spread_percentile is None or equity_1m is None:
        return None
    
    if np.isnan(vix_percentile) or np.isnan(spread_percentile) or np.isnan(equity_1m):
        return None
    
    # Check all three conditions
    vix_stress = vix_percentile >= config.vix_percentile_red
    spread_stress = spread_percentile >= config.spread_percentile_red
    equity_stress = equity_1m <= config.equity_drawdown_red
    
    vix_warning = vix_percentile >= config.vix_percentile_yellow
    spread_warning = spread_percentile >= config.spread_percentile_yellow
    equity_warning = equity_1m <= config.equity_drawdown_yellow
    
    # Count stress signals
    red_signals = sum([vix_stress, spread_stress, equity_stress])
    yellow_signals = sum([vix_warning, spread_warning, equity_warning])
    
    if red_signals >= 2:
        level = AlertLevel.RED
    elif yellow_signals >= 2:
        level = AlertLevel.YELLOW
    else:
        return None  # No alert
    
    return Alert(
        level=level,
        rule_name='collateral_stress',
        title='담보 스트레스',
        what_changed=f"VIX {vix_percentile:.0f}%ile, 스프레드 {spread_percentile:.0f}%ile, 주가 1M {equity_1m:.1f}%",
        vulnerability_path="담보가치 하락 → 마진콜 → 강제 청산 → 추가 하락",
        additional_checks=['레버리지 ETF 자금흐름', '하이일드 발행 중단 여부'],
    )


def check_balance_sheet_contraction(
    data: Dict[str, pd.Series],
    config: Optional[AlertConfig] = None,
    as_of_date: Optional[pd.Timestamp] = None,
) -> Optional[Alert]:
    """
    Check for balance sheet contraction signal.
    대차대조표 수축 경고 체크
    
    Bank Credit 3M 연율 < 0 + 스프레드 확대 동반
    """
    config = config or AlertConfig()
    
    credit = data.get('credit')
    if credit is None:
        credit = data.get('bank_credit')
    spread = data.get('spread')
    if spread is None:
        spread = data.get('hy_spread')
    
    if credit is None:
        return None
    
    if len(credit) < 26:  # At least 6 months of weekly data
        return None
    
    # Calculate 3M annualized growth
    credit_3m = calc_3m_annualized(credit, periods_3m=13)  # Weekly data
    
    if as_of_date:
        credit_3m = credit_3m[credit_3m.index <= as_of_date]
    
    credit_growth = credit_3m.iloc[-1] if len(credit_3m) > 0 else None
    
    if credit_growth is None or np.isnan(credit_growth):
        return None
    
    # Check for spread widening if available
    spread_widening = False
    spread_change = None
    if spread is not None and len(spread) > 4:
        spread_1m = spread.diff(4)  # ~1 month change for weekly
        if as_of_date:
            spread_1m = spread_1m[spread_1m.index <= as_of_date]
        spread_change = spread_1m.iloc[-1] if len(spread_1m) > 0 else None
        if spread_change is not None and not np.isnan(spread_change):
            spread_widening = spread_change > 0
    
    # Determine level
    if credit_growth < config.credit_3m_threshold:
        if spread_widening:
            level = AlertLevel.RED
        else:
            level = AlertLevel.YELLOW
    elif credit_growth < config.credit_deceleration_threshold:
        level = AlertLevel.YELLOW
    else:
        return None  # No alert
    
    spread_msg = f", 스프레드 {spread_change:.2f}pp 확대" if spread_change and spread_change > 0 else ""
    
    return Alert(
        level=level,
        rule_name='balance_sheet_contraction',
        title='대차대조표 수축',
        what_changed=f"은행 신용 3M 연율 {credit_growth:.1f}%{spread_msg}",
        vulnerability_path="신용 축소 → 자산가격 하락 → 담보 훼손 → 추가 신용 축소",
        additional_checks=['M2 성장률', 'Fed 대차대조표 변화'],
    )


def format_alert_for_display(alert: Alert) -> dict:
    """Format alert for Streamlit display."""
    color = ALERT_COLORS.get(alert.level, '#666666')
    
    return {
        'color': color,
        'icon': '🔴' if alert.level == AlertLevel.RED else ('🟡' if alert.level == AlertLevel.YELLOW else '🟢'),
        'title': alert.title,
        'message': alert.format_message(),
        'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M'),
        'checks': alert.additional_checks,
    }
