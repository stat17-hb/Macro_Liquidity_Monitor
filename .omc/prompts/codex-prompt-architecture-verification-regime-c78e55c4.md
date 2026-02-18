---
provider: "codex"
agent_role: "architect"
model: "o4-mini"
files:
  - "c:\\Users\\k1190\\OneDrive\\01.investment\\Macro_Liquidity_Monitor\\indicators\\regime.py"
  - "c:\\Users\\k1190\\OneDrive\\01.investment\\Macro_Liquidity_Monitor\\app.py"
  - "c:\\Users\\k1190\\OneDrive\\01.investment\\Macro_Liquidity_Monitor\\components\\charts.py"
  - "c:\\Users\\k1190\\OneDrive\\01.investment\\Macro_Liquidity_Monitor\\pages\\1_Executive_Overview.py"
timestamp: "2026-02-18T10:13:21.152Z"
---

--- File: c:\Users\k1190\OneDrive\01.investment\Macro_Liquidity_Monitor\indicators\regime.py ---
"""
Regime classification module.
레짐 분류 모듈

4개 레짐을 점수로 분류:
- Expansion: 신용/대차대조표 성장(+), 스프레드 축소, 변동성 낮음
- Late-cycle: 신용 성장 지속, 밸류에이션 확장 > 이익/생산성 개선
- Contraction: 신용 성장 둔화/음전환, 스프레드 확대, 변동성 상승
- Stress: 변동성 급등 + 스프레드 급확대 + 위험자산 급락

각 레짐의 조건을 점수화(0~100)하고 가장 높은 레짐을 표시
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime, REGIME_DESCRIPTIONS
from .transforms import calc_zscore, calc_3m_annualized, calc_1m_change, calc_percentile


@dataclass
class RegimeScore:
    """Scores for each regime with explanations."""
    expansion: float
    late_cycle: float
    contraction: float
    stress: float
    
    def get_primary_regime(self) -> Regime:
        """Get the regime with highest score."""
        scores = {
            Regime.EXPANSION: self.expansion,
            Regime.LATE_CYCLE: self.late_cycle,
            Regime.CONTRACTION: self.contraction,
            Regime.STRESS: self.stress,
        }
        return max(scores, key=scores.get)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'Expansion': self.expansion,
            'Late-cycle': self.late_cycle,
            'Contraction': self.contraction,
            'Stress': self.stress,
        }


@dataclass
class RegimeResult:
    """Complete regime classification result."""
    primary_regime: Regime
    scores: RegimeScore
    explanations: List[str]
    confidence: float
    data_quality_warning: Optional[str] = None


class RegimeClassifier:
    """
    Regime classification engine.
    레짐 분류 엔진
    
    핵심 철학:
    - 유동성 = 대차대조표 확장/수축
    - 가격 = 한계 투자자의 신념
    - 목표 = 취약 지점 탐지
    """
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize classifier with optional config overrides."""
        self.config = config or {}
        
        # Default thresholds
        self.thresholds = {
            'credit_growth_expansion': 3.0,      # 3% YoY for expansion
            'credit_growth_contraction': 0.0,    # 0% for contraction
            'spread_zscore_tight': -0.5,         # Tight spreads
            'spread_zscore_wide': 1.0,           # Wide spreads
            'vix_percentile_low': 30,            # Low volatility
            'vix_percentile_high': 70,           # High volatility
            'vix_stress': 90,                    # Stress threshold
            'valuation_vs_earnings_gap': 0.5,    # Z-score gap for late-cycle
            'equity_drawdown': -5.0,             # 1M drawdown for stress
        }
        self.thresholds.update(self.config.get('thresholds', {}))
    
    def classify(
        self,
        data: Dict[str, pd.Series],
        as_of_date: Optional[pd.Timestamp] = None,
    ) -> RegimeResult:
        """
        Classify current market regime.
        현재 시장 레짐 분류
        
        Args:
            data: Dict of indicator name -> time series
                Required keys:
                - 'credit_growth' or 'bank_credit': Bank credit or similar
                - 'spread': Credit spread (HY or IG)
                - 'vix': Volatility index
                Optional keys:
                - 'equity': Equity index (for stress detection)
                - 'valuation_zscore': Valuation z-score
                - 'earnings_zscore': Earnings z-score
            as_of_date: Date to classify (default: latest)
            
        Returns:
            RegimeResult with classification and explanation
        """
        # Extract latest values
        metrics = self._extract_metrics(data, as_of_date)
        
        # Calculate scores for each regime
        scores = self._calculate_scores(metrics)
        
        # Generate explanations
        explanations = self._generate_explanations(metrics, scores)
        
        # Determine primary regime
        primary = scores.get_primary_regime()
        
        # Calculate confidence (gap between top 2 scores)
        sorted_scores = sorted(scores.to_dict().values(), reverse=True)
        confidence = (sorted_scores[0] - sorted_scores[1]) / 100 if len(sorted_scores) >= 2 else 1.0
        
        # Check data quality
        warning = self._check_data_quality(data)
        
        return RegimeResult(
            primary_regime=primary,
            scores=scores,
            explanations=explanations,
            confidence=confidence,
            data_quality_warning=warning,
        )
    
    def classify_history(
        self,
        data: Dict[str, pd.Series],
        lookback_years: int = 2,
        freq: str = 'ME',
    ) -> pd.DataFrame:
        """
        Classify regime for each historical date.
        과거 레짐 이력 분류

        Args:
            data: Dict of indicator name -> time series (same format as classify())
            lookback_years: Number of years of history to compute (default: 2)
            freq: Pandas frequency string for date sampling (default: 'ME' = month end)

        Returns:
            DataFrame indexed by date with columns:
                regime (str), confidence (float),
                expansion, late_cycle, contraction, stress (float 0-100)
        """
        # Find the date range from available data
        all_dates = []
        for series in data.values():
            if series is not None and len(series) > 0:
                all_dates.extend(series.index.tolist())
        if not all_dates:
            return pd.DataFrame()

        end_date = max(all_dates)
        start_date = end_date - pd.DateOffset(years=lookback_years)

        # Generate monthly sample dates
        sample_dates = pd.date_range(start=start_date, end=end_date, freq=freq)
        if len(sample_dates) == 0:
            return pd.DataFrame()

        records = []
        for date in sample_dates:
            # Slice each series up to this date
            sliced = {}
            for key, series in data.items():
                if series is not None and len(series) > 0:
                    s = series[series.index <= date]
                    if len(s) > 0:
                        sliced[key] = s

            if not sliced:
                continue

            try:
                metrics = self._extract_metrics(sliced, as_of_date=None)
                scores = self._calculate_scores(metrics)
                primary = scores.get_primary_regime()
                sorted_scores = sorted(scores.to_dict().values(), reverse=True)
                confidence = (
                    (sorted_scores[0] - sorted_scores[1]) / 100
                    if len(sorted_scores) >= 2
                    else 1.0
                )
                records.append({
                    'date': date,
                    'regime': primary.value,
                    'confidence': confidence,
                    'expansion': scores.expansion,
                    'late_cycle': scores.late_cycle,
                    'contraction': scores.contraction,
                    'stress': scores.stress,
                })
            except Exception:
                continue

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records).set_index('date')
        return df

    def _extract_metrics(
        self,
        data: Dict[str, pd.Series],
        as_of_date: Optional[pd.Timestamp],
    ) -> Dict[str, float]:
        """Extract relevant metrics from data."""
        metrics = {}
        
        # Helper to get latest value
        def get_latest(series, name):
            if series is None or len(series) == 0:
                return None
            if as_of_date:
                series = series[series.index <= as_of_date]
            return series.iloc[-1] if len(series) > 0 else None
        
        # Credit growth (3M annualized)
        credit = data.get('credit_growth')
        if credit is None:
            credit = data.get('bank_credit')
        if credit is not None and len(credit) > 63:
            credit_3m = calc_3m_annualized(credit, periods_3m=13)  # Weekly data
            metrics['credit_growth_3m'] = get_latest(credit_3m, 'credit_growth_3m')
        
        # Spread z-score
        spread = data.get('spread')
        if spread is None:
            spread = data.get('hy_spread')
        if spread is not None and len(spread) > 156:  # 3 years weekly
            spread_zscore = calc_zscore(spread, window_years=3, periods_per_year=52)
            metrics['spread_zscore'] = get_latest(spread_zscore, 'spread_zscore')
            metrics['spread_level'] = get_latest(spread, 'spread_level')
        
        # VIX percentile
        vix = data.get('vix')
        if vix is not None and len(vix) > 756:  # 3 years daily
            vix_pct = calc_percentile(vix, window_years=3, periods_per_year=252)
            metrics['vix_percentile'] = get_latest(vix_pct, 'vix_percentile')
            metrics['vix_level'] = get_latest(vix, 'vix_level')
        
        # Equity 1M return
        equity = data.get('equity')
        if equity is None:
            equity = data.get('sp500')
        if equity is not None and len(equity) > 21:
            equity_1m = calc_1m_change(equity)
            metrics['equity_1m_return'] = get_latest(equity_1m, 'equity_1m_return')
        
        # Valuation vs Earnings gap
        val_z = data.get('valuation_zscore')
        earn_z = data.get('earnings_zscore')
        if val_z is not None and earn_z is not None:
            gap = val_z - earn_z
            metrics['val_earn_gap'] = get_latest(gap, 'val_earn_gap')
        
        return metrics
    
    def _calculate_scores(self, metrics: Dict[str, float]) -> RegimeScore:
        """Calculate regime scores based on metrics."""
        # Initialize scores
        expansion = 0.0
        late_cycle = 0.0
        contraction = 0.0
        stress = 0.0
        
        # Credit growth component
        credit = metrics.get('credit_growth_3m')
        if credit is not None:
            if credit > self.thresholds['credit_growth_expansion']:
                expansion += 30
            elif credit < self.thresholds['credit_growth_contraction']:
                contraction += 30
            else:
                late_cycle += 15
                expansion += 15
        
        # Spread component
        spread_z = metrics.get('spread_zscore')
        if spread_z is not None:
            if spread_z < self.thresholds['spread_zscore_tight']:
                expansion += 25
            elif spread_z > self.thresholds['spread_zscore_wide']:
                contraction += 20
                stress += 15
            else:
                late_cycle += 15
        
        # VIX component
        vix_pct = metrics.get('vix_percentile')
        if vix_pct is not None:
            if vix_pct < self.thresholds['vix_percentile_low']:
                expansion += 25
            elif vix_pct > self.thresholds['vix_stress']:
                stress += 40
            elif vix_pct > self.thresholds['vix_percentile_high']:
                contraction += 20
                stress += 10
            else:
                late_cycle += 10
        
        # Equity drawdown (stress amplifier)
        equity_1m = metrics.get('equity_1m_return')
        if equity_1m is not None:
            if equity_1m < self.thresholds['equity_drawdown']:
                stress += 30
                contraction += 10
        
        # Valuation vs Earnings gap (late-cycle detector)
        gap = metrics.get('val_earn_gap')
        if gap is not None:
            if gap > self.thresholds['valuation_vs_earnings_gap']:
                late_cycle += 30
                expansion -= 10
        
        # Normalize to 0-100
        max_score = max(expansion, late_cycle, contraction, stress, 1)
        factor = 100 / max_score if max_score > 0 else 1
        
        return RegimeScore(
            expansion=min(100, max(0, expansion * factor * 0.7)),  # Scale down
            late_cycle=min(100, max(0, late_cycle * factor * 0.7)),
            contraction=min(100, max(0, contraction * factor * 0.7)),
            stress=min(100, max(0, stress * factor * 0.7)),
        )
    
    def _generate_explanations(
        self,
        metrics: Dict[str, float],
        scores: RegimeScore,
    ) -> List[str]:
        """Generate 3-line explanation for the regime classification."""
        explanations = []
        primary = scores.get_primary_regime()
        
        # Line 1: Primary driver
        credit = metrics.get('credit_growth_3m')
        if credit is not None:
            if primary == Regime.EXPANSION:
                explanations.append(f"신용 성장 지속 ({credit:.1f}% 3M 연율) - 대차대조표 확장 중")
            elif primary == Regime.CONTRACTION:
                explanations.append(f"신용 성장 둔화 ({credit:.1f}% 3M 연율) - 대차대조표 수축 압력")
            else:
                explanations.append(f"신용 성장 {credit:.1f}% (3M 연율)")
        
        # Line 2: Risk indicator status
        vix_pct = metrics.get('vix_percentile')
        spread_z = metrics.get('spread_zscore')
        if vix_pct is not None and spread_z is not None:
            if primary == Regime.STRESS:
                explanations.append(f"변동성 상위 {vix_pct:.0f}%ile, 스프레드 z={spread_z:.1f} - 담보 스트레스 신호")
            elif primary == Regime.EXPANSION:
                explanations.append(f"변동성 하위 {100-vix_pct:.0f}%ile, 스프레드 축소 - 위험선호 환경")
            else:
                explanations.append(f"변동성 {vix_pct:.0f}%ile, 스프레드 z-score {spread_z:.1f}")
        
        # Line 3: Forward-looking warning
        gap = metrics.get('val_earn_gap')
        if primary == Regime.LATE_CYCLE and gap is not None:
            explanations.append(f"밸류에이션이 이익을 {gap:.1f}σ 초과 - 신념 과열 경고")
        elif primary == Regime.EXPANSION:
            explanations.append("취약지점: 신용 과잉 확장 모니터링 필요")
        elif primary == Regime.CONTRACTION:
            explanations.append("취약지점: 스프레드 확대 → 담보 훼손 → 강제 매도 경로 주시")
        elif primary == Regime.STRESS:
            explanations.append("취약지점: 레버리지 포지션 청산, 유동성 경색 위험")
        else:
            explanations.append("현재 레짐 지속 가능성 평가 중")
        
        return explanations[:3]  # Ensure max 3 lines
    
    def _check_data_quality(self, data: Dict[str, pd.Series]) -> Optional[str]:
        """Check data quality and return warning if issues found."""
        warnings = []
        
        required = ['credit_growth', 'bank_credit', 'spread', 'hy_spread', 'vix']
        available = [k for k in required if k in data and data[k] is not None and len(data[k]) > 0]
        
        if len(available) < 3:
            warnings.append(f"필수 지표 부족: {3 - len(available)}개 누락")
        
        for name, series in data.items():
            if series is not None and len(series) > 0:
                latest_date = series.index[-1] if hasattr(series, 'index') else None
                if latest_date:
                    days_old = (pd.Timestamp.now() - pd.Timestamp(latest_date)).days
                    if days_old > 7:
                        warnings.append(f"{name} 데이터가 {days_old}일 전 기준")
        
        return '; '.join(warnings) if warnings else None


