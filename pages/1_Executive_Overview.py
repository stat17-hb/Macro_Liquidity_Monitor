"""
Executive Overview Page
통합 대시보드 개요 페이지

핵심 철학:
- 대차대조표 확장/수축, 담보가치, 리스크 프리미엄, 레버리지, 신용 스프레드를 한 화면에
- 위험 레짐(Expansion/Late-cycle/Contraction/Stress) 상단 배지
- 취약 지점 Top 3 자동 텍스트 출력
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime, REGIME_COLORS
from components.cards import render_regime_badge, render_metric_card, render_vulnerability_card
from components.charts import create_timeseries_chart, create_regime_gauge
from components.reports import (
    generate_daily_summary, 
    generate_belief_analysis, 
    generate_vulnerability_report
)
from components.styles import render_page_header, render_info_box, render_numbered_list, COLOR_PALETTE
from indicators.transforms import (
    calc_zscore, 
    calc_1m_change, 
    calc_3m_annualized,
    calc_percentile
)


st.set_page_config(
    page_title="Executive Overview | 유동성 대시보드",
    page_icon="📈",
    layout="wide",
)

# Apply global CSS
from components.styles import get_global_css
st.markdown(get_global_css(), unsafe_allow_html=True)

render_page_header(
    icon="📈",
    title="Executive Overview",
    subtitle="대차대조표 확장/수축 관점의 유동성 종합 현황",
)

# Get data from session state
if 'data_dict' not in st.session_state:
    st.warning("⚠️ 먼저 메인 페이지에서 데이터를 로드해주세요.")
    st.page_link("app.py", label="메인 페이지로 이동", icon="🏠")
    st.stop()

data_dict = st.session_state['data_dict']
regime_result = st.session_state['regime_result']


# ============================================================================
# REGIME BADGE (상단)
# ============================================================================

render_regime_badge(
    regime=regime_result.primary_regime,
    explanations=regime_result.explanations,
    confidence=regime_result.confidence,
)


# ============================================================================
# ONE-LINE SUMMARY (오늘의 요약)
# ============================================================================

# Extract metrics for summary
metrics = {}

if 'bank_credit' in data_dict:
    credit = data_dict['bank_credit']
    credit_3m = calc_3m_annualized(credit, periods_3m=13)  # Weekly
    metrics['credit_growth_3m'] = credit_3m.iloc[-1] if len(credit_3m) > 0 else None

if 'hy_spread' in data_dict:
    spread = data_dict['hy_spread']
    spread_z = calc_zscore(spread, window_years=3, periods_per_year=52)
    metrics['spread_zscore'] = spread_z.iloc[-1] if len(spread_z) > 0 else None

if 'vix' in data_dict:
    vix = data_dict['vix']
    vix_pct = calc_percentile(vix, window_years=3, periods_per_year=252)
    metrics['vix_percentile'] = vix_pct.iloc[-1] if len(vix_pct) > 0 else None

if 'sp500' in data_dict:
    equity = data_dict['sp500']
    equity_1m = calc_1m_change(equity)
    metrics['equity_1m'] = equity_1m.iloc[-1] if len(equity_1m) > 0 else None

# Generate summary
summary = generate_daily_summary(
    regime=regime_result.primary_regime,
    credit_growth=metrics.get('credit_growth_3m'),
    spread_zscore=metrics.get('spread_zscore'),
    vix_percentile=metrics.get('vix_percentile'),
    equity_1m=metrics.get('equity_1m'),
)

render_info_box(
    content=summary,
    title="📝 오늘의 한 줄 요약",
)


# ============================================================================
# KEY METRICS CARDS (6개 핵심 카드)
# ============================================================================

st.markdown("### 📊 핵심 지표")

col1, col2, col3 = st.columns(3)

with col1:
    # Credit Growth
    if 'bank_credit' in data_dict:
        credit = data_dict['bank_credit']
        latest = credit.iloc[-1] / 1e12 if len(credit) > 0 else 0
        change_1m = calc_1m_change(credit).iloc[-1] if len(credit) > 21 else None
        
        st.metric(
            "🏦 은행 신용",
            f"${latest:.2f}T",
            f"{change_1m:+.1f}% (1M)" if change_1m and not np.isnan(change_1m) else None,
        )
    else:
        st.info("Bank Credit 데이터 없음")

with col2:
    # Credit Spread
    if 'hy_spread' in data_dict:
        spread = data_dict['hy_spread']
        latest = spread.iloc[-1] * 100 if len(spread) > 0 else 0
        change_1m = calc_1m_change(spread).iloc[-1] if len(spread) > 4 else None
        
        st.metric(
            "📈 HY 스프레드",
            f"{latest:.0f} bps",
            f"{change_1m:+.1f}%" if change_1m and not np.isnan(change_1m) else None,
            delta_color="inverse",
        )
    else:
        st.info("HY Spread 데이터 없음")

with col3:
    # VIX
    if 'vix' in data_dict:
        vix = data_dict['vix']
        latest = vix.iloc[-1] if len(vix) > 0 else 0
        change_1m = calc_1m_change(vix).iloc[-1] if len(vix) > 21 else None
        
        st.metric(
            "⚡ VIX",
            f"{latest:.1f}",
            f"{change_1m:+.1f}%" if change_1m and not np.isnan(change_1m) else None,
            delta_color="inverse",
        )
    else:
        st.info("VIX 데이터 없음")

col4, col5, col6 = st.columns(3)

with col4:
    # Real Yield
    if 'real_yield' in data_dict:
        ry = data_dict['real_yield']
        latest = ry.iloc[-1] if len(ry) > 0 else 0
        change_1m = calc_1m_change(ry).iloc[-1] if len(ry) > 4 else None
        
        st.metric(
            "💰 실질금리 (10Y)",
            f"{latest:+.2f}%",
            f"{change_1m:+.2f}pp" if change_1m and not np.isnan(change_1m) else None,
            delta_color="inverse",
        )
    else:
        st.info("Real Yield 데이터 없음")

with col5:
    # S&P 500
    if 'sp500' in data_dict:
        sp = data_dict['sp500']
        latest = sp.iloc[-1] if len(sp) > 0 else 0
        ret_1m = calc_1m_change(sp).iloc[-1] if len(sp) > 21 else None
        
        st.metric(
            "📊 S&P 500",
            f"{latest:,.0f}",
            f"{ret_1m:+.1f}% (1M)" if ret_1m and not np.isnan(ret_1m) else None,
        )
    else:
        st.info("S&P 500 데이터 없음")

with col6:
    # PE Ratio
    if 'pe_ratio' in data_dict:
        pe = data_dict['pe_ratio']
        latest = pe.iloc[-1] if len(pe) > 0 else 0
        zscore = calc_zscore(pe, window_years=3, periods_per_year=52).iloc[-1] if len(pe) > 156 else None
        
        st.metric(
            "📐 P/E Ratio",
            f"{latest:.1f}x",
            f"z={zscore:+.1f}" if zscore and not np.isnan(zscore) else None,
        )
    else:
        st.info("P/E Ratio 데이터 없음")


# ============================================================================
# KEY TIME SERIES (핵심 타임시리즈)
# ============================================================================

st.markdown("---")
st.markdown("### 📈 핵심 타임시리즈")

col1, col2 = st.columns(2)

with col1:
    # Balance sheet chart
    if 'bank_credit' in data_dict or 'fed_assets' in data_dict or 'm2' in data_dict:
        chart_data = {}
        if 'fed_assets' in data_dict:
            chart_data['Fed Assets'] = data_dict['fed_assets'] / 1e12
        if 'bank_credit' in data_dict:
            chart_data['Bank Credit'] = data_dict['bank_credit'] / 1e12
        if 'm2' in data_dict:
            chart_data['M2'] = data_dict['m2'] / 1e12
        
        from components.charts import create_multi_line_chart
        fig = create_multi_line_chart(chart_data, title='대차대조표 규모 (조 달러)', normalize=False)
        st.plotly_chart(fig, width="stretch")

with col2:
    # Risk indicators
    if 'vix' in data_dict or 'hy_spread' in data_dict:
        chart_data = {}
        if 'vix' in data_dict:
            chart_data['VIX'] = data_dict['vix']
        if 'hy_spread' in data_dict:
            chart_data['HY Spread (%)'] = data_dict['hy_spread'] * 100
        
        from components.charts import create_multi_line_chart
        fig = create_multi_line_chart(
            chart_data, 
            title='리스크 지표', 
            normalize=False,
            secondary_y=['HY Spread (%)'] if 'HY Spread (%)' in chart_data else None
        )
        st.plotly_chart(fig, width="stretch")


# ============================================================================
# REGIME GAUGE
# ============================================================================

st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🎯 레짐 점수")
    fig = create_regime_gauge(
        scores=regime_result.scores.to_dict(),
        primary_regime=regime_result.primary_regime.value,
    )
    st.plotly_chart(fig, width="stretch")

with col2:
    st.markdown("### ⚠️ 취약 지점 Top 3")
    
    # Generate vulnerability report
    vulnerabilities = generate_vulnerability_report(
        regime=regime_result.primary_regime,
        metrics=metrics,
    )
    
    if vulnerabilities:
        for vuln in vulnerabilities:
            render_vulnerability_card(
                rank=vuln['rank'],
                title=vuln['title'],
                description=vuln['description'],
                severity=vuln['severity'],
                related_indicators=vuln.get('indicators', []),
            )
    else:
        st.info("현재 주요 취약 지점이 감지되지 않습니다.")


# ============================================================================
# BELIEF ANALYSIS (신념 분석)
# ============================================================================

st.markdown("---")
st.markdown("### 🧠 신념 분석")
st.markdown("*현재 대차대조표를 확장시키는 신념은 무엇인가?*")

# Get additional metrics
pe_zscore = None
if 'pe_ratio' in data_dict:
    pe = data_dict['pe_ratio']
    pe_zscore = calc_zscore(pe, window_years=3, periods_per_year=52).iloc[-1] if len(pe) > 156 else None

eps_growth = None
if 'forward_eps' in data_dict:
    eps = data_dict['forward_eps']
    eps_growth = calc_1m_change(eps).iloc[-1] * 12 if len(eps) > 4 else None  # Annualized

real_yield = metrics.get('real_yield')
if 'real_yield' in data_dict:
    real_yield = data_dict['real_yield'].iloc[-1] if len(data_dict['real_yield']) > 0 else None

breakeven = None
if 'breakeven' in data_dict:
    breakeven = data_dict['breakeven'].iloc[-1] if len(data_dict['breakeven']) > 0 else None

# Generate analysis
analysis = generate_belief_analysis(
    regime=regime_result.primary_regime,
    credit_growth=metrics.get('credit_growth_3m'),
    real_yield=real_yield,
    breakeven=breakeven,
    pe_zscore=pe_zscore,
    eps_growth=eps_growth,
)

render_numbered_list(
    items=analysis,
    accent_color=COLOR_PALETTE['primary'],
)


# ============================================================================
# DATA QUALITY WARNING
# ============================================================================

if regime_result.data_quality_warning:
    st.markdown("---")
    st.warning(f"⚠️ 데이터 품질 경고: {regime_result.data_quality_warning}")
