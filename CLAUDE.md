# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Streamlit 기반 글로벌 유동성 모니터링 대시보드 - Fed 대차대조표, 신용 창출, QT 모니터링 분석 도구.

**핵심 철학**:
1. 유동성 = 대차대조표 확장/수축 (고정된 돈의 양 ✗)
2. 가격 = 한계 투자자(marginal buyer)의 신념 (돈의 양 ✗)
3. 목표 = 취약점 탐지 (가격 설명 ✗)

## Running the Dashboard

```bash
# Start dashboard (opens browser at http://localhost:8501)
streamlit run app.py

# Stop dashboard
Ctrl+C
```

**Enable Fed Balance Sheet Data**:
1. Sidebar → "Fed 대차대조표 포함" checkbox
2. Click "데이터 새로고침"

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_regime.py

# Run specific test
pytest tests/test_transforms.py::test_calc_yoy

# Validate Python syntax for all files
python -m py_compile app.py config.py loaders/*.py indicators/*.py pages/*.py
```

## Architecture

### Data Flow Pipeline

```
DataLoader (base.py)
    ↓
FREDLoader / YFinanceLoader / CSVLoader / SampleDataLoader
    ↓
load_all_data() in app.py (cached 6 hours)
    ↓
prepare_data_dict() → converts to dict of pd.Series
    ↓
RegimeClassifier / AlertEngine / Derived Metrics
    ↓
Streamlit Pages (visualization)
```

### Core Philosophy Implementation

**Fed Balance Sheet Identity** (핵심):
```
ΔReserves = ΔSOMA + ΔLending - ΔRRP - ΔTGA

Where:
- SOMA (WALCL): Fed total assets
- Reserves (WRESBAL): Bank reserves at Fed
- RRP (RRPONTSYD): Overnight reverse repo
- TGA (WTREGEN): Treasury General Account
- Lending (WLCFLPCL): Fed lending facilities
```

**Implemented in**:
- `config.py`: FED_BALANCE_SHEET_INDICATORS dict
- `indicators/derived_metrics.py`: verify_balance_sheet_identity()
- `pages/7_QT_Monitoring.py`: Full visualization

### Key Modules

**config.py** - Central configuration:
- `MINIMUM_INDICATORS`: 18 core indicators (Fed BS, spreads, equity, rates)
- `FED_BALANCE_SHEET_INDICATORS`: 6 Fed components
- `DERIVED_METRICS`: 7 calculated metrics definitions
- `Regime` enum: Expansion/Late-cycle/Contraction/Stress
- `ALERT_RULES`: 3 alert definitions

**loaders/** - Data acquisition layer:
- `base.py`: Abstract DataLoader with caching (6h TTL), schema validation
- `fred_loader.py`: FRED API wrapper
  - `load_all_minimum_set()`: 13 FRED indicators
  - `load_fed_balance_sheet()`: 6 Fed BS components
- `yfinance_loader.py`: Market data (VIX, S&P500)
- `sample_data.py`: Generates 5-year synthetic data (15 indicators, 6001 rows)

**indicators/** - Analysis layer:
- `transforms.py`: 10+ functions (YoY, 3M ann, z-score, acceleration, percentile)
- `regime.py`: RegimeClassifier (4 regimes, weighted scoring)
- `alerts.py`: AlertEngine (3 rules: belief overheating, collateral stress, BS contraction)
- `derived_metrics.py`: 7 Fed metrics (QT pace, reserve regime, money market stress, etc.)

**components/** - UI building blocks:
- `charts.py`: Plotly charts (timeseries, multi-line, z-score heatmap, regime gauge)
- `cards.py`: Streamlit cards (regime badge, metrics, alerts, vulnerabilities)
- `reports.py`: Report generators (daily summary, belief analysis)

**pages/** - Dashboard pages:
1. `1_Executive_Overview.py`: Master dashboard, regime classification
2. `2_Balance_Sheet.py`: Fed assets, bank credit, M2 tracking
3. `3_Collateral.py`: VIX, spreads, equity stress
4. `4_Marginal_Belief.py`: Valuation vs earnings gap
5. `5_Leverage.py`: Leverage scoring, marginal buyer identification
6. `6_Alerts.py`: Alert system with playbook
7. `7_QT_Monitoring.py`: **Fed QT tracking, reserve regime, money market stress**

### Data Schema

All loaders return standardized long-format DataFrame:
```python
{
    'date': pd.Timestamp,
    'value': float,
    'indicator': str  # e.g., 'Fed Total Assets', 'VIX'
}
```

**Converted to dict** in `app.py::prepare_data_dict()`:
```python
data_dict = {
    'fed_assets': pd.Series(indexed by date),
    'reserve_balances': pd.Series(...),
    'vix': pd.Series(...),
    # ... 15 total series
}
```

### Regime Classification Logic

**RegimeClassifier** (`indicators/regime.py`):

Scores 4 dimensions (0-100 each):
1. **Credit Growth** (3M annualized Bank Credit)
2. **Spread** (HY spread z-score, 3Y window)
3. **Volatility** (VIX percentile, 3Y window)
4. **Valuation vs Earnings** (PE z-score Δ - EPS z-score Δ)

**Output**:
- Primary regime (Expansion/Late-cycle/Contraction/Stress)
- 4 scores
- 3-line explanation
- Confidence (0-1)

**Thresholds** (in `config.py::REGIME_WEIGHTS`):
- credit_growth: 0.25
- spread: 0.25
- volatility: 0.20
- valuation_vs_earnings: 0.15

### Alert System

**3 Alert Rules** (`config.py::ALERT_RULES`):

1. **belief_overheating**: Valuation z-score Δ > Earnings z-score Δ + 0.5
2. **collateral_stress**: VIX >90p + Spread >75p + Equity 1M <-5%
3. **balance_sheet_contraction**: Bank Credit 3M ann <0 + Spread widening

**AlertEngine** (`indicators/alerts.py`):
- Returns: Level (Green/Yellow/Red), description, vulnerable path, additional checks

### Derived Metrics (Fed Balance Sheet)

**7 Functions** in `indicators/derived_metrics.py`:

1. `calculate_qt_pace(fed_assets)` → Monthly % change
2. `classify_reserve_regime(reserves, rrp)` → Abundant/Ample/Tight/Scarce
3. `verify_balance_sheet_identity(reserves, soma, lending, rrp, tga)` → LHS, RHS, residual
4. `detect_money_market_stress(rrp, reserves)` → Normal/Elevated/Stress + score
5. `calculate_fed_lending_stress(lending)` → Regime + percentile
6. `calculate_tga_reserve_drag(tga, reserves)` → TGA impact ratio
7. `calculate_reserve_demand_proxy(rrp, reserves)` → Crisis indicator (>50% = crisis)

**Reserve Regime Thresholds**:
- Abundant: >$2.5T (QT can continue)
- Ample: $1.5T-$2.5T (normal operations)
- Tight: $500B-$1.5T (stress signals)
- Scarce: <$500B (crisis risk)

## Important Implementation Patterns

### Transform Functions

**Always use indicator-specific period parameters**:
```python
from indicators.transforms import calc_yoy, calc_3m_annualized, calc_zscore

# Weekly data (52 periods/year)
yoy = calc_yoy(series, periods=52)
three_m = calc_3m_annualized(series, periods_3m=13)  # 52/4 = 13 weeks
zscore = calc_zscore(series, window_years=3, periods_per_year=52)

# Daily data (252 trading days/year)
yoy = calc_yoy(series, periods=252)
three_m = calc_3m_annualized(series, periods_3m=63)  # 252/4 = 63 days
```

### Adding New Indicators

1. **Define in config.py**:
```python
MINIMUM_INDICATORS['new_indicator'] = IndicatorConfig(
    name='Display Name',
    description='Korean description',
    source='fred',  # or 'yfinance', 'csv'
    ticker='FRED_TICKER',
    category='balance_sheet',  # or 'collateral', 'belief', 'leverage', 'spread'
    invert=False  # True if lower = more risk
)
```

2. **Add to loader** (`loaders/fred_loader.py` or `loaders/yfinance_loader.py`):
```python
# In load_all_minimum_set() or equivalent
tickers.append('NEW_TICKER')
```

3. **Map in app.py** (`prepare_data_dict()`):
```python
name_mapping = {
    'Display Name': 'new_indicator',  # snake_case key
    # ...
}
```

4. **Add sample data** (`loaders/sample_data.py`):
```python
# Generate synthetic data matching FRED ticker patterns
```

### Adding New Pages

Create `pages/N_PageName.py`:
```python
import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PAGE_CONFIG
from components.charts import create_timeseries_chart
from indicators.transforms import calc_yoy

st.set_page_config(**PAGE_CONFIG)

# Get data from session state
data_dict = st.session_state.get('data_dict', {})
regime_result = st.session_state.get('regime_result', {})

# Page content
st.title("Page Title")
# ... implementation
```

**Navigation**: Streamlit auto-discovers pages in `pages/` folder, sorted numerically.

### Caching Strategy

**app.py**:
```python
@st.cache_data(ttl=3600 * 6)  # 6 hours
def load_all_data(use_sample: bool = True):
    # Data loading logic
```

**DataLoader base class**:
```python
self._cache_ttl_hours = 6
self._cache[key] = df
self._cache_timestamps[key] = datetime.now()
```

**Clear cache**: Sidebar → "데이터 새로고침" button → `st.cache_data.clear()`

## Knowledge Base Philosophy (Do NOT modify)

The `knowledge_base/` folder contains proprietary research materials explaining the theoretical framework:
- Fed balance sheet mechanics
- QT termination signals
- Reserve regime classifications
- Money market stress indicators
- Marginal belief vs money quantity framework

**CRITICAL**:
- `knowledge_base/` is in `.gitignore` - never commit
- Do not modify or delete knowledge base files
- Use knowledge base as reference for understanding analysis framework

## Common Development Patterns

### Reading Indicator Data
```python
# Get from session state (in pages)
data_dict = st.session_state.get('data_dict', {})
fed_assets = data_dict.get('fed_assets')  # pd.Series
reserves = data_dict.get('reserve_balances')

# Check if available
if fed_assets is not None and not fed_assets.empty:
    # Use data
```

### Applying Transformations
```python
from indicators.transforms import calc_yoy, calc_zscore, calc_acceleration

# Chain transformations
yoy_growth = calc_yoy(bank_credit, periods=52)
zscore = calc_zscore(spread, window_years=3, periods_per_year=52)
accel = calc_acceleration(credit_growth, periods=13)
```

### Creating Charts
```python
from components.charts import create_timeseries_chart, create_multi_line_chart

# Single series
fig = create_timeseries_chart(
    series=fed_assets,
    title="Fed Total Assets",
    yaxis_title="Billions USD"
)
st.plotly_chart(fig, width="stretch")

# Multiple series
fig = create_multi_line_chart(
    data_dict={'Reserves': reserves, 'RRP': rrp},
    title="Fed Liquidity Components"
)
```

### Using Derived Metrics
```python
from indicators.derived_metrics import classify_reserve_regime, detect_money_market_stress

# Returns dict with regime, score, thresholds
regime_info = classify_reserve_regime(reserves, rrp)
st.metric("Reserve Regime", regime_info['regime'])

# Returns dict with stress_regime, score, change_1m
stress_info = detect_money_market_stress(rrp, reserves)
```

## Critical Notes

- **Period Parameters**: Always verify periods align with data frequency (weekly=52, daily=252)
- **Z-score Windows**: Default 3Y window, configurable via `window_years` parameter
- **Missing Data**: All transform functions handle NaN gracefully, return NaN for insufficient data
- **Date Alignment**: All series in `data_dict` are pd.Series with DatetimeIndex
- **Regime Confidence**: <0.7 = uncertain, use with caution
- **Alert Severity**: Green (ok), Yellow (watch), Red (action needed)

## Dependencies

See `requirements.txt`:
- streamlit >= 1.28.0
- pandas >= 2.0.0
- plotly >= 5.18.0
- yfinance >= 0.2.31
- fredapi >= 0.5.1
- scipy >= 1.11.0

**FRED API Key** (optional): Set in `config.py::AppConfig.fred_api_key` or use sample data.
