"""
Liquidity Monitoring Dashboard - Main Entry Point
유동성 모니터링 대시보드 - 메인 앱

핵심 철학:
1) 유동성 = 대차대조표 확장/수축 (고정된 돈의 총량 X)
2) 가격 = 한계 투자자(marginal buyer)의 신념
3) 목표 = 취약 지점 탐지 (가격 설명 X)
"""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PAGE_CONFIG, Regime, config
from loaders import SampleDataLoader, FREDLoader, YFinanceLoader, CSVLoader
from indicators import RegimeClassifier
from indicators.alerts import AlertEngine


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title=PAGE_CONFIG['page_title'],
    page_icon=PAGE_CONFIG['page_icon'],
    layout=PAGE_CONFIG['layout'],
    initial_sidebar_state=PAGE_CONFIG['initial_sidebar_state'],
)

# Custom CSS for high-contrast theme - imported from centralized styles
from components.styles import get_global_css
st.markdown(get_global_css(), unsafe_allow_html=True)



# ============================================================================
# DATA LOADING (Cached)
# ============================================================================

@st.cache_data(ttl=3600 * 6)  # Cache for 6 hours
def load_all_data(use_sample: bool = True, load_fed_balance_sheet: bool = False):
    """Load all data from sources."""
    if use_sample:
        loader = SampleDataLoader()
        return loader.load_all()
    else:
        # Try to load from real sources
        data_frames = []
        load_status = []

        fred = FREDLoader(api_key=config.fred_api_key)
        if fred.is_ready():
            try:
                if load_fed_balance_sheet:
                    # Load Fed balance sheet indicators
                    fred_data = fred.load_fed_balance_sheet()
                else:
                    # Load minimum set (original indicators)
                    fred_data = fred.load_all_minimum_set()
                
                if not fred_data.empty:
                    data_frames.append(fred_data)
                    indicator_count = len(fred_data['indicator'].unique())
                    load_status.append(f"FRED: {indicator_count}개 지표 로딩됨")
            except Exception as e:
                load_status.append(f"FRED: 로딩 실패 - {e}")
        else:
            load_status.append(f"FRED: {fred.get_status_message()}")

        yf = YFinanceLoader()
        if yf.is_available():
            try:
                yf_data = yf.load_all_minimum_set()
                if not yf_data.empty:
                    data_frames.append(yf_data)
                    indicator_count = len(yf_data['indicator'].unique())
                    load_status.append(f"yfinance: {indicator_count}개 지표 로딩됨")
            except Exception as e:
                load_status.append(f"yfinance: 로딩 실패 - {e}")

        # Show load status
        if load_status:
            for status in load_status:
                if "실패" in status or "필요" in status or "미설치" in status:
                    st.warning(status)
                else:
                    st.info(status)

        if data_frames:
            return pd.concat(data_frames, ignore_index=True)
        else:
            st.warning("실시간 데이터를 가져올 수 없어 샘플 데이터를 사용합니다.")
            return SampleDataLoader().load_all()


