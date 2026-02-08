"""
Balance Sheet Expansion Page
대차대조표/신용창출 페이지

핵심 철학:
- 유동성은 대차대조표 확장/수축
- 중앙은행, 은행신용, M2로 "시스템이 얼마나 대차대조표를 늘리는지" 측정
- 성장률/가속도(2차 미분), 분해(기여도), 변곡점 탐지
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime
from components.charts import create_timeseries_chart, create_multi_line_chart, create_zscore_heatmap
from components.cards import render_metric_card
from indicators.transforms import (
    calc_yoy, 
    calc_3m_annualized, 
    calc_1m_change,
    calc_zscore,
    calc_acceleration,
    detect_inflection,
)
from components.styles import render_page_header


st.set_page_config(
    page_title="대차대조표 | 유동성 대시보드",
    page_icon="🏦",
    layout="wide",
)

# Apply global CSS
from components.styles import get_global_css
st.markdown(get_global_css(), unsafe_allow_html=True)

render_page_header(
    icon="🏦",
    title="Balance Sheet Expansion",
    subtitle="대차대조표 확장/수축과 신용창출 모니터링",
    philosophy="유동성은 고정된 돈의 총량이 아니라, **금융시스템 대차대조표가 확장·수축**하며 '파생'되는 결과입니다.",
)

# Get data
if 'data_dict' not in st.session_state:
    st.warning("⚠️ 먼저 메인 페이지에서 데이터를 로드해주세요.")
    st.page_link("app.py", label="메인 페이지로 이동", icon="🏠")
    st.stop()

data_dict = st.session_state['data_dict']


# ============================================================================
# OVERVIEW METRICS
# ============================================================================

st.markdown("### 📊 대차대조표 현황")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if 'fed_assets' in data_dict:
        fed = data_dict['fed_assets']
        latest = fed.iloc[-1] / 1e12 if len(fed) > 0 else 0
        yoy = calc_yoy(fed, periods=52).iloc[-1] if len(fed) > 52 else None
        
        st.metric(
            "Fed 자산",
            f"${latest:.2f}T",
            f"{yoy:+.1f}% YoY" if yoy else None,
        )

with col2:
    if 'bank_credit' in data_dict:
        credit = data_dict['bank_credit']
        latest = credit.iloc[-1] / 1e12 if len(credit) > 0 else 0
        ann_3m = calc_3m_annualized(credit, periods_3m=13).iloc[-1] if len(credit) > 13 else None
        
        st.metric(
            "은행 신용",
            f"${latest:.2f}T",
            f"{ann_3m:+.1f}% (3M ann)" if ann_3m else None,
        )

with col3:
    if 'm2' in data_dict:
        m2 = data_dict['m2']
        latest = m2.iloc[-1] / 1e12 if len(m2) > 0 else 0
        yoy = calc_yoy(m2, periods=52).iloc[-1] if len(m2) > 52 else None
        
        st.metric(
            "M2",
            f"${latest:.2f}T",
            f"{yoy:+.1f}% YoY" if yoy else None,
        )

with col4:
    # Calculate total balance sheet growth
    if 'bank_credit' in data_dict:
        credit = data_dict['bank_credit']
        acc = calc_acceleration(credit, 13, 13)  # Weekly
        latest_acc = acc.iloc[-1] if len(acc) > 0 else None
        
        status = "가속" if latest_acc and latest_acc > 0 else "감속"
        st.metric(
            "성장 가속도",
            status,
            f"{latest_acc/1e9:+.1f}B/wk²" if latest_acc else None,
        )


# ============================================================================
# LEVEL CHARTS
# ============================================================================

st.markdown("---")
st.markdown("### 📈 절대 수준 (Level)")

# Combine balance sheet components
bs_data = {}
if 'fed_assets' in data_dict:
    bs_data['Fed Assets'] = data_dict['fed_assets'] / 1e12
if 'bank_credit' in data_dict:
    bs_data['Bank Credit'] = data_dict['bank_credit'] / 1e12
if 'm2' in data_dict:
    bs_data['M2'] = data_dict['m2'] / 1e12

if bs_data:
    fig = create_multi_line_chart(
        bs_data,
        title='대차대조표 구성요소 (조 달러)',
        normalize=False,
        height=450,
    )
    st.plotly_chart(fig, width="stretch")
else:
    st.info("대차대조표 데이터가 없습니다.")


# ============================================================================
# GROWTH RATE CHARTS
# ============================================================================

st.markdown("---")
st.markdown("### 📊 성장률")

tab1, tab2, tab3 = st.tabs(["YoY 성장률", "3M 연율화", "1M 변화"])

with tab1:
    growth_data = {}
    for name, key in [('Fed Assets', 'fed_assets'), ('Bank Credit', 'bank_credit'), ('M2', 'm2')]:
        if key in data_dict:
            growth_data[name] = calc_yoy(data_dict[key], periods=52)
    
    if growth_data:
        fig = create_multi_line_chart(
            growth_data,
            title='YoY 성장률 (%)',
            normalize=False,
            height=400,
        )
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, width="stretch")

with tab2:
    growth_data = {}
    for name, key in [('Fed Assets', 'fed_assets'), ('Bank Credit', 'bank_credit'), ('M2', 'm2')]:
        if key in data_dict:
            growth_data[name] = calc_3m_annualized(data_dict[key], periods_3m=13)
    
    if growth_data:
        fig = create_multi_line_chart(
            growth_data,
            title='3개월 연율화 성장률 (%)',
            normalize=False,
            height=400,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, width="stretch")

with tab3:
    growth_data = {}
    for name, key in [('Fed Assets', 'fed_assets'), ('Bank Credit', 'bank_credit'), ('M2', 'm2')]:
        if key in data_dict:
            growth_data[name] = calc_1m_change(data_dict[key], periods_1m=4)
    
    if growth_data:
        fig = create_multi_line_chart(
            growth_data,
            title='1개월 변화율 (%)',
            normalize=False,
            height=400,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, width="stretch")


# ============================================================================
# Z-SCORE ANALYSIS
# ============================================================================

st.markdown("---")
st.markdown("### 📐 Z-Score 분석")

col1, col2 = st.columns(2)

with col1:
    # Z-score time series
    zscore_data = {}
    for name, key in [('Fed Assets', 'fed_assets'), ('Bank Credit', 'bank_credit'), ('M2', 'm2')]:
        if key in data_dict:
            zscore_data[name] = calc_zscore(data_dict[key], window_years=3, periods_per_year=52)
    
    if zscore_data:
        fig = create_multi_line_chart(
            zscore_data,
            title='Z-Score (3년 윈도우)',
            normalize=False,
            height=350,
        )
        fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.5)
        fig.add_hline(y=-2, line_dash="dash", line_color="green", opacity=0.5)
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.3)
        st.plotly_chart(fig, width="stretch")

with col2:
    # Z-score heatmap
    if zscore_data:
        # Prepare data for heatmap
        zscore_df_list = []
        for name, series in zscore_data.items():
            if series is not None and len(series) > 0:
                temp_df = pd.DataFrame({
                    'date': series.index,
                    'indicator': name,
                    'zscore': series.values,
                })
                zscore_df_list.append(temp_df)
        
        if zscore_df_list:
            zscore_df = pd.concat(zscore_df_list, ignore_index=True)
            # Resample to weekly if too many points
            fig = create_zscore_heatmap(
                zscore_df,
                title='Z-Score 히트맵',
                height=350,
            )
            st.plotly_chart(fig, width="stretch")


# ============================================================================
# ACCELERATION (2ND DERIVATIVE)
# ============================================================================

st.markdown("---")
st.markdown("### 🚀 가속도 (2차 미분)")
st.markdown("*성장 속도가 빨라지고 있는가, 느려지고 있는가?*")

if 'bank_credit' in data_dict:
    credit = data_dict['bank_credit']
    
    # Calculate acceleration
    acc = calc_acceleration(credit, first_diff_periods=4, second_diff_periods=4)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        acc_df = pd.DataFrame({
            'date': acc.index,
            'value': acc.values / 1e9,  # Billions
            'indicator': '신용 가속도'
        })
        
        fig = create_timeseries_chart(
            acc_df,
            title='은행 신용 가속도 (10억 달러/주²)',
            date_col='date',
            value_col='value',
            height=350,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        latest_acc = acc.iloc[-1] if len(acc) > 0 else 0
        avg_acc = acc.iloc[-13:].mean() if len(acc) > 13 else 0  # 3 month average
        
        st.markdown("#### 현재 상태")
        
        if latest_acc > 0 and avg_acc > 0:
            st.success("🚀 **신용 확장 가속 중**")
            st.markdown("대차대조표가 점점 더 빠르게 확장되고 있습니다.")
        elif latest_acc < 0 and avg_acc < 0:
            st.error("🔻 **신용 확장 감속 중**")
            st.markdown("대차대조표 확장 속도가 줄어들고 있습니다.")
        elif latest_acc > 0:
            st.info("📈 **반등 중**")
            st.markdown("단기적으로 확장 속도가 회복되고 있습니다.")
        else:
            st.warning("📉 **일시 둔화**")
            st.markdown("단기적으로 확장 속도가 줄어들었습니다.")


# ============================================================================
# INFLECTION POINT DETECTION
# ============================================================================

st.markdown("---")
st.markdown("### 🔄 변곡점 탐지")

if 'bank_credit' in data_dict:
    credit = data_dict['bank_credit']
    growth = calc_yoy(credit, periods=52)
    inflection = detect_inflection(growth, lookback=13, sensitivity=1.0)
    
    # Filter to significant inflection points
    peaks = inflection[inflection == 1]
    troughs = inflection[inflection == -1]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**최근 고점 (Peak)**")
        if len(peaks) > 0:
            recent_peaks = peaks.tail(3)
            for date, _ in recent_peaks.items():
                val = growth.loc[date] if date in growth.index else None
                if val:
                    st.markdown(f"• {date.strftime('%Y-%m-%d')}: {val:.1f}%")
        else:
            st.markdown("최근 1년 내 유의미한 고점 없음")
    
    with col2:
        st.markdown("**최근 저점 (Trough)**")
        if len(troughs) > 0:
            recent_troughs = troughs.tail(3)
            for date, _ in recent_troughs.items():
                val = growth.loc[date] if date in growth.index else None
                if val:
                    st.markdown(f"• {date.strftime('%Y-%m-%d')}: {val:.1f}%")
        else:
            st.markdown("최근 1년 내 유의미한 저점 없음")


# ============================================================================
# INTERPRETATION
# ============================================================================

st.markdown("---")
st.markdown("### 💡 해석 가이드")

with st.expander("대차대조표 지표 해석 방법"):
    st.markdown("""
    #### Fed 자산 (Fed Total Assets)
    - 중앙은행의 대차대조표 규모
    - QE 시 확장, QT 시 수축
    - 시스템 유동성의 "원천"
    
    #### 은행 신용 (Bank Credit)
    - 상업은행이 창출한 신용 총량
    - 경제활동과 위험선호를 반영
    - 대차대조표 확장의 "전파" 채널
    
    #### M2 (광의통화)
    - 일반 경제주체가 보유한 화폐
    - 신용창출의 "결과"로 생성
    - 수요 측면의 유동성 지표
    
    #### 가속도 (2차 미분)
    - 양수: 성장 속도가 빨라짐 (확장 가속)
    - 음수: 성장 속도가 느려짐 (확장 감속 또는 수축 가속)
    - 변곡점에서 리스크 자산 전환점 발생 가능
    """)
