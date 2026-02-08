"""
Regime classification module.
레짐 분류 모듈

4개 레짐을 점수로 분류:
- Expansion: 신용/대차대조표 성장(+), 스프레드 축소, 변동성 낮음
- Late-cycle: 신용 성장 지속, 밸류에이션 확장 > 이익/생산성 개선
- Contraction: 신용 성장 둔화/음전환, 스프레드 확대, 변동성 상승
- Stress: 변동성 급등 + 스프레드 급확대 + 위험자산 급락

각 레짐의 조건을 점수화(0~100)하고 가장 높은 레짐을 표시
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime, REGIME_DESCRIPTIONS
from .transforms import calc_zscore, calc_3m_annualized, calc_1m_change, calc_percentile


@dataclass
class RegimeScore:
    """Scores for each regime with explanations."""
    expansion: float
    late_cycle: float
    contraction: float
    stress: float
    
    def get_primary_regime(self) -> Regime:
        """Get the regime with highest score."""
        scores = {
            Regime.EXPANSION: self.expansion,
            Regime.LATE_CYCLE: self.late_cycle,
            Regime.CONTRACTION: self.contraction,
            Regime.STRESS: self.stress,
        }
        return max(scores, key=scores.get)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'Expansion': self.expansion,
            'Late-cycle': self.late_cycle,
            'Contraction': self.contraction,
            'Stress': self.stress,
        }


@dataclass
class RegimeResult:
    """Complete regime classification result."""
    primary_regime: Regime
    scores: RegimeScore
    explanations: List[str]
    confidence: float
    data_quality_warning: Optional[str] = None


class RegimeClassifier:
    """
    Regime classification engine.
    레짐 분류 엔진
    
    핵심 철학:
    - 유동성 = 대차대조표 확장/수축
    - 가격 = 한계 투자자의 신념
    - 목표 = 취약 지점 탐지
    """
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize classifier with optional config overrides."""
        self.config = config or {}
        
        # Default thresholds
        self.thresholds = {
            'credit_growth_expansion': 3.0,      # 3% YoY for expansion
            'credit_growth_contraction': 0.0,    # 0% for contraction
            'spread_zscore_tight': -0.5,         # Tight spreads
            'spread_zscore_wide': 1.0,           # Wide spreads
            'vix_percentile_low': 30,            # Low volatility
            'vix_percentile_high': 70,           # High volatility
            'vix_stress': 90,                    # Stress threshold
            'valuation_vs_earnings_gap': 0.5,    # Z-score gap for late-cycle
            'equity_drawdown': -5.0,             # 1M drawdown for stress
        }
        self.thresholds.update(self.config.get('thresholds', {}))
    
    def classify(
        self,
        data: Dict[str, pd.Series],
        as_of_date: Optional[pd.Timestamp] = None,
    ) -> RegimeResult:
        """
        Classify current market regime.
        현재 시장 레짐 분류
        
        Args:
            data: Dict of indicator name -> time series
                Required keys:
                - 'credit_growth' or 'bank_credit': Bank credit or similar
                - 'spread': Credit spread (HY or IG)
                - 'vix': Volatility index
                Optional keys:
                - 'equity': Equity index (for stress detection)
                - 'valuation_zscore': Valuation z-score
                - 'earnings_zscore': Earnings z-score
            as_of_date: Date to classify (default: latest)
            
        Returns:
            RegimeResult with classification and explanation
        """
        # Extract latest values
        metrics = self._extract_metrics(data, as_of_date)
        
        # Calculate scores for each regime
        scores = self._calculate_scores(metrics)
        
        # Generate explanations
        explanations = self._generate_explanations(metrics, scores)
        
        # Determine primary regime
        primary = scores.get_primary_regime()
        
        # Calculate confidence (gap between top 2 scores)
        sorted_scores = sorted(scores.to_dict().values(), reverse=True)
        confidence = (sorted_scores[0] - sorted_scores[1]) / 100 if len(sorted_scores) >= 2 else 1.0
        
        # Check data quality
        warning = self._check_data_quality(data)
        
        return RegimeResult(
            primary_regime=primary,
            scores=scores,
            explanations=explanations,
            confidence=confidence,
            data_quality_warning=warning,
        )
    
    def _extract_metrics(
        self,
        data: Dict[str, pd.Series],
        as_of_date: Optional[pd.Timestamp],
    ) -> Dict[str, float]:
        """Extract relevant metrics from data."""
        metrics = {}
        
        # Helper to get latest value
        def get_latest(series, name):
            if series is None or len(series) == 0:
                return None
            if as_of_date:
                series = series[series.index <= as_of_date]
            return series.iloc[-1] if len(series) > 0 else None
        
        # Credit growth (3M annualized)
        credit = data.get('credit_growth')
        if credit is None:
            credit = data.get('bank_credit')
        if credit is not None and len(credit) > 63:
            credit_3m = calc_3m_annualized(credit, periods_3m=13)  # Weekly data
            metrics['credit_growth_3m'] = get_latest(credit_3m, 'credit_growth_3m')
        
        # Spread z-score
        spread = data.get('spread')
        if spread is None:
            spread = data.get('hy_spread')
        if spread is not None and len(spread) > 156:  # 3 years weekly
            spread_zscore = calc_zscore(spread, window_years=3, periods_per_year=52)
            metrics['spread_zscore'] = get_latest(spread_zscore, 'spread_zscore')
            metrics['spread_level'] = get_latest(spread, 'spread_level')
        
        # VIX percentile
        vix = data.get('vix')
        if vix is not None and len(vix) > 756:  # 3 years daily
            vix_pct = calc_percentile(vix, window_years=3, periods_per_year=252)
            metrics['vix_percentile'] = get_latest(vix_pct, 'vix_percentile')
            metrics['vix_level'] = get_latest(vix, 'vix_level')
        
        # Equity 1M return
        equity = data.get('equity')
        if equity is None:
            equity = data.get('sp500')
        if equity is not None and len(equity) > 21:
            equity_1m = calc_1m_change(equity)
            metrics['equity_1m_return'] = get_latest(equity_1m, 'equity_1m_return')
        
        # Valuation vs Earnings gap
        val_z = data.get('valuation_zscore')
        earn_z = data.get('earnings_zscore')
        if val_z is not None and earn_z is not None:
            gap = val_z - earn_z
            metrics['val_earn_gap'] = get_latest(gap, 'val_earn_gap')
        
        return metrics
    
    def _calculate_scores(self, metrics: Dict[str, float]) -> RegimeScore:
        """Calculate regime scores based on metrics."""
        # Initialize scores
        expansion = 0.0
        late_cycle = 0.0
        contraction = 0.0
        stress = 0.0
        
        # Credit growth component
        credit = metrics.get('credit_growth_3m')
        if credit is not None:
            if credit > self.thresholds['credit_growth_expansion']:
                expansion += 30
            elif credit < self.thresholds['credit_growth_contraction']:
                contraction += 30
            else:
                late_cycle += 15
                expansion += 15
        
        # Spread component
        spread_z = metrics.get('spread_zscore')
        if spread_z is not None:
            if spread_z < self.thresholds['spread_zscore_tight']:
                expansion += 25
            elif spread_z > self.thresholds['spread_zscore_wide']:
                contraction += 20
                stress += 15
            else:
                late_cycle += 15
        
        # VIX component
        vix_pct = metrics.get('vix_percentile')
        if vix_pct is not None:
            if vix_pct < self.thresholds['vix_percentile_low']:
                expansion += 25
            elif vix_pct > self.thresholds['vix_stress']:
                stress += 40
            elif vix_pct > self.thresholds['vix_percentile_high']:
                contraction += 20
                stress += 10
            else:
                late_cycle += 10
        
        # Equity drawdown (stress amplifier)
        equity_1m = metrics.get('equity_1m_return')
        if equity_1m is not None:
            if equity_1m < self.thresholds['equity_drawdown']:
                stress += 30
                contraction += 10
        
        # Valuation vs Earnings gap (late-cycle detector)
        gap = metrics.get('val_earn_gap')
        if gap is not None:
            if gap > self.thresholds['valuation_vs_earnings_gap']:
                late_cycle += 30
                expansion -= 10
        
        # Normalize to 0-100
        max_score = max(expansion, late_cycle, contraction, stress, 1)
        factor = 100 / max_score if max_score > 0 else 1
        
        return RegimeScore(
            expansion=min(100, max(0, expansion * factor * 0.7)),  # Scale down
            late_cycle=min(100, max(0, late_cycle * factor * 0.7)),
            contraction=min(100, max(0, contraction * factor * 0.7)),
            stress=min(100, max(0, stress * factor * 0.7)),
        )
    
    def _generate_explanations(
        self,
        metrics: Dict[str, float],
        scores: RegimeScore,
    ) -> List[str]:
        """Generate 3-line explanation for the regime classification."""
        explanations = []
        primary = scores.get_primary_regime()
        
        # Line 1: Primary driver
        credit = metrics.get('credit_growth_3m')
        if credit is not None:
            if primary == Regime.EXPANSION:
                explanations.append(f"신용 성장 지속 ({credit:.1f}% 3M 연율) - 대차대조표 확장 중")
            elif primary == Regime.CONTRACTION:
                explanations.append(f"신용 성장 둔화 ({credit:.1f}% 3M 연율) - 대차대조표 수축 압력")
            else:
                explanations.append(f"신용 성장 {credit:.1f}% (3M 연율)")
        
        # Line 2: Risk indicator status
        vix_pct = metrics.get('vix_percentile')
        spread_z = metrics.get('spread_zscore')
        if vix_pct is not None and spread_z is not None:
            if primary == Regime.STRESS:
                explanations.append(f"변동성 상위 {vix_pct:.0f}%ile, 스프레드 z={spread_z:.1f} - 담보 스트레스 신호")
            elif primary == Regime.EXPANSION:
                explanations.append(f"변동성 하위 {100-vix_pct:.0f}%ile, 스프레드 축소 - 위험선호 환경")
            else:
                explanations.append(f"변동성 {vix_pct:.0f}%ile, 스프레드 z-score {spread_z:.1f}")
        
        # Line 3: Forward-looking warning
        gap = metrics.get('val_earn_gap')
        if primary == Regime.LATE_CYCLE and gap is not None:
            explanations.append(f"밸류에이션이 이익을 {gap:.1f}σ 초과 - 신념 과열 경고")
        elif primary == Regime.EXPANSION:
            explanations.append("취약지점: 신용 과잉 확장 모니터링 필요")
        elif primary == Regime.CONTRACTION:
            explanations.append("취약지점: 스프레드 확대 → 담보 훼손 → 강제 매도 경로 주시")
        elif primary == Regime.STRESS:
            explanations.append("취약지점: 레버리지 포지션 청산, 유동성 경색 위험")
        else:
            explanations.append("현재 레짐 지속 가능성 평가 중")
        
        return explanations[:3]  # Ensure max 3 lines
    
    def _check_data_quality(self, data: Dict[str, pd.Series]) -> Optional[str]:
        """Check data quality and return warning if issues found."""
        warnings = []
        
        required = ['credit_growth', 'bank_credit', 'spread', 'hy_spread', 'vix']
        available = [k for k in required if k in data and data[k] is not None and len(data[k]) > 0]
        
        if len(available) < 3:
            warnings.append(f"필수 지표 부족: {3 - len(available)}개 누락")
        
        for name, series in data.items():
            if series is not None and len(series) > 0:
                latest_date = series.index[-1] if hasattr(series, 'index') else None
                if latest_date:
                    days_old = (pd.Timestamp.now() - pd.Timestamp(latest_date)).days
                    if days_old > 7:
                        warnings.append(f"{name} 데이터가 {days_old}일 전 기준")
        
        return '; '.join(warnings) if warnings else None


def calculate_regime_scores(data: Dict[str, pd.Series]) -> RegimeScore:
    """
    Calculate regime scores (convenience function).
    레짐 점수 계산 (편의 함수)
    """
    classifier = RegimeClassifier()
    result = classifier.classify(data)
    return result.scores


def determine_regime(data: Dict[str, pd.Series]) -> Tuple[Regime, List[str]]:
    """
    Determine current regime with explanation (convenience function).
    현재 레짐 판정 (편의 함수)
    
    Returns:
        Tuple of (regime, list of 3 explanation lines)
    """
    classifier = RegimeClassifier()
    result = classifier.classify(data)
    return result.primary_regime, result.explanations