def calculate_regime_scores(data: Dict[str, pd.Series]) -> RegimeScore:
    """
    Calculate regime scores (convenience function).
    레짐 점수 계산 (편의 함수)
    """
    classifier = RegimeClassifier()
    result = classifier.classify(data)
    return result.scores


def determine_regime(data: Dict[str, pd.Series]) -> Tuple[Regime, List[str]]:
    """
    Determine current regime with explanation (convenience function).
    현재 레짐 판정 (편의 함수)
    
    Returns:
        Tuple of (regime, list of 3 explanation lines)
    """
    classifier = RegimeClassifier()
    result = classifier.classify(data)
    return result.primary_regime, result.explanations


--- File: c:\Users\k1190\OneDrive\01.investment\Macro_Liquidity_Monitor\app.py ---
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

# Compute regime history (monthly, 2-year lookback)
try:
    regime_history_df = classifier.classify_history(regime_data, lookback_years=2)
except Exception:
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


--- File: c:\Users\k1190\OneDrive\01.investment\Macro_Liquidity_Monitor\components\charts.py ---
"""
Chart components for visualization.
시각화 차트 컴포넌트

핵심 시각화:
- 타임시리즈 라인 차트
- Z-score 히트맵
- 밸류에이션 vs 이익 산점도
- 레짐 게이지
"""
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime, REGIME_COLORS

