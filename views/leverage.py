"""
Leverage & Marginal Buyer Page
레버리지/한계 투자자 페이지
"""
import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.charts import create_timeseries_chart, create_multi_line_chart
from indicators.transforms import calc_zscore, calc_3m_annualized, calc_yoy
from components.styles import render_page_header, render_score_display





render_page_header(
    icon="⚡",
    title="Leverage & Marginal Buyer",
    subtitle="레버리지 축적과 한계 투자자 분석",
)


def render_leverage(data_dict, regime_result=None):
    # Get data from args instead of session state
    if not data_dict:
        st.warning('⚠️ 데이터가 없습니다.')
        return
    
    
    # Leverage Score
    def calculate_leverage_score(data):
        scores = []
        if 'bank_credit' in data:
            g = calc_3m_annualized(data['bank_credit'], 13).iloc[-1]
            scores.append(min(100, max(0, 30 + g * 4.5)))
        if 'hy_spread' in data and len(data['hy_spread']) > 10:
            s = data['hy_spread']
            pct = (s.iloc[-1] - s.min()) / (s.max() - s.min()) * 100
            scores.append(100 - pct)
        if 'vix' in data and len(data['vix']) > 10:
            v = data['vix']
            pct = (v.iloc[-1] - v.min()) / (v.max() - v.min()) * 100
            scores.append(100 - pct)
        return sum(scores) / len(scores) if scores else 50
    
    score = calculate_leverage_score(data_dict)
    render_score_display(
        score=score,
        max_score=100,
        label="레버리지 점수",
    )
    
    st.markdown("---")
    st.markdown("### 🏦 신용 성장")
    
    if 'bank_credit' in data_dict:
        credit = data_dict['bank_credit']
        growth_data = {'YoY': calc_yoy(credit, 52), '3M Ann': calc_3m_annualized(credit, 13)}
        fig = create_multi_line_chart(growth_data, title='은행 신용 성장률 (%)', height=400)
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, width="stretch")
    
    st.markdown("---")
    st.markdown("### 👤 한계 투자자 추정")
    characteristics = []
    if 'bank_credit' in data_dict:
        g = calc_3m_annualized(data_dict['bank_credit'], 13).iloc[-1]
        if g > 10: characteristics.append("레버리지 투자자 (높은 신용 성장)")
        elif g < 0: characteristics.append("디레버리지 투자자 (신용 축소)")
    if 'vix' in data_dict and data_dict['vix'].iloc[-1] < 15:
        characteristics.append("위험선호 투자자 (낮은 변동성)")
    elif 'vix' in data_dict and data_dict['vix'].iloc[-1] > 30:
        characteristics.append("위험회피 투자자 (높은 변동성)")
    
    for c in characteristics: st.markdown(f"• {c}")
    if not characteristics: st.info("특별한 투자자 유형 감지 없음")
    