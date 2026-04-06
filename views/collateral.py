"""
Collateral & Haircuts Page
담보가치/증거금 환경 페이지

핵심 철학:
- 담보가치 상승 → 신용창출 촉진 경로
- 담보 스트레스: 변동성 급등 + 스프레드 확대 + 위험자산 급락의 동시 발생
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime
from components.charts import create_timeseries_chart, create_multi_line_chart
from components.cards import render_metric_card, render_alert_card
from indicators.transforms import (
    calc_zscore, 
    calc_1m_change, 
    calc_percentile,
)
from indicators.alerts import check_collateral_stress, AlertLevel
from components.styles import render_page_header






render_page_header(
    icon="💎",
    title="Collateral & Haircuts",
    subtitle="담보가치 환경과 담보 스트레스 모니터링",
    philosophy="**담보가치 상승 → 추가 신용창출 촉진 → 자산가격 상승 → 담보가치 재상승**의 선순환 / **담보가치 하락 → 마진콜 → 강제청산 → 가격 하락 → 담보가치 재하락**의 악순환",
)

# Get data

def render_collateral(data_dict, regime_result=None):
    # Get data from args instead of session state
    if not data_dict:
        st.warning('⚠️ 데이터가 없습니다.')
        return
    
    
    
    # ============================================================================
    # COLLATERAL STRESS INDICATOR
    # ============================================================================
    
    st.markdown("### 🚨 담보 스트레스 신호")
    
    # Check collateral stress
    alert = check_collateral_stress(data_dict)
    
    if alert:
        render_alert_card(
            level=alert.level,
            title=alert.title,
            message=alert.format_message(),
            additional_checks=alert.additional_checks,
        )
    else:
        st.success("✅ 현재 담보 스트레스 신호 없음")
    
    
    # ============================================================================
    # KEY METRICS
    # ============================================================================
    
    st.markdown("---")
    st.markdown("### 📊 주요 지표")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'vix' in data_dict:
            vix = data_dict['vix']
            latest = vix.iloc[-1] if len(vix) > 0 else 0
            pct = calc_percentile(vix, window_years=3).iloc[-1] if len(vix) > 756 else None
            
            st.metric(
                "VIX",
                f"{latest:.1f}",
                f"{pct:.0f}%ile" if pct else None,
                delta_color="inverse",
            )
    
    with col2:
        if 'hy_spread' in data_dict:
            spread = data_dict['hy_spread']
            latest = spread.iloc[-1] * 100 if len(spread) > 0 else 0  # bps
            pct = calc_percentile(spread, window_years=3, periods_per_year=52).iloc[-1] if len(spread) > 156 else None
            
            st.metric(
                "HY 스프레드",
                f"{latest:.0f} bps",
                f"{pct:.0f}%ile" if pct else None,
                delta_color="inverse",
            )
    
    with col3:
        if 'ig_spread' in data_dict:
            spread = data_dict['ig_spread']
            latest = spread.iloc[-1] * 100 if len(spread) > 0 else 0
            pct = calc_percentile(spread, window_years=3, periods_per_year=52).iloc[-1] if len(spread) > 156 else None
            
            st.metric(
                "IG 스프레드",
                f"{latest:.0f} bps",
                f"{pct:.0f}%ile" if pct else None,
                delta_color="inverse",
            )
    
    with col4:
        if 'sp500' in data_dict:
            sp = data_dict['sp500']
            ret_1m = calc_1m_change(sp).iloc[-1] if len(sp) > 21 else None
            
            st.metric(
                "S&P 500 (1M)",
                f"{ret_1m:+.1f}%" if ret_1m else "N/A",
                "",
            )
    
    
    # ============================================================================
    # VOLATILITY PANEL
    # ============================================================================
    
    st.markdown("---")
    st.markdown("### ⚡ 변동성")
    
    if 'vix' in data_dict:
        vix = data_dict['vix']
        
        tab1, tab2 = st.tabs(["VIX 추이", "VIX 백분위"])
        
        with tab1:
            vix_df = pd.DataFrame({
                'date': vix.index,
                'value': vix.values,
                'indicator': 'VIX'
            })
            fig = create_timeseries_chart(
                vix_df,
                title='VIX (CBOE 변동성 지수)',
                height=400,
            )
            # Add threshold lines
            fig.add_hline(y=20, line_dash="dash", line_color="green", opacity=0.5,
                         annotation_text="안정", annotation_position="right")
            fig.add_hline(y=30, line_dash="dash", line_color="orange", opacity=0.5,
                         annotation_text="경계", annotation_position="right")
            fig.add_hline(y=40, line_dash="dash", line_color="red", opacity=0.5,
                         annotation_text="스트레스", annotation_position="right")
            st.plotly_chart(fig, width="stretch")
        
        with tab2:
            vix_pct = calc_percentile(vix, window_years=3)
            pct_df = pd.DataFrame({
                'date': vix_pct.index,
                'value': vix_pct.values,
                'indicator': 'VIX Percentile'
            })
            fig = create_timeseries_chart(
                pct_df,
                title='VIX 백분위 (3년 롤링)',
                height=400,
            )
            fig.add_hline(y=75, line_dash="dash", line_color="orange", opacity=0.5)
            fig.add_hline(y=90, line_dash="dash", line_color="red", opacity=0.5)
            st.plotly_chart(fig, width="stretch")
    
    
    # ============================================================================
    # CREDIT SPREADS
    # ============================================================================
    
    st.markdown("---")
    st.markdown("### 📈 신용 스프레드")
    
    spread_data = {}
    if 'hy_spread' in data_dict:
        spread_data['HY Spread (%)'] = data_dict['hy_spread'] * 100
    if 'ig_spread' in data_dict:
        spread_data['IG Spread (%)'] = data_dict['ig_spread'] * 100
    
    if spread_data:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = create_multi_line_chart(
                spread_data,
                title='신용 스프레드 (%)',
                height=400,
            )
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            # Z-scores
            zscore_data = {}
            if 'hy_spread' in data_dict:
                zscore_data['HY Z-Score'] = calc_zscore(data_dict['hy_spread'], window_years=3, periods_per_year=52)
            if 'ig_spread' in data_dict:
                zscore_data['IG Z-Score'] = calc_zscore(data_dict['ig_spread'], window_years=3, periods_per_year=52)
            
            if zscore_data:
                fig = create_multi_line_chart(
                    zscore_data,
                    title='스프레드 Z-Score (3년)',
                    height=400,
                )
                fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.3)
                fig.add_hline(y=2, line_dash="dash", line_color="red", opacity=0.5)
                fig.add_hline(y=-2, line_dash="dash", line_color="green", opacity=0.5)
                st.plotly_chart(fig, width="stretch")
    
    
    # ============================================================================
    # COLLATERAL ASSETS (Equity as proxy)
    # ============================================================================
    
    st.markdown("---")
    st.markdown("### 📊 담보 자산 가치")
    
    if 'sp500' in data_dict:
        sp = data_dict['sp500']
        
        col1, col2 = st.columns(2)
        
        with col1:
            sp_df = pd.DataFrame({
                'date': sp.index,
                'value': sp.values,
                'indicator': 'S&P 500'
            })
            fig = create_timeseries_chart(
                sp_df,
                title='S&P 500 (주요 담보 자산)',
                height=350,
            )
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            # Monthly returns
            ret_1m = calc_1m_change(sp)
            ret_df = pd.DataFrame({
                'date': ret_1m.index,
                'value': ret_1m.values,
                'indicator': '1M Return'
            })
            fig = create_timeseries_chart(
                ret_df,
                title='S&P 500 1개월 수익률 (%)',
                height=350,
            )
            fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.3)
            fig.add_hline(y=-5, line_dash="dash", line_color="orange", opacity=0.5,
                         annotation_text="경계", annotation_position="right")
            fig.add_hline(y=-10, line_dash="dash", line_color="red", opacity=0.5,
                         annotation_text="스트레스", annotation_position="right")
            st.plotly_chart(fig, width="stretch")
    
    
    # ============================================================================
    # COMPOSITE STRESS INDEX
    # ============================================================================
    
    st.markdown("---")
    st.markdown("### 🎯 담보 스트레스 종합 지표")
    
    # Create composite stress index
    stress_components = []
    
    if 'vix' in data_dict:
        vix = data_dict['vix']
        if len(vix) > 100:
            vix_pct = calc_percentile(vix, window_years=1, periods_per_year=252)
            vix_pct = vix_pct.dropna()
            if len(vix_pct) > 0:
                stress_components.append(('VIX', vix_pct / 100))
    
    if 'hy_spread' in data_dict:
        spread = data_dict['hy_spread']
        if len(spread) > 20:
            spread_pct = calc_percentile(spread, window_years=1, periods_per_year=52)
            spread_pct = spread_pct.dropna()
            # Resample to daily for alignment
            spread_pct = spread_pct.resample('D').ffill()
            if len(spread_pct) > 0:
                stress_components.append(('Spread', spread_pct / 100))
    
    if 'sp500' in data_dict:
        sp = data_dict['sp500']
        if len(sp) > 21:
            ret_1m = calc_1m_change(sp)
            ret_1m = ret_1m.dropna()
            # Convert to stress: negative returns = positive stress
            equity_stress = (-ret_1m / 10).clip(-1, 1)  # Scale -10% to 1.0
            equity_stress = (equity_stress + 1) / 2  # Normalize to 0-1
            if len(equity_stress) > 0:
                stress_components.append(('Equity', equity_stress))
    
    if len(stress_components) >= 2:
        # Find common date range
        all_start = max(s.index.min() for _, s in stress_components)
        all_end = min(s.index.max() for _, s in stress_components)
        
        if all_start < all_end:
            # Use first component's index as base
            base_idx = stress_components[0][1].loc[all_start:all_end].index
            
            aligned_components = []
            for name, series in stress_components:
                clipped = series.loc[all_start:all_end]
                # Reindex to base
                reindexed = clipped.reindex(base_idx, method='ffill')
                aligned_components.append(reindexed)
            
            # Compute average
            composite = sum(aligned_components) / len(aligned_components)
            composite = composite.dropna()
            
            if len(composite) > 0:
                composite_df = pd.DataFrame({
                    'date': composite.index,
                    'value': composite.values * 100,
                    'indicator': 'Composite Stress'
                })
                
                fig = create_timeseries_chart(
                    composite_df,
                    title='담보 스트레스 종합 지수 (0-100)',
                    height=400,
                )
                fig.add_hline(y=50, line_dash="dash", line_color="orange", opacity=0.5,
                             annotation_text="경계", annotation_position="right")
                fig.add_hline(y=75, line_dash="dash", line_color="red", opacity=0.5,
                             annotation_text="고위험", annotation_position="right")
                st.plotly_chart(fig, width="stretch")
                
                # Latest reading
                latest_stress = composite.iloc[-1] * 100 if len(composite) > 0 else 0
                
                if latest_stress > 75:
                    st.error(f"🔴 **담보 스트레스 고위험**: {latest_stress:.0f}/100")
                elif latest_stress > 50:
                    st.warning(f"🟡 **담보 스트레스 경계**: {latest_stress:.0f}/100")
                else:
                    st.success(f"🟢 **담보 스트레스 안정**: {latest_stress:.0f}/100")
            else:
                st.info("데이터가 충분하지 않아 종합 지수를 계산할 수 없습니다.")
        else:
            st.info("데이터 기간이 겹치지 않아 종합 지수를 계산할 수 없습니다.")
    else:
        st.info("종합 지수 계산에 필요한 데이터가 부족합니다.")
    
    
    # ============================================================================
    # INTERPRETATION
    # ============================================================================
    
    st.markdown("---")
    
    with st.expander("💡 담보 스트레스 해석 가이드"):
        st.markdown("""
        #### 담보가치와 신용창출의 선순환/악순환
        
        **선순환 (담보가치 상승기)**
        1. 자산가격 상승 → 담보가치 증가
        2. 같은 담보로 더 많은 대출 가능
        3. 추가 유동성으로 자산 매수
        4. 자산가격 추가 상승
        
        **악순환 (담보가치 하락기)**
        1. 자산가격 하락 → 담보가치 감소
        2. 마진콜 발생 → 추가 담보 요구
        3. 담보 부족 시 강제 청산
        4. 강제 매도로 자산가격 추가 하락
        
        #### 스트레스 신호
        - **VIX > 30**: 변동성 급등, 헤지 비용 증가
        - **HY 스프레드 75%ile 이상**: 신용위험 프리미엄 확대
        - **주가 1M < -5%**: 담보가치 급락
        - **3개 신호 동시 발생**: 담보 스트레스 단계
        """)
    