"""
Marginal Belief Page
신념/기대/리스크 프리미엄 페이지

핵심 철학:
- 가격은 돈의 양이 아닌 한계 투자자(marginal buyer)의 신념에서 결정
- 기대와 위험 프리미엄이 가격을 움직임
- "신념 과열" 신호: 밸류에이션 확장 속도 > 이익/생산성 개선 속도
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime
from components.charts import (
    create_timeseries_chart, 
    create_multi_line_chart,
    create_valuation_scatter,
)
from components.cards import render_alert_card
from components.reports import generate_belief_analysis, generate_fundamental_check
from indicators.transforms import (
    calc_zscore, 
    calc_zscore_change,
    calc_1m_change,
)
from indicators.alerts import check_belief_overheating, AlertLevel
from components.styles import render_page_header, render_numbered_list, COLOR_PALETTE


st.set_page_config(
    page_title="신념/기대 | 유동성 대시보드",
    page_icon="🧠",
    layout="wide",
)

# Apply global CSS
from components.styles import get_global_css
st.markdown(get_global_css(), unsafe_allow_html=True)

render_page_header(
    icon="🧠",
    title="Marginal Belief",
    subtitle="한계 투자자의 신념과 리스크 프리미엄 모니터링",
    philosophy="자산 가격은 **돈의 양**이 아니라 **한계 투자자(marginal buyer)의 신념**(기대수익, 위험 프리미엄)에서 움직입니다.",
)

# Get data
if 'data_dict' not in st.session_state:
    st.warning("⚠️ 먼저 메인 페이지에서 데이터를 로드해주세요.")
    st.page_link("app.py", label="메인 페이지로 이동", icon="🏠")
    st.stop()

data_dict = st.session_state['data_dict']
regime_result = st.session_state['regime_result']


# ============================================================================
# BELIEF OVERHEATING CHECK
# ============================================================================

st.markdown("### 🔥 신념 과열 신호")

alert = check_belief_overheating(data_dict)

if alert:
    render_alert_card(
        level=alert.level,
        title=alert.title,
        message=alert.format_message(),
        additional_checks=alert.additional_checks,
    )
else:
    st.success("✅ 현재 신념 과열 신호 없음")


# ============================================================================
# KEY METRICS
# ============================================================================

st.markdown("---")
st.markdown("### 📊 주요 지표")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if 'real_yield' in data_dict:
        ry = data_dict['real_yield']
        latest = ry.iloc[-1] if len(ry) > 0 else 0
        change_1m = calc_1m_change(ry).iloc[-1] if len(ry) > 4 else None
        
        st.metric(
            "실질금리 (10Y)",
            f"{latest:+.2f}%",
            f"{change_1m:+.2f}pp" if change_1m else None,
            delta_color="inverse",
        )

with col2:
    if 'breakeven' in data_dict:
        be = data_dict['breakeven']
        latest = be.iloc[-1] if len(be) > 0 else 0
        change_1m = calc_1m_change(be).iloc[-1] if len(be) > 4 else None
        
        st.metric(
            "기대인플레이션 (10Y)",
            f"{latest:.2f}%",
            f"{change_1m:+.2f}pp" if change_1m else None,
        )

with col3:
    if 'pe_ratio' in data_dict:
        pe = data_dict['pe_ratio']
        latest = pe.iloc[-1] if len(pe) > 0 else 0
        zscore = calc_zscore(pe, window_years=3, periods_per_year=52).iloc[-1] if len(pe) > 156 else None
        
        st.metric(
            "P/E Ratio",
            f"{latest:.1f}x",
            f"z={zscore:+.1f}" if zscore else None,
            delta_color="inverse" if zscore and zscore > 1 else "normal",
        )

with col4:
    if 'forward_eps' in data_dict:
        eps = data_dict['forward_eps']
        latest = eps.iloc[-1] if len(eps) > 0 else 0
        change_3m = (eps.iloc[-1] / eps.iloc[-13] - 1) * 100 if len(eps) > 13 else None
        
        st.metric(
            "Forward EPS",
            f"${latest:.1f}",
            f"{change_3m:+.1f}% (3M)" if change_3m else None,
        )


# ============================================================================
# INTEREST RATES AND EXPECTATIONS
# ============================================================================

st.markdown("---")
st.markdown("### 💰 금리와 인플레이션 기대")

rate_data = {}
if 'real_yield' in data_dict:
    rate_data['Real Yield (10Y)'] = data_dict['real_yield']
if 'breakeven' in data_dict:
    rate_data['Breakeven (10Y)'] = data_dict['breakeven']

if rate_data:
    col1, col2 = st.columns(2)
    
    with col1:
        fig = create_multi_line_chart(
            rate_data,
            title='실질금리 vs 기대인플레이션 (%)',
            height=400,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        # Implied nominal = real + breakeven
        if 'real_yield' in data_dict and 'breakeven' in data_dict:
            ry = data_dict['real_yield']
            be = data_dict['breakeven']
            common_idx = ry.index.intersection(be.index)
            nominal = ry.loc[common_idx] + be.loc[common_idx]
            
            implied_data = {
                'Real Yield': ry.loc[common_idx],
                'Breakeven': be.loc[common_idx],
                'Implied Nominal': nominal,
            }
            
            fig = create_multi_line_chart(
                implied_data,
                title='금리 분해 (실질 + 기대인플레)',
                height=400,
            )
            st.plotly_chart(fig, width="stretch")


# ============================================================================
# VALUATION VS EARNINGS
# ============================================================================

st.markdown("---")
st.markdown("### 📐 밸류에이션 vs 이익추정")
st.markdown("*밸류에이션 확장이 이익 개선으로 정당화되는가?*")

if 'pe_ratio' in data_dict and 'forward_eps' in data_dict:
    pe = data_dict['pe_ratio']
    eps = data_dict['forward_eps']
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Time series comparison
        pe_zscore = calc_zscore(pe, window_years=3, periods_per_year=52)
        eps_zscore = calc_zscore(eps, window_years=3, periods_per_year=52)
        
        zscore_data = {
            'PE Z-Score': pe_zscore,
            'EPS Z-Score': eps_zscore,
        }
        
        fig = create_multi_line_chart(
            zscore_data,
            title='밸류에이션 vs 이익추정 Z-Score',
            height=400,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        # Scatter plot: valuation change vs earnings change
        val_change = calc_zscore_change(pe, window_years=3, change_periods=4, periods_per_year=52)
        earn_change = calc_zscore_change(eps, window_years=3, change_periods=4, periods_per_year=52)
        
        if len(val_change.dropna()) > 10 and len(earn_change.dropna()) > 10:
            fig = create_valuation_scatter(
                val_change,
                earn_change,
                title='신념 과열 탐지 (1개월 Z-score 변화)',
                height=400,
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("충분한 데이터가 없어 산점도를 표시할 수 없습니다.")

    # Gap analysis
    st.markdown("#### 밸류에이션-이익 Gap")
    
    pe_z = calc_zscore(pe, window_years=3, periods_per_year=52)
    eps_z = calc_zscore(eps, window_years=3, periods_per_year=52)
    
    common_idx = pe_z.index.intersection(eps_z.index)
    gap = pe_z.loc[common_idx] - eps_z.loc[common_idx]
    
    gap_df = pd.DataFrame({
        'date': gap.index,
        'value': gap.values,
        'indicator': 'PE-EPS Gap'
    })
    
    fig = create_timeseries_chart(
        gap_df,
        title='밸류에이션-이익 Gap (PE z-score - EPS z-score)',
        height=350,
    )
    fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.3)
    fig.add_hline(y=0.5, line_dash="dash", line_color="orange", opacity=0.5,
                 annotation_text="경계", annotation_position="right")
    fig.add_hline(y=1.0, line_dash="dash", line_color="red", opacity=0.5,
                 annotation_text="과열", annotation_position="right")
    st.plotly_chart(fig, width="stretch")
    
    latest_gap = gap.iloc[-1] if len(gap) > 0 else 0
    
    if latest_gap > 1.0:
        st.error(f"🔴 **신념 과열**: 밸류에이션이 이익추정을 {latest_gap:.1f}σ 초과")
    elif latest_gap > 0.5:
        st.warning(f"🟡 **경계**: 밸류에이션이 이익추정을 {latest_gap:.1f}σ 초과")
    elif latest_gap < -0.5:
        st.success(f"🟢 **저평가**: 이익추정이 밸류에이션을 {-latest_gap:.1f}σ 초과")
    else:
        st.info(f"균형: Gap = {latest_gap:.2f}σ")


# ============================================================================
# BELIEF ANALYSIS (3 SENTENCES)
# ============================================================================

st.markdown("---")
st.markdown("### 🧠 신념 분석")
st.markdown("*현재 대차대조표를 확장시키는 신념은 무엇인가?*")

# Get metrics for analysis
credit_growth = None
if 'bank_credit' in data_dict:
    from indicators.transforms import calc_3m_annualized
    credit = data_dict['bank_credit']
    credit_3m = calc_3m_annualized(credit, periods_3m=13)
    credit_growth = credit_3m.iloc[-1] if len(credit_3m) > 0 else None

real_yield = data_dict['real_yield'].iloc[-1] if 'real_yield' in data_dict and len(data_dict['real_yield']) > 0 else None
breakeven = data_dict['breakeven'].iloc[-1] if 'breakeven' in data_dict and len(data_dict['breakeven']) > 0 else None
pe_zscore = calc_zscore(pe, window_years=3, periods_per_year=52).iloc[-1] if 'pe_ratio' in data_dict else None
eps_growth_val = (eps.iloc[-1] / eps.iloc[-13] - 1) * 100 if 'forward_eps' in data_dict and len(eps) > 13 else None

analysis = generate_belief_analysis(
    regime=regime_result.primary_regime,
    credit_growth=credit_growth,
    real_yield=real_yield,
    breakeven=breakeven,
    pe_zscore=pe_zscore,
    eps_growth=eps_growth_val,
)

render_numbered_list(
    items=analysis,
    accent_color=COLOR_PALETTE['secondary'],
)


# ============================================================================
# FUNDAMENTAL CHECK
# ============================================================================

st.markdown("---")
st.markdown("### ✅ 실물 뒷받침 체크리스트")
st.markdown("*그 신념이 실물(이익/생산성)로 뒷받침되는가?*")

checks = generate_fundamental_check(
    pe_zscore=pe_zscore,
    eps_growth=eps_growth_val,
    credit_growth=credit_growth,
)

if checks:
    for check_item, passed, explanation in checks:
        if passed is True:
            st.markdown(f"✅ **{check_item}**: {explanation}")
        elif passed is False:
            st.markdown(f"❌ **{check_item}**: {explanation}")
        else:
            st.markdown(f"⚠️ **{check_item}**: {explanation}")
else:
    st.info("체크리스트 평가를 위한 데이터가 부족합니다.")


# ============================================================================
# INTERPRETATION
# ============================================================================

st.markdown("---")

with st.expander("💡 신념 지표 해석 가이드"):
    st.markdown("""
    #### 한계 투자자(Marginal Buyer)의 신념
    
    가격은 **평균 투자자**가 아닌 **한계 투자자**의 신념으로 결정됩니다.
    한계 투자자는 현재 가격에서 매수/매도를 결정하는 마지막 트레이더입니다.
    
    #### 실질금리와 위험자산
    - **마이너스 실질금리**: 현금 보유 비용 → 위험자산 선호
    - **플러스 실질금리**: 안전자산 매력 상승 → 위험자산 할인율 상승
    
    #### 기대인플레이션
    - **상승**: 명목자산보다 실물자산(주식, 상품) 선호
    - **하락**: 디플레이션 우려 → 성장 둔화 시그널
    
    #### 신념 과열 감지
    - **PE z-score > EPS z-score**: 밸류에이션이 이익을 앞서감
    - 밸류에이션 확장이 이익 개선 없이 진행되면 **신념 과열**
    - 신념이 현실화되지 않으면 급격한 되돌림 위험
    """)