def prepare_data_dict(df: pd.DataFrame) -> dict:
    """Convert long-format DataFrame to dict of series."""
    data_dict = {}

    for indicator in df['indicator'].unique():
        ind_df = df[df['indicator'] == indicator].copy()
        ind_df = ind_df.sort_values('date')
        series = pd.Series(
            ind_df['value'].values,
            index=pd.DatetimeIndex(ind_df['date']),
            name=indicator
        )

        # Map to standard names
        name_mapping = {
            'Fed Total Assets': 'fed_assets',
            'Reserve Balances': 'reserve_balances',
            'Reverse Repo': 'reverse_repo',
            'TGA Balance': 'tga_balance',
            'Fed Lending': 'fed_lending',
            'Bank Credit': 'bank_credit',
            'M2': 'm2',
            'HY Spread': 'hy_spread',
            'IG Spread': 'ig_spread',
            'VIX': 'vix',
            'S&P 500': 'sp500',
            'Real Yield 10Y': 'real_yield',
            'Breakeven 10Y': 'breakeven',
            'Forward EPS': 'forward_eps',
            'PE Ratio': 'pe_ratio',
            # YFinance ETF proxies
            'HY ETF': 'hy_etf',
            'IG ETF': 'ig_etf',
            'TLT': 'tlt',
            '10Y Yield': 'treasury_10y',
        }

        key = name_mapping.get(indicator, indicator.lower().replace(' ', '_'))
        data_dict[key] = series

    # Add derived data
    if 'bank_credit' in data_dict:
        data_dict['credit'] = data_dict['bank_credit']
        data_dict['credit_growth'] = data_dict['bank_credit']

    if 'hy_spread' in data_dict:
        data_dict['spread'] = data_dict['hy_spread']
    elif 'hy_etf' in data_dict:
        # Use HY ETF as spread proxy (inverted - lower price = wider spread)
        data_dict['spread'] = data_dict['hy_etf']

    if 'sp500' in data_dict:
        data_dict['equity'] = data_dict['sp500']

    if 'pe_ratio' in data_dict:
        data_dict['valuation'] = data_dict['pe_ratio']

    if 'forward_eps' in data_dict:
        data_dict['earnings'] = data_dict['forward_eps']

    return data_dict


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.title("📊 유동성 대시보드")
    st.markdown("---")

    # Data source selection
    st.subheader("데이터 소스")
    use_sample = st.checkbox("샘플 데이터 사용", value=False,
                             help="체크 해제 시 실시간 데이터 로딩 시도")

    load_fed_balance_sheet = st.checkbox("Fed 대차대조표 포함",
                                         value=True,
                                         help="Reserve Balances, Reverse Repo, TGA, Fed Lending 포함")

    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    
    # Custom CSV upload
    st.subheader("사용자 데이터")
    uploaded_file = st.file_uploader(
        "CSV 파일 업로드",
        type=['csv'],
        help="날짜와 값 컬럼이 포함된 CSV 파일"
    )
    
    if uploaded_file:
        indicator_name = st.text_input("지표 이름", value="Custom")
        if st.button("데이터 추가"):
            try:
                csv_loader = CSVLoader()
                custom_df = csv_loader.load_from_upload(uploaded_file, indicator_name)
                st.success(f"{len(custom_df)} 행 로드됨")
            except Exception as e:
                st.error(f"로드 실패: {e}")
    
    st.markdown("---")
    
    # Info
    st.caption("대차대조표 관점의 유동성 분석")


# ============================================================================
# MAIN CONTENT
# ============================================================================

# Load data
df = load_all_data(use_sample=use_sample, load_fed_balance_sheet=load_fed_balance_sheet)
data_dict = prepare_data_dict(df)

# Get regime classification
classifier = RegimeClassifier()

# Prepare data for classification
regime_data = {
    'credit_growth': data_dict.get('credit_growth'),
    'spread': data_dict.get('spread'),
    'vix': data_dict.get('vix'),
    'equity': data_dict.get('equity'),
}

regime_result = classifier.classify(regime_data)

# Store in session state
st.session_state['data'] = df
st.session_state['data_dict'] = data_dict
st.session_state['regime_result'] = regime_result

# Main page header
st.title("📊 유동성 모니터링 대시보드")
st.markdown("""
> **핵심 철학**: 유동성은 고정된 돈의 총량이 아닌, 금융시스템 대차대조표의 **확장과 수축**입니다.  
> 가격은 한계 투자자(marginal buyer)의 **신념**에서 결정됩니다.  
> 목표는 가격 설명이 아닌 **취약 지점 탐지**입니다.
""")

st.markdown("---")

# Quick navigation
st.markdown("### 📍 페이지 탐색")
col1, col2, col3 = st.columns(3)

with col1:
    st.page_link("pages/1_Executive_Overview.py", label="📈 Executive Overview", icon="📈")
    st.page_link("pages/2_Balance_Sheet.py", label="🏦 대차대조표", icon="🏦")

with col2:
    st.page_link("pages/3_Collateral.py", label="💎 담보/변동성", icon="💎")
    st.page_link("pages/4_Marginal_Belief.py", label="🧠 신념/기대", icon="🧠")

with col3:
    st.page_link("pages/5_Leverage.py", label="⚡ 레버리지", icon="⚡")
    st.page_link("pages/6_Alerts.py", label="🚨 알림", icon="🚨")

st.markdown("---")

# Data summary
st.markdown("### 📊 데이터 현황")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("총 지표 수", len(df['indicator'].unique()))
with col2:
    if not df.empty:
        st.metric("데이터 시작", df['date'].min().strftime('%Y-%m-%d'))
with col3:
    if not df.empty:
        st.metric("데이터 종료", df['date'].max().strftime('%Y-%m-%d'))
with col4:
    st.metric("데이터 소스", "샘플" if use_sample else "실시간")

# Show available indicators
with st.expander("사용 가능한 지표 목록"):
    indicators = df['indicator'].unique().tolist()
    for i in range(0, len(indicators), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(indicators):
                col.markdown(f"• {indicators[i + j]}")
