"""
QT (Quantitative Tightening) Monitoring Page
양적긴축 모니터링 페이지

핵심 철학:
- Fed 대차대조표 항등식: Δ Reserves = Δ SOMA + Δ Lending - Δ Reverse Repo - Δ TGA
- QT 페이스 추적 (월간 자산 변화)
- 준비금 레짐 분류 (Abundant/Ample/Tight/Scarce)
- 자금시장 스트레스 신호 (역레포 수요, Fed 대출)
- QT 일시중단 예측 신호
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
    calc_percentile,
)
from components.styles import render_page_header


st.set_page_config(
    page_title="QT 모니터링 | 유동성 대시보드",
    page_icon="🔄",
    layout="wide",
)

# Apply global CSS
from components.styles import get_global_css
st.markdown(get_global_css(), unsafe_allow_html=True)

render_page_header(
    icon="🔄",
    title="Quantitative Tightening (QT) Monitoring",
    subtitle="Fed 양적긴축과 자금시장 유동성 추적",
    philosophy="**QT 핵심**: Fed 자산 감소(SOMA 축소) → 준비금 감소 → 자금시장 경색 신호(역레포 급증). **취약점**: 준비금 부족 시점을 조기 탐지하여 시장 스트레스 예측",
)

# Get data
if 'data_dict' not in st.session_state:
    st.warning("⚠️ 먼저 메인 페이지에서 데이터를 로드해주세요.")
    st.page_link("app.py", label="메인 페이지로 이동", icon="🏠")
    st.stop()

data_dict = st.session_state['data_dict']


# ============================================================================
# 1. FED BALANCE SHEET IDENTITY SECTION
# ============================================================================

st.markdown("### 📋 Fed 대차대조표 항등식 (Balance Sheet Identity)")
st.markdown("""
**항등식**: Δ Reserves = Δ SOMA + Δ Lending - Δ Reverse Repo - Δ TGA

