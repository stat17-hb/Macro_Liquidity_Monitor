"""
Alerts & Playbook Page
알림/대응 페이지

핵심 기능:
- 룰 기반 신호등(녹/황/적) + 사용자 임계치 설정
- 레짐 전환 감지 시 요약과 행동 제안
- 신호는 "취약 지점"에 대한 경고로 문구 작성
"""
import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime, AlertLevel, REGIME_DESCRIPTIONS
from components.cards import render_alert_card
from indicators.alerts import AlertEngine, check_belief_overheating, check_collateral_stress, check_balance_sheet_contraction
from components.styles import render_page_header

st.set_page_config(page_title="알림 | 유동성 대시보드", page_icon="🚨", layout="wide")

# Apply global CSS
from components.styles import get_global_css
st.markdown(get_global_css(), unsafe_allow_html=True)

render_page_header(
    icon="🚨",
    title="Alerts & Playbook",
    subtitle="룰 기반 알림과 대응 가이드",
)

if 'data_dict' not in st.session_state:
    st.warning("⚠️ 먼저 메인 페이지에서 데이터를 로드해주세요.")
    st.stop()

data_dict = st.session_state['data_dict']
regime_result = st.session_state['regime_result']

# Check all alerts
engine = AlertEngine()
alerts = engine.check_all_alerts(data_dict)

st.markdown("---")
st.markdown("### 🚦 현재 알림")

if alerts:
    for alert in alerts:
        render_alert_card(alert.level, alert.title, alert.format_message(), alert.additional_checks)
else:
    st.success("✅ 현재 활성화된 알림 없음")

st.markdown("---")
st.markdown("### 📊 레짐 현황")
regime = regime_result.primary_regime
st.markdown(f"**현재 레짐**: {regime.value}")
st.markdown(f"**설명**: {REGIME_DESCRIPTIONS.get(regime, '')}")

for exp in regime_result.explanations: st.markdown(f"• {exp}")

st.markdown("---")
st.markdown("### 🎯 행동 제안 (Playbook)")

playbooks = {
    Regime.EXPANSION: [("위험자산 익스포저 유지/확대", "신용 확장기에는 위험자산이 유리"), ("레버리지 모니터링", "과도한 레버리지 축적 경계")],
    Regime.LATE_CYCLE: [("리스크 축소 검토", "신념이 실물을 앞서는 구간"), ("헤지 비용 점검", "변동성 상승 전 헤지 구축")],
    Regime.CONTRACTION: [("현금 비중 확대", "신용 수축기 유동성 확보"), ("스프레드 모니터링", "급확대 시 추가 하락 신호")],
    Regime.STRESS: [("위험 노출 최소화", "담보 스트레스 구간"), ("유동성 확보", "강제 청산 위험 대비")],
}

for action, reason in playbooks.get(regime, []):
    st.markdown(f"**{action}**: {reason}")

st.markdown("---")
st.markdown("### ⚙️ 알림 설정")

with st.expander("임계치 조정"):
    col1, col2 = st.columns(2)
    with col1:
        st.slider("VIX 스트레스 임계치 (percentile)", 50, 100, 90)
        st.slider("스프레드 스트레스 임계치 (percentile)", 50, 100, 75)
    with col2:
        st.slider("주가 1M 하락 경고 (%)", -20, 0, -5)
        st.slider("신용 성장 경고 (%)", -10, 20, 0)
    st.caption("※ 이 설정은 현재 세션에만 적용됩니다")
