"""
Report generation module.
리포트 생성 모듈

핵심 리포트:
- 오늘의 한 줄 요약 (유동성=대차대조표 관점)
- "현재 대차대조표를 확장시키는 신념은 무엇인가?" 분석
- "그 신념이 실물로 뒷받침되는가?" 체크리스트
- 취약 지점 보고서
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime, REGIME_DESCRIPTIONS


def generate_daily_summary(
    regime: Regime,
    credit_growth: Optional[float] = None,
    spread_zscore: Optional[float] = None,
    vix_percentile: Optional[float] = None,
    equity_1m: Optional[float] = None,
) -> str:
    """
    Generate one-line daily summary.
    오늘의 한 줄 요약 생성
    
    철학: 유동성 = 대차대조표 확장/수축
    
    Args:
        regime: Current regime
        credit_growth: Bank credit 3M annualized growth
        spread_zscore: Credit spread z-score
        vix_percentile: VIX percentile
        equity_1m: Equity 1M return
        
    Returns:
        One-line summary string
    """
    parts = []
    
    # Regime state
    if regime == Regime.EXPANSION:
        parts.append("금융시스템 대차대조표가 확장 중이며")
    elif regime == Regime.LATE_CYCLE:
        parts.append("대차대조표 확장 지속되나 신념이 실물을 앞서가고 있어")
    elif regime == Regime.CONTRACTION:
        parts.append("대차대조표 수축 압력이 감지되며")
    else:  # STRESS
        parts.append("담보가치 훼손으로 대차대조표 급격한 수축 위험에")
    
    # Credit state
    if credit_growth is not None:
        if credit_growth > 5:
            parts.append(f"신용 창출 활발 ({credit_growth:.1f}% 연율)")
        elif credit_growth > 0:
            parts.append(f"신용 성장 완만 ({credit_growth:.1f}% 연율)")
        else:
            parts.append(f"신용 수축 진행 ({credit_growth:.1f}% 연율)")
    
    # Risk state
    risk_parts = []
    if spread_zscore is not None:
        if spread_zscore > 1.5:
            risk_parts.append("스프레드 확대")
        elif spread_zscore < -1:
            risk_parts.append("스프레드 축소")
    
    if vix_percentile is not None:
        if vix_percentile > 80:
            risk_parts.append("변동성 고조")
        elif vix_percentile < 20:
            risk_parts.append("변동성 안정")
    
    if risk_parts:
        parts.append(f"리스크 프리미엄은 {', '.join(risk_parts)}")
    
    return ', '.join(parts) + '.'


def generate_belief_analysis(
    regime: Regime,
    credit_growth: Optional[float] = None,
    real_yield: Optional[float] = None,
    breakeven: Optional[float] = None,
    pe_zscore: Optional[float] = None,
    eps_growth: Optional[float] = None,
) -> List[str]:
    """
    Generate 3-sentence analysis of what belief is expanding balance sheets.
    "현재 대차대조표를 확장시키는 신념은 무엇인가?" 분석
    
    철학: 가격 = 한계 투자자(marginal buyer)의 신념
    
    Returns:
        List of 3 analysis sentences
    """
    sentences = []
    
    # Sentence 1: Identify the primary belief
    if pe_zscore is not None and pe_zscore > 1:
        if eps_growth is not None and eps_growth > 10:
            sentences.append(
                f"현재 밸류에이션 확장(PE z-score {pe_zscore:.1f})은 "
                f"강한 이익 성장 기대({eps_growth:.1f}%)에 기반합니다."
            )
        else:
            sentences.append(
                f"현재 밸류에이션 확장(PE z-score {pe_zscore:.1f})은 "
                "이익 성장보다는 할인율 하락(금리 인하 기대)에 기반합니다."
            )
    elif real_yield is not None:
        if real_yield < 0:
            sentences.append(
                f"마이너스 실질금리({real_yield:.2f}%)가 위험자산 선호를 지지하며, "
                "현금 보유 비용이 자산 매수를 유도합니다."
            )
        elif real_yield < 1:
            sentences.append(
                f"낮은 실질금리({real_yield:.2f}%)가 레버리지 비용을 낮추어 "
                "대차대조표 확장을 지원합니다."
            )
        else:
            sentences.append(
                f"상승한 실질금리({real_yield:.2f}%)가 할인율을 높여 "
                "대차대조표 확장을 제약하고 있습니다."
            )
    else:
        sentences.append("현재 시장의 지배적 신념을 파악하기 위한 데이터가 부족합니다.")
    
    # Sentence 2: Risk appetite source
    if breakeven is not None:
        if breakeven > 2.5:
            sentences.append(
                f"높은 기대인플레이션({breakeven:.1f}%)은 "
                "실물자산과 주식에 대한 선호를 강화합니다."
            )
        elif breakeven < 2.0:
            sentences.append(
                f"낮은 기대인플레이션({breakeven:.1f}%)은 "
                "성장 둔화 우려를 반영하며 신중한 자산배분을 시사합니다."
            )
        else:
            sentences.append(
                f"안정적인 기대인플레이션({breakeven:.1f}%)은 "
                "현재 신념이 극단적이지 않음을 보여줍니다."
            )
    else:
        sentences.append("인플레이션 기대 데이터를 확인할 수 없습니다.")
    
    # Sentence 3: Marginal buyer behavior
    if credit_growth is not None:
        if credit_growth > 5:
            sentences.append(
                "활발한 신용 창출은 한계 투자자가 레버리지를 통해 "
                "적극적으로 위험자산을 매수하고 있음을 시사합니다."
            )
        elif credit_growth > 0:
            sentences.append(
                "완만한 신용 성장은 한계 투자자의 위험 선호가 "
                "과도하지도 위축되지도 않은 균형 상태임을 보여줍니다."
            )
        else:
            sentences.append(
                "신용 수축은 한계 투자자가 레버리지를 축소하며 "
                "위험자산 노출을 줄이고 있음을 경고합니다."
            )
    else:
        sentences.append("신용 성장 데이터가 필요합니다.")
    
    return sentences[:3]


def generate_fundamental_check(
    pe_zscore: Optional[float] = None,
    eps_growth: Optional[float] = None,
    credit_growth: Optional[float] = None,
    productivity_growth: Optional[float] = None,
    sales_growth: Optional[float] = None,
) -> List[Tuple[str, bool, str]]:
    """
    Generate checklist: "Is belief backed by fundamentals?"
    "그 신념이 실물(이익/생산성)로 뒷받침되는가?" 체크리스트
    
    Returns:
        List of (check_item, is_passed, explanation) tuples
    """
    checks = []
    
    # Check 1: Valuation vs. Earnings
    if pe_zscore is not None and eps_growth is not None:
        if pe_zscore > 1:
            if eps_growth > pe_zscore * 5:  # Rough heuristic
                passed = True
                explanation = f"밸류에이션 확장이 이익 성장({eps_growth:.1f}%)으로 정당화됨"
            else:
                passed = False
                explanation = f"밸류에이션(z={pe_zscore:.1f}) 확장이 이익 성장({eps_growth:.1f}%)을 앞서감"
        else:
            passed = True
            explanation = "밸류에이션이 과도하게 확장되지 않음"
        checks.append(("밸류에이션 ≤ 이익 성장", passed, explanation))
    
    # Check 2: Credit vs. Productivity
    if credit_growth is not None:
        if productivity_growth is not None:
            if credit_growth <= productivity_growth * 1.5:
                passed = True
                explanation = f"신용 성장({credit_growth:.1f}%)이 생산성 개선과 균형"
            else:
                passed = False
                explanation = f"신용 성장({credit_growth:.1f}%)이 생산성 개선을 크게 초과"
        else:
            # Use sales growth as proxy
            if sales_growth is not None:
                if credit_growth <= sales_growth * 1.5:
                    passed = True
                    explanation = f"신용 성장({credit_growth:.1f}%)이 매출 성장과 균형"
                else:
                    passed = False
                    explanation = f"신용 성장({credit_growth:.1f}%)이 매출 성장을 초과"
            else:
                passed = None
                explanation = "생산성/매출 데이터 부족"
        checks.append(("신용 성장 ≤ 생산성 개선", passed, explanation))
    
    # Check 3: Leverage sustainability
    if credit_growth is not None and eps_growth is not None:
        if credit_growth <= eps_growth + 3:  # Allow some margin
            passed = True
            explanation = "레버리지 증가가 이익 개선 범위 내"
        else:
            passed = False
            explanation = f"레버리지 증가({credit_growth:.1f}%)가 이익 개선({eps_growth:.1f}%)을 초과"
        checks.append(("레버리지 확장 지속가능", passed, explanation))
    
    return checks


def generate_vulnerability_report(
    regime: Regime,
    metrics: Dict[str, float],
    alerts: Optional[List] = None,
) -> List[Dict[str, str]]:
    """
    Generate top 3 vulnerabilities report.
    취약 지점 Top 3 보고서 생성
    
    철학: 목표 = 취약 지점 탐지 (가격 설명 X)
    
    Returns:
        List of {rank, title, description, severity, indicators} dicts
    """
    vulnerabilities = []
    
    # Analyze metrics to find vulnerabilities
    credit_growth = metrics.get('credit_growth_3m')
    spread_zscore = metrics.get('spread_zscore')
    vix_percentile = metrics.get('vix_percentile')
    pe_zscore = metrics.get('pe_zscore')
    real_yield = metrics.get('real_yield')
    
    # Vulnerability 1: Leverage accumulation
    if credit_growth is not None and credit_growth > 8:
        vulnerabilities.append({
            'title': '레버리지 과잉 축적',
            'description': (
                f"신용 성장({credit_growth:.1f}%)이 빠르게 진행 중. "
                "경기 둔화 시 동시다발적 디레버리징 위험."
            ),
            'severity': 'high' if credit_growth > 12 else 'medium',
            'indicators': ['Bank Credit', 'Consumer Credit', 'HY Issuance'],
        })
    
    # Vulnerability 2: Valuation stretch
    if pe_zscore is not None and pe_zscore > 1.5:
        vulnerabilities.append({
            'title': '밸류에이션 과열',
            'description': (
                f"밸류에이션 z-score({pe_zscore:.1f})가 높음. "
                "이익 실망 시 급격한 되돌림 가능."
            ),
            'severity': 'high' if pe_zscore > 2 else 'medium',
            'indicators': ['Forward EPS', 'PE Ratio', 'Earnings Revisions'],
        })
    
    # Vulnerability 3: Spread complacency
    if spread_zscore is not None and spread_zscore < -1:
        vulnerabilities.append({
            'title': '스프레드 안주',
            'description': (
                f"스프레드가 역사적 저점 수준(z={spread_zscore:.1f}). "
                "신용 이벤트 발생 시 급격한 확대 위험."
            ),
            'severity': 'medium',
            'indicators': ['HY Spread', 'IG Spread', 'Default Rate'],
        })
    
    # Vulnerability 4: Rate sensitivity
    if real_yield is not None and real_yield < 0:
        vulnerabilities.append({
            'title': '금리 상승 취약',
            'description': (
                f"마이너스 실질금리({real_yield:.1f}%)에 의존한 밸류에이션. "
                "금리 정상화 시 듀레이션 자산 조정 위험."
            ),
            'severity': 'medium',
            'indicators': ['10Y Real Yield', 'Fed Policy', 'Duration Assets'],
        })
    
    # Vulnerability 5: Volatility complacency
    if vix_percentile is not None and vix_percentile < 20:
        vulnerabilities.append({
            'title': '변동성 저평가',
            'description': (
                f"VIX가 하위 {vix_percentile:.0f}%ile. "
                "숏 감마 포지션 증가 시 변동성 급등 위험."
            ),
            'severity': 'low',
            'indicators': ['VIX', 'Option Gamma', 'Vol of Vol'],
        })
    
    # Add regime-specific vulnerabilities
    if regime == Regime.LATE_CYCLE:
        vulnerabilities.append({
            'title': '사이클 후반 리스크',
            'description': (
                "신념이 실물보다 앞서감. "
                "경기 지표 악화 시 신뢰 붕괴 위험."
            ),
            'severity': 'medium',
            'indicators': ['ISM PMI', 'Leading Indicators', 'Yield Curve'],
        })
    elif regime == Regime.STRESS:
        vulnerabilities.append({
            'title': '시스템 리스크',
            'description': (
                "담보가치 훼손으로 강제 청산 진행. "
                "반대매매 → 가격 하락 → 추가 마진콜 악순환."
            ),
            'severity': 'high',
            'indicators': ['Margin Debt', 'ETF Flows', 'Dealer Inventory'],
        })
    
    # Sort by severity and take top 3
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    vulnerabilities.sort(key=lambda x: severity_order.get(x['severity'], 2))
    
    # Add rank
    for i, v in enumerate(vulnerabilities[:3], 1):
        v['rank'] = i
    
    return vulnerabilities[:3]