# Color palette for consistency - defined directly to avoid circular imports
COLORS = {
    'primary': '#3b82f6',      # Blue
    'secondary': '#8b5cf6',    # Purple
    'success': '#22c55e',      # Green
    'warning': '#f59e0b',      # Amber
    'danger': '#ef4444',       # Red
    'neutral': '#6b7280',      # Gray
    'bg_dark': '#1e293b',      # Dark background
    'bg_light': '#e2e8f0',     # Light background
    'grid': '#374151',         # Grid lines
}


def create_timeseries_chart(
    df: pd.DataFrame,
    title: str = '',
    date_col: str = 'date',
    value_col: str = 'value',
    indicator_col: Optional[str] = None,
    highlight_recent: bool = True,
    show_trend: bool = False,
    height: int = 400,
) -> go.Figure:
    """
    Create a single time series chart.
    단일 타임시리즈 차트 생성
    
    Args:
        df: DataFrame with date and value columns
        title: Chart title
        date_col: Name of date column
        value_col: Name of value column
        indicator_col: Name of indicator column (for multi-indicator data)
        highlight_recent: Whether to highlight recent 3 months
        show_trend: Whether to show trend line
        height: Chart height in pixels
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    # Handle multi-indicator data
    if indicator_col and indicator_col in df.columns:
        indicators = df[indicator_col].unique()
        for i, ind in enumerate(indicators):
            ind_df = df[df[indicator_col] == ind].sort_values(date_col)
            color = px.colors.qualitative.Set2[i % len(px.colors.qualitative.Set2)]
            fig.add_trace(go.Scatter(
                x=ind_df[date_col],
                y=ind_df[value_col],
                name=ind,
                mode='lines',
                line=dict(color=color, width=2),
            ))
    else:
        df = df.sort_values(date_col)
        fig.add_trace(go.Scatter(
            x=df[date_col],
            y=df[value_col],
            name=title or 'Value',
            mode='lines',
            line=dict(color=COLORS['primary'], width=2),
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.1)',
        ))
    
    # Highlight recent 3 months
    if highlight_recent and len(df) > 63:
        recent_start = df[date_col].iloc[-63]
        fig.add_vrect(
            x0=recent_start, x1=df[date_col].iloc[-1],
            fillcolor="rgba(59, 130, 246, 0.1)",
            layer="below",
            line_width=0,
        )
    
    # Update layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        height=height,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=True,
            gridcolor=COLORS['grid'],
            gridwidth=0.5,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=COLORS['grid'],
            gridwidth=0.5,
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
        ),
    )
    
    return fig


def create_multi_line_chart(
    data: Dict[str, pd.Series],
    title: str = '',
    normalize: bool = False,
    height: int = 400,
    secondary_y: Optional[List[str]] = None,
) -> go.Figure:
    """
    Create a multi-line chart with optional secondary y-axis.
    다중 라인 차트 생성
    
    Args:
        data: Dict of name -> time series
        title: Chart title
        normalize: Whether to normalize to 100 at start
        height: Chart height
        secondary_y: List of series names to put on secondary y-axis
        
    Returns:
        Plotly Figure
    """
    secondary_y = secondary_y or []
    has_secondary = len(secondary_y) > 0
    
    if has_secondary:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()
    
    colors = px.colors.qualitative.Set2
    
    for i, (name, series) in enumerate(data.items()):
        if series is None or len(series) == 0:
            continue
            
        values = series.copy()
        if normalize and len(values) > 0:
            values = (values / values.iloc[0]) * 100
        
        is_secondary = name in secondary_y
        color = colors[i % len(colors)]
        
        trace = go.Scatter(
            x=series.index if hasattr(series, 'index') else range(len(series)),
            y=values,
            name=name,
            mode='lines',
            line=dict(color=color, width=2, dash='dash' if is_secondary else 'solid'),
        )
        
        if has_secondary:
            fig.add_trace(trace, secondary_y=is_secondary)
        else:
            fig.add_trace(trace)
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        height=height,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    
    return fig


def create_zscore_heatmap(
    df: pd.DataFrame,
    date_col: str = 'date',
    indicator_col: str = 'indicator',
    zscore_col: str = 'zscore',
    title: str = 'Z-Score Heatmap',
    height: int = 400,
) -> go.Figure:
    """
    Create a z-score heatmap (indicators x time).
    Z-score 히트맵 생성
    
    Args:
        df: DataFrame in long format with date, indicator, zscore columns
        date_col: Name of date column
        indicator_col: Name of indicator column
        zscore_col: Name of zscore column
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly Figure
    """
    # Pivot to wide format
    pivot = df.pivot(index=indicator_col, columns=date_col, values=zscore_col)
    
    # Limit to recent dates if too many
    if pivot.shape[1] > 52:
        pivot = pivot.iloc[:, -52:]  # Last 52 periods
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=[
            [0.0, '#ef4444'],      # Red (negative)
            [0.25, '#f97316'],     # Orange
            [0.5, '#fafafa'],      # White (neutral)
            [0.75, '#22c55e'],     # Green
            [1.0, '#16a34a'],      # Dark green (positive)
        ],
        zmid=0,
        zmin=-3,
        zmax=3,
        colorbar=dict(
            title=dict(text='Z-Score', side='right'),
        ),
        hovertemplate='%{y}<br>%{x}<br>Z-Score: %{z:.2f}<extra></extra>',
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        height=height,
        margin=dict(l=120, r=40, t=60, b=60),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='Date'),
        yaxis=dict(title=''),
    )
    
    return fig


def create_valuation_scatter(
    valuation_change: pd.Series,
    earnings_change: pd.Series,
    title: str = '밸류에이션 vs 이익 변화 (신념 과열 탐지)',
    height: int = 400,
) -> go.Figure:
    """
    Create valuation vs earnings change scatter plot.
    밸류에이션 vs 이익 산점도 (신념 과열 탐지)
    
    Args:
        valuation_change: Valuation z-score change series
        earnings_change: Earnings z-score change series
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly Figure
    """
    # Align dates
    common_idx = valuation_change.index.intersection(earnings_change.index)
    val = valuation_change.loc[common_idx]
    earn = earnings_change.loc[common_idx]
    
    # Determine color based on gap (valuation - earnings)
    gap = val - earn
    colors = np.where(gap > 0.5, COLORS['danger'],
             np.where(gap > 0, COLORS['warning'], COLORS['success']))
    
    fig = go.Figure()
    
    # Add scatter points
    fig.add_trace(go.Scatter(
        x=earn,
        y=val,
        mode='markers',
        marker=dict(
            color=gap,
            colorscale='RdYlGn_r',
            size=8,
            colorbar=dict(title='Gap'),
            cmin=-1,
            cmax=1,
        ),
        text=[d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in common_idx],
        hovertemplate='Date: %{text}<br>Earnings: %{x:.2f}<br>Valuation: %{y:.2f}<extra></extra>',
    ))
    
    # Add diagonal line (where valuation = earnings change)
    max_val = max(abs(val.max()), abs(earn.max()), abs(val.min()), abs(earn.min())) or 1
    fig.add_trace(go.Scatter(
        x=[-max_val, max_val],
        y=[-max_val, max_val],
        mode='lines',
        line=dict(color='gray', dash='dash', width=1),
        showlegend=False,
        hoverinfo='skip',
    ))
    
    # Add overheating zone
    fig.add_shape(
        type='rect',
        x0=-max_val, x1=max_val,
        y0=0.5, y1=max_val,
        fillcolor='rgba(239, 68, 68, 0.1)',
        line=dict(width=0),
        layer='below',
    )
    
    fig.add_annotation(
        x=0, y=max_val * 0.8,
        text='⚠️ 신념 과열 영역',
        showarrow=False,
        font=dict(color=COLORS['danger']),
    )
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        height=height,
        margin=dict(l=60, r=40, t=60, b=60),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title='이익 추정 Z-Score 변화',
            zeroline=True,
            zerolinecolor='gray',
        ),
        yaxis=dict(
            title='밸류에이션 Z-Score 변화',
            zeroline=True,
            zerolinecolor='gray',
        ),
    )
    
    return fig


def create_regime_history_chart(
    regime_history_df: pd.DataFrame,
    height: int = 350,
) -> go.Figure:
    """
    Create a timeline chart showing regime history with confidence overlay.
    레짐 이력 타임라인 차트 (신뢰도 오버레이 포함)

    Args:
        regime_history_df: DataFrame indexed by date with columns:
            regime (str), confidence (float),
            expansion, late_cycle, contraction, stress
        height: Chart height in pixels

    Returns:
        Plotly Figure
    """
    if regime_history_df is None or regime_history_df.empty:
        return go.Figure()

    # Map regime strings to colors
    regime_color_map = {
        Regime.EXPANSION.value: REGIME_COLORS[Regime.EXPANSION],
        Regime.LATE_CYCLE.value: REGIME_COLORS[Regime.LATE_CYCLE],
        Regime.CONTRACTION.value: REGIME_COLORS[Regime.CONTRACTION],
        Regime.STRESS.value: REGIME_COLORS[Regime.STRESS],
    }

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    dates = regime_history_df.index.tolist()
    regimes = regime_history_df['regime'].tolist()

    # Group consecutive same-regime periods into bands
    bands = []
    if dates:
        band_start = dates[0]
        band_regime = regimes[0]
        for i in range(1, len(dates)):
            if regimes[i] != band_regime:
                bands.append((band_start, dates[i], band_regime))
                band_start = dates[i]
                band_regime = regimes[i]
        bands.append((band_start, dates[-1], band_regime))

    # Add colored background bands for each regime period
    for band_start, band_end, regime in bands:
        color = regime_color_map.get(regime, '#6b7280')
        fig.add_vrect(
            x0=band_start,
            x1=band_end,
            fillcolor=color,
            opacity=0.20,
            layer='below',
            line_width=0,
        )

    # Add confidence line on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=regime_history_df.index,
            y=regime_history_df['confidence'],
            name='신뢰도',
            mode='lines+markers',
            line=dict(color='#ffffff', width=2),
            marker=dict(size=5),
            hovertemplate='%{x|%Y-%m}<br>신뢰도: %{y:.0%}<extra></extra>',
        ),
        secondary_y=True,
    )

    # Add vertical dashed lines at transition points
    for i in range(1, len(regimes)):
        if regimes[i] != regimes[i - 1]:
            color = regime_color_map.get(regimes[i], '#6b7280')
            fig.add_vline(
                x=dates[i],
                line=dict(color=color, dash='dot', width=1),
            )
            fig.add_annotation(
                x=dates[i],
                y=1.05,
                yref='paper',
                text=regimes[i],
                showarrow=False,
                font=dict(color=color, size=10),
                xanchor='left',
            )

    fig.update_layout(
        title=dict(text='레짐 이력 (최근 2년)', font=dict(size=14)),
        height=height,
        margin=dict(l=40, r=60, t=50, b=40),
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor=COLORS['grid'], gridwidth=0.5),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig.update_yaxes(
        title_text='신뢰도',
        secondary_y=True,
        range=[0, 1.1],
        tickformat='.0%',
        showgrid=False,
    )
    fig.update_yaxes(
        title_text='',
        secondary_y=False,
        showticklabels=False,
        showgrid=False,
    )

    return fig


def create_regime_gauge(
    scores: Dict[str, float],
    primary_regime: str,
    height: int = 300,
) -> go.Figure:
    """
    Create a gauge chart showing regime scores.
    레짐 점수 게이지 차트
    
    Args:
        scores: Dict of regime name -> score (0-100)
        primary_regime: Name of the primary regime
        height: Chart height
        
    Returns:
        Plotly Figure
    """
    # Create horizontal bar chart for each regime
    regimes = ['Expansion', 'Late-cycle', 'Contraction', 'Stress']
    colors = [REGIME_COLORS[Regime.EXPANSION], REGIME_COLORS[Regime.LATE_CYCLE],
              REGIME_COLORS[Regime.CONTRACTION], REGIME_COLORS[Regime.STRESS]]
    
    values = [scores.get(r, 0) for r in regimes]
    
    fig = go.Figure()
    
    for i, (regime, value, color) in enumerate(zip(regimes, values, colors)):
        is_primary = regime == primary_regime
        fig.add_trace(go.Bar(
            y=[regime],
            x=[value],
            orientation='h',
            marker=dict(
                color=color,
                line=dict(color='white', width=2) if is_primary else dict(width=0),
            ),
            text=f'{value:.0f}',
            textposition='inside',
            name=regime,
            showlegend=False,
        ))
    
    fig.update_layout(
        title=dict(text='레짐 점수', font=dict(size=14)),
        height=height,
        margin=dict(l=100, r=40, t=40, b=20),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            range=[0, 100],
            title='Score',
            showgrid=True,
            gridcolor=COLORS['grid'],
        ),
        yaxis=dict(
            title='',
            categoryorder='array',
            categoryarray=regimes[::-1],
        ),
        barmode='overlay',
    )
    
    return fig


--- File: c:\Users\k1190\OneDrive\01.investment\Macro_Liquidity_Monitor\pages\1_Executive_Overview.py ---
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
from components.charts import create_timeseries_chart, create_regime_gauge, create_regime_history_chart
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
# REGIME HISTORY TIMELINE (레짐 이력)
# ============================================================================

st.markdown("---")
st.markdown("### 📅 레짐 이력")

regime_history_df = st.session_state.get('regime_history_df')

if regime_history_df is not None and not regime_history_df.empty:
    # Compute transition stats
    current_regime = regime_result.primary_regime.value
    hist_regimes = regime_history_df['regime'].tolist()
    hist_dates = regime_history_df.index.tolist()

    # Find last transition date and previous regime
    last_transition_date = None
    previous_regime = None
    for i in range(len(hist_regimes) - 1, 0, -1):
        if hist_regimes[i] != hist_regimes[i - 1]:
            last_transition_date = hist_dates[i]
            previous_regime = hist_regimes[i - 1]
            break

    # Days in current regime
    if last_transition_date is not None:
        days_in_regime = (pd.Timestamp.now() - last_transition_date).days
    else:
        # No transition found — in same regime for entire history
        days_in_regime = (pd.Timestamp.now() - hist_dates[0]).days if hist_dates else None

    # Display stats
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    with stat_col1:
        st.metric(
            "현재 레짐 유지 기간",
            f"{days_in_regime}일" if days_in_regime is not None else "—",
        )
    with stat_col2:
        st.metric(
            "이전 레짐",
            previous_regime if previous_regime else "—",
        )
    with stat_col3:
        st.metric(
            "마지막 전환",
            last_transition_date.strftime('%Y-%m-%d') if last_transition_date else "—",
        )

    fig_history = create_regime_history_chart(regime_history_df)
    st.plotly_chart(fig_history, use_container_width=True)
else:
    st.info("레짐 이력 데이터 없음")


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


[HEADLESS SESSION] You are running non-interactively in a headless pipeline. Produce your FULL, comprehensive analysis directly in your response. Do NOT ask for clarification or confirmation - work thoroughly with all provided context. Do NOT write brief acknowledgments - your response IS the deliverable.

# Architecture Verification: Regime History Timeline

## Task Completed
Added a Regime History Timeline visualization to a Streamlit-based macro liquidity monitoring dashboard.

## Changes Made (4 files)

### 1. indicators/regime.py — new method `classify_history()`
Added to `RegimeClassifier` class (after the existing `classify()` method at line 143):
```python
def classify_history(self, data, lookback_years=2, freq='ME') -> pd.DataFrame:
    # Generates monthly date range (last N years)
    # For each date: slices each series up to that date
    # Calls existing _extract_metrics() + _calculate_scores()
    # Returns DataFrame: date | regime | confidence | expansion | late_cycle | contraction | stress
```

### 2. app.py — cache regime history
After `regime_result = classifier.classify(regime_data)` (line 231):
```python
try:
    regime_history_df = classifier.classify_history(regime_data, lookback_years=2)
except Exception:
    regime_history_df = None
st.session_state['regime_history_df'] = regime_history_df
```

### 3. components/charts.py — new `create_regime_history_chart()`
```python
def create_regime_history_chart(regime_history_df, height=350) -> go.Figure:
    # Colored background bands for each consecutive regime period (add_vrect)
    # Confidence line on secondary y-axis
    # Dotted vertical lines + labels at transitions
    # Returns empty Figure if df is None/empty
```

### 4. pages/1_Executive_Overview.py — new section
- Imports `create_regime_history_chart` from components.charts
- Reads `st.session_state['regime_history_df']`
- Shows 3 stat metrics: days in current regime, previous regime, last transition date
- Renders history chart or graceful fallback info message

## Please verify:
1. Is `classify_history()` correctly reusing existing logic without duplication?
2. Are there any edge cases not handled (e.g., empty data, single regime across all history, NaN confidence values)?
3. Is the chart implementation correct (vrect bands, secondary y-axis, transition annotations)?
4. Does the Executive Overview page correctly compute transition stats from the history DataFrame?
5. Any potential bugs or issues with the implementation?

## Key Files to Check
- `indicators/regime.py` (lines 144-220)
- `app.py` (lines 233-243)
- `components/charts.py` (lines 365-465)
- `pages/1_Executive_Overview.py` (lines 299-351)
