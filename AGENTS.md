# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository Overview

Streamlit-based macro liquidity monitoring dashboard analyzing Fed balance sheet mechanics, credit cycles, and market regime classification.

**Core Philosophy** (핵심 철학):
1. Liquidity = Balance sheet expansion/contraction (NOT fixed money supply)
2. Price = Marginal buyer's belief (NOT money quantity)
3. Goal = Vulnerability detection (NOT price explanation)

## Commands

```bash
# Run dashboard (http://localhost:8501)
streamlit run app.py

# Run all tests
pytest tests/

# Run specific test
pytest tests/test_transforms.py::test_calc_yoy

# Validate syntax
python -m py_compile app.py config.py loaders/*.py indicators/*.py pages/*.py
```

**Enable Fed Balance Sheet Data**: Sidebar → "Fed 대차대조표 포함" checkbox → "데이터 새로고침"

## Architecture

### Data Flow
```
DataLoader (loaders/base.py)
    ↓
FREDLoader / YFinanceLoader / SampleDataLoader
    ↓
load_all_data() in app.py (cached 6 hours)
    ↓
prepare_data_dict() → dict of pd.Series
    ↓
RegimeClassifier / AlertEngine / Derived Metrics
    ↓
Streamlit Pages (visualization)
```

### Key Modules

- **config.py**: Central configuration - `MINIMUM_INDICATORS` (18 indicators), `Regime` enum, `ALERT_RULES`
- **loaders/**: Data acquisition layer with 6-hour caching
  - `fred_loader.py`: FRED API (13 indicators + 6 Fed balance sheet components)
  - `yfinance_loader.py`: Market data (VIX, S&P500)
  - `sample_data.py`: 5-year synthetic data for testing
- **indicators/**: Analysis layer
  - `transforms.py`: YoY, 3M annualized, z-score, acceleration, percentile functions
  - `regime.py`: 4-regime classifier (Expansion/Late-cycle/Contraction/Stress)
  - `alerts.py`: 3 alert rules (belief overheating, collateral stress, BS contraction)
  - `derived_metrics.py`: Fed metrics (QT pace, reserve regime, money market stress)
- **components/**: Plotly charts and Streamlit cards
- **pages/**: 7 dashboard pages (auto-discovered by Streamlit, numbered 1-7)

### Data Schema

All loaders return long-format DataFrame:
```python
{'date': pd.Timestamp, 'value': float, 'indicator': str}
```

Converted to dict in `app.py::prepare_data_dict()`:
```python
data_dict = {'fed_assets': pd.Series, 'vix': pd.Series, ...}
```

Pages access data via `st.session_state['data_dict']`.

## Critical Implementation Patterns

### Transform Period Parameters
Always match periods to data frequency:
```python
# Weekly data (52 periods/year)
calc_yoy(series, periods=52)
calc_3m_annualized(series, periods_3m=13)
calc_zscore(series, window_years=3, periods_per_year=52)

# Daily data (252 trading days/year)
calc_yoy(series, periods=252)
calc_3m_annualized(series, periods_3m=63)
```

### Adding New Indicators
1. Define in `config.py::MINIMUM_INDICATORS`
2. Add to loader (`loaders/fred_loader.py` or `loaders/yfinance_loader.py`)
3. Map in `app.py::prepare_data_dict()` name_mapping dict
4. Add synthetic data in `loaders/sample_data.py`

### Adding New Pages
Create `pages/N_PageName.py`:
```python
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PAGE_CONFIG
st.set_page_config(**PAGE_CONFIG)

data_dict = st.session_state.get('data_dict', {})
regime_result = st.session_state.get('regime_result', {})
```

### Fed Balance Sheet Identity
Core equation: `ΔReserves = ΔSOMA + ΔLending - ΔRRP - ΔTGA`
- Implemented in `indicators/derived_metrics.py::verify_balance_sheet_identity()`
- Visualized in `pages/7_QT_Monitoring.py`

## Important Notes

- **FRED API Key**: Set via `FRED_API_KEY` environment variable or `.streamlit/secrets.toml`
- **knowledge_base/**: Contains proprietary research - do NOT modify or commit (in .gitignore)
- **Caching**: 6-hour TTL; clear via sidebar "데이터 새로고침" button
- **Missing data**: All transform functions handle NaN gracefully
- **Date alignment**: All series use DatetimeIndex
- **Regime confidence**: <0.7 = uncertain