- **SOMA Assets** (Δ SOMA): Fed 증권 보유 변화 → QT 페이스
- **Fed Lending** (Δ Lending): 신용창출 압박 시 증가
- **Reverse Repo** (Δ RRP): 유동성 흡수 메커니즘
- **TGA Balance** (Δ TGA): 재정 수정자, 높을수록 준비금 흡수
""")

# Create 5-component display
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if 'fed_assets' in data_dict:
        fed = data_dict['fed_assets']
        latest = fed.iloc[-1] / 1e12 if len(fed) > 0 else 0
        month_ago = fed.iloc[-5] / 1e12 if len(fed) > 5 else latest
        delta = latest - month_ago

        st.metric(
            "Fed Total Assets",
            f"${latest:.2f}T",
            f"{delta:+.2f}T (1M)",
            border=True,
        )

with col2:
    if 'reserve_balances' in data_dict:
        reserves = data_dict['reserve_balances']
        latest = reserves.iloc[-1] / 1e12 if len(reserves) > 0 else 0
        month_ago = reserves.iloc[-5] / 1e12 if len(reserves) > 5 else latest
        delta = latest - month_ago

        st.metric(
            "Reserve Balances",
            f"${latest:.2f}T",
            f"{delta:+.2f}T (1M)",
            border=True,
        )

with col3:
    if 'fed_lending' in data_dict:
        lending = data_dict['fed_lending']
        latest = lending.iloc[-1] / 1e9 if len(lending) > 0 else 0
        month_ago = lending.iloc[-5] / 1e9 if len(lending) > 5 else latest
        delta = latest - month_ago

        st.metric(
            "Fed Lending",
            f"${latest:.1f}B",
            f"{delta:+.1f}B (1M)",
            border=True,
        )

with col4:
    if 'reverse_repo' in data_dict:
        rrp = data_dict['reverse_repo']
        latest = rrp.iloc[-1] / 1e9 if len(rrp) > 0 else 0
        month_ago = rrp.iloc[-5] / 1e9 if len(rrp) > 5 else latest
        delta = latest - month_ago

        st.metric(
            "Reverse Repo (RRP)",
            f"${latest:.1f}B",
            f"{delta:+.1f}B (1M)",
            border=True,
        )

with col5:
    if 'tga_balance' in data_dict:
        tga = data_dict['tga_balance']
        latest = tga.iloc[-1] / 1e9 if len(tga) > 0 else 0
        month_ago = tga.iloc[-5] / 1e9 if len(tga) > 5 else latest
        delta = latest - month_ago

        st.metric(
            "TGA Balance",
            f"${latest:.1f}B",
            f"{delta:+.1f}B (1M)",
            border=True,
        )

# Identity verification
col1, col2 = st.columns([2, 1])

with col1:
    # Calculate each component of the identity
    st.markdown("**항등식 검증**")

    if all(k in data_dict for k in ['fed_assets', 'reserve_balances', 'fed_lending', 'reverse_repo', 'tga_balance']):
        fed = data_dict['fed_assets']
        reserves = data_dict['reserve_balances']
        lending = data_dict['fed_lending']
        rrp = data_dict['reverse_repo']
        tga = data_dict['tga_balance']

        # Monthly changes
        fed_chg = fed.iloc[-1] - fed.iloc[-5] if len(fed) > 5 else 0
        lending_chg = lending.iloc[-1] - lending.iloc[-5] if len(lending) > 5 else 0
        rrp_chg = rrp.iloc[-1] - rrp.iloc[-5] if len(rrp) > 5 else 0
        tga_chg = tga.iloc[-1] - tga.iloc[-5] if len(tga) > 5 else 0
        reserves_chg = reserves.iloc[-1] - reserves.iloc[-5] if len(reserves) > 5 else 0

        # Calculate identity components
        soma_effect = fed_chg / 1e9
        lending_effect = lending_chg / 1e9
        rrp_effect = -rrp_chg / 1e9  # Negative because RRP absorbs reserves
        tga_effect = tga_chg / 1e9  # Positive because higher TGA absorbs reserves

        calculated_reserve_change = soma_effect + lending_effect + rrp_effect - tga_effect
        actual_reserve_change = reserves_chg / 1e9
        identity_error = abs(calculated_reserve_change - actual_reserve_change)

        # Display as markdown table
        st.markdown(f"""
        | Component | 1M Change (B) | Effect on Reserves |
        |-----------|---------------|--------------------|
        | SOMA Assets | {soma_effect:+.1f}B | {soma_effect:+.1f}B |
        | Fed Lending | {lending_effect:+.1f}B | {lending_effect:+.1f}B |
        | Reverse Repo | {rrp_chg:+.1f}B | {rrp_effect:+.1f}B |
        | TGA Balance | {tga_chg:+.1f}B | {-tga_effect:+.1f}B |
        | **Total (Calculated)** | | **{calculated_reserve_change:+.1f}B** |
        | **Reserve Balances (Actual)** | | **{actual_reserve_change:+.1f}B** |
        | **Error** | | **{identity_error:.1f}B** |
        """)

with col2:
    if identity_error < 50:  # Less than 50B error is acceptable
        st.success("✅ 항등식 성립")
        st.markdown("*대차대조표 항등식이 부호 수준에서 검증됨*")
    else:
        st.warning("⚠️ 데이터 확인 필요")
        st.markdown("*일부 데이터 지연이 있을 수 있음*")


# ============================================================================
# 2. QT PACE TRACKING
# ============================================================================

st.markdown("---")
st.markdown("### 📊 QT 페이스 추적 (Pace of Tightening)")

tab1, tab2, tab3 = st.tabs(["Fed 자산 추이", "월간 QT 페이스", "QT 누적"])

with tab1:
    # Fed Total Assets level
    if 'fed_assets' in data_dict:
        fed = data_dict['fed_assets']
        fed_df = pd.DataFrame({
            'date': fed.index,
            'value': fed.values / 1e12,
            'indicator': 'Fed Total Assets'
        })

        fig = create_timeseries_chart(
            fed_df,
            title='Fed 총자산 (조 달러)',
            date_col='date',
            value_col='value',
            height=400,
        )

        # Add QE/QT regions
        fig.add_vrect(
            x0=pd.Timestamp('2020-03-01'), x1=pd.Timestamp('2021-12-31'),
            fillcolor="rgba(34, 197, 94, 0.1)",
            layer="below",
            line_width=0,
            annotation_text="QE Period",
            annotation_position="top left",
        )

        fig.add_vrect(
            x0=pd.Timestamp('2022-01-01'), x1=fed.index[-1],
            fillcolor="rgba(239, 68, 68, 0.1)",
            layer="below",
            line_width=0,
            annotation_text="QT Period",
            annotation_position="top left",
        )

        st.plotly_chart(fig, width="stretch")

with tab2:
    # Monthly QT pace
    if 'fed_assets' in data_dict:
        fed = data_dict['fed_assets']

        # Calculate monthly change
        monthly_change = fed.diff(periods=4)  # 4-week change (approximately monthly)
        monthly_pct = (fed.pct_change(periods=4) * 100)

        pace_df = pd.DataFrame({
            'date': monthly_change.index,
            'value': monthly_change.values / 1e9,
            'indicator': 'Monthly Change'
        })

        fig = create_timeseries_chart(
            pace_df,
            title='월간 QT 페이스 (10억 달러)',
            date_col='date',
            value_col='value',
            height=350,
        )

        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)

        # Add stress zones
        fig.add_hrect(
            y0=-100, y1=0,
            fillcolor="rgba(239, 68, 68, 0.1)",
            layer="below",
            line_width=0,
            annotation_text="Aggressive QT",
            annotation_position="right",
        )

        st.plotly_chart(fig, width="stretch")

        # QT pace metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            recent_pace = monthly_change.iloc[-4:].mean() / 1e9
            st.metric(
                "최근 4주 평균 QT 페이스",
                f"{recent_pace:+.1f}B",
                "음수 = 자산 감소"
            )

        with col2:
            # Detect tapering
            last_4_weeks_pace = monthly_change.iloc[-4:].mean()
            prev_4_weeks_pace = monthly_change.iloc[-8:-4].mean()
            tapering = last_4_weeks_pace > prev_4_weeks_pace  # Less negative = tapering

            if tapering and last_4_weeks_pace < 0:
                st.success("🟢 QT 감속 중")
                st.markdown(f"*QT 페이스가 완화되는 중*")
            elif last_4_weeks_pace < 0:
                st.error("🔴 QT 진행 중")
                st.markdown(f"*적극적인 자산 감소*")
            else:
                st.warning("🟡 QT 일시중단")
                st.markdown(f"*자산 증가 또는 안정화*")

        with col3:
            # QE/QT cumulative since peak
            peak_idx = fed.idxmax()
            peak_val = fed.max()
            current_val = fed.iloc[-1]
            cumulative_qt = (current_val - peak_val) / 1e12

            st.metric(
                "누적 QT (피크 이후)",
                f"{cumulative_qt:+.2f}T",
                f"{(cumulative_qt/peak_val)*100:+.1f}%"
            )

with tab3:
    # Cumulative QT visualization
    if 'fed_assets' in data_dict:
        fed = data_dict['fed_assets']
        peak_val = fed.max()
        cumulative_qt = fed - peak_val

        cumul_df = pd.DataFrame({
            'date': cumulative_qt.index,
            'value': cumulative_qt.values / 1e12,
            'indicator': 'Cumulative QT'
        })

        fig = create_timeseries_chart(
            cumul_df,
            title='누적 QT (피크 기준, 조 달러)',
            date_col='date',
            value_col='value',
            height=350,
        )

        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)

        st.plotly_chart(fig, width="stretch")


# ============================================================================
# 3. RESERVE REGIME CLASSIFICATION
# ============================================================================

st.markdown("---")
st.markdown("### 💾 준비금 레짐 분류 (Reserve Regime)")

col1, col2 = st.columns([2, 1])

with col1:
    if 'reserve_balances' in data_dict:
        reserves = data_dict['reserve_balances']
        reserves_t = reserves / 1e9  # Billions

        reserve_df = pd.DataFrame({
            'date': reserves.index,
            'value': reserves_t.values,
            'indicator': 'Reserve Balances'
        })

        fig = create_timeseries_chart(
            reserve_df,
            title='준비금 수준 (10억 달러)',
            date_col='date',
            value_col='value',
            height=350,
        )

        # Add regime zones
        fig.add_hrect(
            y0=2500, y1=3500,
            fillcolor="rgba(34, 197, 94, 0.1)",
            layer="below",
            line_width=1,
            line_color="green",
            annotation_text="Abundant",
            annotation_position="right",
        )

        fig.add_hrect(
            y0=1500, y1=2500,
            fillcolor="rgba(59, 130, 246, 0.1)",
            layer="below",
            line_width=1,
            line_color="blue",
            annotation_text="Ample",
            annotation_position="right",
        )

        fig.add_hrect(
            y0=500, y1=1500,
            fillcolor="rgba(245, 158, 11, 0.1)",
            layer="below",
            line_width=1,
            line_color="orange",
            annotation_text="Tight",
            annotation_position="right",
        )

        fig.add_hrect(
            y0=0, y1=500,
            fillcolor="rgba(239, 68, 68, 0.1)",
            layer="below",
            line_width=1,
            line_color="red",
            annotation_text="Scarce",
            annotation_position="right",
        )

        st.plotly_chart(fig, width="stretch")

with col2:
    if 'reserve_balances' in data_dict:
        reserves = data_dict['reserve_balances']
        latest = reserves.iloc[-1] / 1e9

        # Classify regime
        if latest >= 2500:
            regime_label = "Abundant"
            regime_color = "🟢"
            regime_desc = "준비금 과잉\n(QT 진행 여유)"
        elif latest >= 1500:
            regime_label = "Ample"
            regime_color = "🔵"
            regime_desc = "준비금 충분\n(정상 수준)"
        elif latest >= 500:
            regime_label = "Tight"
            regime_color = "🟡"
            regime_desc = "준비금 부족\n(스트레스 신호)"
        else:
            regime_label = "Scarce"
            regime_color = "🔴"
            regime_desc = "준비금 부족\n(경색 위험)"

        st.markdown(f"### {regime_color} {regime_label}")
        st.markdown(f"**${latest:.0f}B**")
        st.markdown(regime_desc)

        # Distance to threshold
        if latest < 2500:
            distance = 2500 - latest
            st.markdown(f"---")
            st.markdown(f"Abundant까지 **${distance:.0f}B** 필요")


# ============================================================================
# 4. MONEY MARKET STRESS INDICATORS
# ============================================================================

st.markdown("---")
st.markdown("### 🚨 자금시장 스트레스 지표 (Money Market Stress)")

tab1, tab2 = st.tabs(["역레포 수요", "Fed 대출 시설"])

with tab1:
    if 'reverse_repo' in data_dict:
        rrp = data_dict['reverse_repo']
        rrp_b = rrp / 1e9

        rrp_df = pd.DataFrame({
            'date': rrp.index,
            'value': rrp_b.values,
            'indicator': 'Reverse Repo'
        })

        fig = create_timeseries_chart(
            rrp_df,
            title='역레포 (Reverse Repo) 수요 (10억 달러)',
            date_col='date',
            value_col='value',
            height=350,
        )

        # Add stress zones
        fig.add_hrect(
            y0=0, y1=500,
            fillcolor="rgba(34, 197, 94, 0.1)",
            layer="below",
            annotation_text="Normal",
            annotation_position="right",
        )

        fig.add_hrect(
            y0=500, y1=1500,
            fillcolor="rgba(245, 158, 11, 0.1)",
            layer="below",
            annotation_text="Elevated",
            annotation_position="right",
        )

        fig.add_hrect(
            y0=1500, y1=2500,
            fillcolor="rgba(239, 68, 68, 0.1)",
            layer="below",
            annotation_text="Crisis",
            annotation_position="right",
        )

        st.plotly_chart(fig, width="stretch")

        # RRP metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            latest_rrp = rrp_b.iloc[-1]
            st.metric("현재 RRP 수요", f"${latest_rrp:.0f}B")

        with col2:
            # RRP spike detection
            recent_avg = rrp_b.iloc[-13:].mean()
            prev_avg = rrp_b.iloc[-26:-13].mean()
            spike = (recent_avg - prev_avg) / prev_avg * 100 if prev_avg > 0 else 0

            st.metric(
                "RRP 변화 (1M)",
                f"{spike:+.1f}%",
                "스트레스 신호" if spike > 10 else "정상"
            )

        with col3:
            # Distance to crisis
            crisis_threshold = 1500
            if latest_rrp < crisis_threshold:
                distance = crisis_threshold - latest_rrp
                st.metric(
                    "위기 수준까지",
                    f"${distance:.0f}B",
                    "여유 있음"
                )
            else:
                st.metric(
                    "위기 수준 초과",
                    f"${latest_rrp - crisis_threshold:+.0f}B",
                    "⚠️ 경고"
                )

with tab2:
    if 'fed_lending' in data_dict:
        lending = data_dict['fed_lending']
        lending_b = lending / 1e9

        lending_df = pd.DataFrame({
            'date': lending.index,
            'value': lending_b.values,
            'indicator': 'Fed Lending'
        })

        fig = create_timeseries_chart(
            lending_df,
            title='Fed 대출 시설 (10억 달러)',
            date_col='date',
            value_col='value',
            height=350,
        )

        # Add stress zones
        fig.add_hrect(
            y0=0, y1=100,
            fillcolor="rgba(34, 197, 94, 0.1)",
            layer="below",
            annotation_text="Normal",
            annotation_position="right",
        )

        fig.add_hrect(
            y0=100, y1=300,
            fillcolor="rgba(245, 158, 11, 0.1)",
            layer="below",
            annotation_text="Elevated",
            annotation_position="right",
        )

        fig.add_hrect(
            y0=300, y1=1000,
            fillcolor="rgba(239, 68, 68, 0.1)",
            layer="below",
            annotation_text="Crisis",
            annotation_position="right",
        )

        st.plotly_chart(fig, width="stretch")

        # Lending metrics
        col1, col2 = st.columns(2)

        with col1:
            latest_lending = lending_b.iloc[-1]
            st.metric("현재 Fed 대출", f"${latest_lending:.1f}B")

        with col2:
            # Lending spike
            if latest_lending > 100:
                st.error(f"🔴 Fed 대출 활성화")
                st.markdown(f"*은행 시스템 스트레스 신호*")
            elif latest_lending > 50:
                st.warning(f"🟡 Fed 대출 증가")
                st.markdown(f"*모니터링 필요*")
            else:
                st.success(f"🟢 Fed 대출 정상")
                st.markdown(f"*은행 시스템 안정*")


# ============================================================================
# 5. QT PAUSE PREDICTION SIGNALS
# ============================================================================

st.markdown("---")
st.markdown("### 🔮 QT 일시중단 예측 신호 (QT Pause Signals)")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**준비금 충분성 메트릭**")

    if 'reserve_balances' in data_dict and 'reverse_repo' in data_dict:
        reserves = data_dict['reserve_balances'].iloc[-1] / 1e9
        rrp = data_dict['reverse_repo'].iloc[-1] / 1e9

        # Reserve demand proxy (RRP as % of total liquidity)
        total_liquidity = reserves + rrp
        reserve_demand_pct = (rrp / total_liquidity * 100) if total_liquidity > 0 else 0

        st.metric(
            "RRP / 총 유동성",
            f"{reserve_demand_pct:.1f}%",
            "위기 임계값: >50%"
        )

        # Distance to sufficient reserves
        sufficient_threshold = 1500  # Historical 2019 crisis level
        if reserves < sufficient_threshold:
            distance = sufficient_threshold - reserves
            st.metric(
                "충분한 준비금까지",
                f"${distance:.0f}B",
                "증가 필요"
            )
        else:
            excess = reserves - sufficient_threshold
            st.metric(
                "초과 준비금",
                f"${excess:.0f}B",
                "QT 계속 가능"
            )

with col2:
    st.markdown("**2019 레포 위기와의 비교**")

    if 'reserve_balances' in data_dict:
        reserves = data_dict['reserve_balances']
        current = reserves.iloc[-1] / 1e9

        # 2019 repo crisis level (Sep 2019)
        crisis_2019_reserves = 1500  # Approx level

        st.metric(
            "현재 vs 2019",
            f"${current:.0f}B vs ${crisis_2019_reserves:.0f}B",
            f"{((current/crisis_2019_reserves - 1) * 100):+.0f}%"
        )

        if current < crisis_2019_reserves * 1.2:
            st.error("🔴 위기 수준 접근")
            st.markdown("*QT 일시중단 압박 증가*")
        elif current < crisis_2019_reserves * 1.5:
            st.warning("🟡 중간 수준")
            st.markdown("*QT 페이스 조정 가능성*")
        else:
            st.success("🟢 안전 여유")
            st.markdown("*QT 계속 진행 가능*")

with col3:
    st.markdown("**위험 신호 스캔**")

    warning_count = 0
    warnings = []

    # Signal 1: RRP > 1000B
    if 'reverse_repo' in data_dict:
        rrp_latest = data_dict['reverse_repo'].iloc[-1] / 1e9
        if rrp_latest > 1000:
            warning_count += 1
            warnings.append("⚠️ RRP > $1000B")

    # Signal 2: Reserves declining rapidly
    if 'reserve_balances' in data_dict:
        reserves = data_dict['reserve_balances']
        if len(reserves) > 4:
            recent_decline = (reserves.iloc[-1] - reserves.iloc[-4]) / 1e9
            if recent_decline < -100:
                warning_count += 1
                warnings.append("⚠️ 준비금 급격히 감소")

    # Signal 3: Fed Lending elevated
    if 'fed_lending' in data_dict:
        lending = data_dict['fed_lending'].iloc[-1] / 1e9
        if lending > 100:
            warning_count += 1
            warnings.append("⚠️ Fed 대출 증가")

    # Signal 4: VIX elevated
    if 'vix' in data_dict:
        vix = data_dict['vix'].iloc[-1]
        if vix > 25:
            warning_count += 1
            warnings.append("⚠️ VIX > 25")

    st.metric("활성 경고", warning_count, "개")

    if warning_count > 0:
        st.error(f"**위험 신호 {warning_count}개 감지**")
        for w in warnings:
            st.markdown(f"• {w}")
    else:
        st.success("**안전 상태**")
        st.markdown("* 현재 주요 경고 없음")


# ============================================================================
# INTERPRETATION & GUIDANCE
# ============================================================================

st.markdown("---")
st.markdown("### 💡 QT 모니터링 해석 가이드")

with st.expander("QT 프레임워크 상세 설명"):
    st.markdown("""
    #### Fed 대차대조표 항등식

    **Δ Reserves = Δ SOMA + Δ Lending - Δ Reverse Repo - Δ TGA**

    - **SOMA Assets (Δ SOMA)**: QT = Fed 증권 매각/만기 미갱신
    - **Fed Lending (Δ Lending)**: 금융 스트레스 시 증가
    - **Reverse Repo (Δ RRP)**: 민간 자금시장의 유동성 흡수
      - RRP 급증 = 준비금 부족 신호
      - 2019년 9월: $100B → $500B (3주 내)
    - **TGA Balance (Δ TGA)**: 정부 지출 시 증가 → 준비금 흡수

    #### 준비금 레짐 분류

    | 레짐 | 수준 | 의미 |
    |------|------|------|
    | **Abundant** | >$2.5T | QT 진행 여유 |
    | **Ample** | $1.5T-$2.5T | 정상 운영 수준 |
    | **Tight** | $500B-$1.5T | 스트레스 신호 |
    | **Scarce** | <$500B | 경색 위험 |

    #### QT 일시중단 신호 (2019년 9월 & 2023년 3월)

    1. **RRP 급증**: $500B → $2000B+ (4주 내)
    2. **준비금 급감**: 주간 $50B-$100B 감소
    3. **Fed 대출 활성화**: 할인창구 또는 SVB 긴급대출
    4. **금리 스파이크**: SOFR 10bps+ 점프

    #### 취약점 조기 탐지

    - **QT 페이스가 균일하면서 준비금이 $1.5T 근처**: QT 일시중단 논의 시작
    - **RRP 수요가 월 평균 $1T+**: 자금시장 불안 심화
    - **Fed 대출이 3개월 연속 증가**: 신용 경색 초기 신호

    #### 관찰 포인트

    1. **QT 페이스 추이**: 일정 → 감속 → 일시중단 순서로 진행
    2. **준비금과 RRP의 합**: 항상 감소 (QT 진행 중)
    3. **TGA 변동성**: 재정정책의 타이밍 신호
    """)

with st.expander("2019년 9월 Repo Crisis vs 2023년 은행위기 비교"):
    st.markdown("""
    #### 2019년 9월 Repo Crisis

    - **Trigger**: Fed 잔액 정책 변경 (QT → QE 전환)
    - **Evidence**:
      - RRP: $0B → $500B+ (3주)
      - Reserves: $1.7T → $1.5T (유지)
      - SOFR: 2% → 10%+ (스파이크)
    - **Response**: Fed QE 재개, 즉시 대출 공급
    - **Duration**: 약 2개월로 진정

    #### 2023년 3월 은행위기 (SVB Collapse)

    - **Trigger**: 금리 급상승 → 은행 자산 평가손 → 예금 인출
    - **Evidence**:
      - RRP: 유지 높은 수준 ($2T+)
      - Reserves: 안정적 ($3T+)
      - Fed 대출: BTFP 조성 ($300B)
    - **Response**: Fed 긴급 유동성 공급
    - **Duration**: 2주 내 진정

    #### 차이점

    - **2019**: 준비금 부족 → 자금시장 경색
    - **2023**: 은행 신용 부족 → 예금 인출
    - **공통점**: 둘 다 Fed의 적극적 개입 필요
    """)

st.markdown("---")

with st.expander("QT 모니터링 체크리스트"):
    st.markdown("""
    ### 주간 모니터링 체크리스트

    #### 매주 확인
    - [ ] Fed 자산 추이 (WALCL)
    - [ ] 준비금 수준 (WRESBAL)
    - [ ] RRP 수요 (RRPONTSYD)
    - [ ] Fed 대출 (WLCFLPCL)
    - [ ] TGA 잔액 (WTREGEN)

    #### 월간 분석
    - [ ] QT 페이스 (월간 자산 변화)
    - [ ] 준비금 레짐 (Abundant vs Ample)
    - [ ] RRP/준비금 비율 추이
    - [ ] Fed 대출 시설 사용률

    #### 위험 신호
    - [ ] RRP 1000억 이상 주간 증가
    - [ ] 준비금 주간 100억 이상 감소
    - [ ] Fed 대출 100억 이상
    - [ ] SOFR ±10bps 변동
    - [ ] VIX > 30

    #### 의사결정 포인트
    - [ ] 준비금 < $1.5T: QT 일시중단 논의 시작
    - [ ] RRP > $1.5T: 자금시장 경색 신호
    - [ ] Fed 대출 > $300B: 신용 위기 단계
    """)
