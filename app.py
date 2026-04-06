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
                # Always load minimum set (Fed BS + all macro indicators for analysis)
                fred_data = fred.load_all_minimum_set()

                # If Fed BS checkbox is on, additionally load Discount Window (WLDWSL)
                if load_fed_balance_sheet and not fred_data.empty:
                    try:
                        dw_data = fred.load('WLDWSL')
                        if not dw_data.empty:
                            fred_data = pd.concat([fred_data, dw_data], ignore_index=True)
                    except Exception:
                        pass  # Discount Window is optional

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

# Compute regime history (monthly, 2-year lookback)
try:
    regime_history_df = classifier.classify_history(regime_data, lookback_years=2)
except Exception as e:
    import traceback
    traceback.print_exc()
    regime_history_df = None

# Store in session state
st.session_state['data'] = df
st.session_state['data_dict'] = data_dict
st.session_state['regime_result'] = regime_result
st.session_state['regime_history_df'] = regime_history_df

# Main page header
st.title("📊 유동성 모니터링 대시보드")
st.markdown("""
> **핵심 철학**: 유동성은 고정된 돈의 총량이 아닌, 금융시스템 대차대조표의 **확장과 수축**입니다.  
> 가격은 한계 투자자(marginal buyer)의 **신념**에서 결정됩니다.  
> 목표는 가격 설명이 아닌 **취약 지점 탐지**입니다.
""")

st.markdown("---")

# ============================================================================
# HERO SECTION (Overview & Regime Badge)
# ============================================================================

from components.cards import render_regime_badge
from components.reports import generate_daily_summary
from components.styles import render_info_box
from indicators.transforms import calc_3m_annualized, calc_zscore, calc_percentile, calc_1m_change

# 1. Regime Badge
render_regime_badge(
    regime=regime_result.primary_regime,
    explanations=regime_result.explanations,
    confidence=regime_result.confidence,
)

# 2. Extract metrics for summary
metrics = {}
if 'bank_credit' in data_dict:
    credit = data_dict['bank_credit']
    credit_3m = calc_3m_annualized(credit, periods_3m=13)
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

# 3. Generate and Render Summary
summary = generate_daily_summary(
    regime=regime_result.primary_regime,
    credit_growth=metrics.get('credit_growth_3m'),
    spread_zscore=metrics.get('spread_zscore'),
    vix_percentile=metrics.get('vix_percentile'),
    equity_1m=metrics.get('equity_1m'),
)
render_info_box(content=summary, title="📝 오늘의 한 줄 요약")

st.markdown("---")

# ============================================================================
# TABS NAVIGATION SYSTEM
# ============================================================================

tabs = st.tabs([
    "📈 Executive Overview",
    "🏦 대차대조표",
    "💎 담보/변동성",
    "🧠 신념/기대",
    "⚡ 레버리지",
    "🚨 알림",
    "🦅 QT 모니터링"
])

# Import views
from views.overview import render_overview
from views.balance_sheet import render_balance_sheet
from views.collateral import render_collateral
from views.marginal_belief import render_marginal_belief
from views.leverage import render_leverage
from views.alerts import render_alerts
from views.qt_monitoring import render_qt_monitoring

with tabs[0]:
    render_overview(data_dict, regime_result)
    
with tabs[1]:
    render_balance_sheet(data_dict, regime_result)
    
with tabs[2]:
    render_collateral(data_dict, regime_result)

with tabs[3]:
    render_marginal_belief(data_dict, regime_result)

with tabs[4]:
    render_leverage(data_dict, regime_result)

with tabs[5]:
    render_alerts(data_dict, regime_result)

with tabs[6]:
    render_qt_monitoring(data_dict, regime_result)

