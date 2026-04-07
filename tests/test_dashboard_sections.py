"""Smoke tests for redesigned dashboard sections."""
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime
from indicators.regime import RegimeResult, RegimeScore
from indicators.alerts import AlertConfig
from views.dashboard_sections import (
    DIAGNOSTIC_VIEW_OPTIONS,
    build_dashboard_metrics,
    build_view_context,
    render_action_center,
    render_command_center,
    render_diagnostics,
)


class DummyBlock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def form_submit_button(self, *args, **kwargs):
        return False


def _noop(*args, **kwargs):
    return None


def _dummy_columns(spec):
    count = spec if isinstance(spec, int) else len(spec)
    return [DummyBlock() for _ in range(count)]


def _sample_data_dict():
    weekly_dates = pd.date_range('2021-01-03', periods=220, freq='W')
    daily_dates = pd.date_range('2021-01-01', periods=900, freq='D')
    return {
        'bank_credit': pd.Series(1.0e13 + pd.Series(range(220), index=weekly_dates).values * 1.2e10, index=weekly_dates),
        'hy_spread': pd.Series(0.03 + pd.Series(range(220), index=weekly_dates).values * 0.00005, index=weekly_dates),
        'fed_assets': pd.Series(8.7e12 - pd.Series(range(220), index=weekly_dates).values * 8.0e9, index=weekly_dates),
        'm2': pd.Series(2.0e13 + pd.Series(range(220), index=weekly_dates).values * 9.0e9, index=weekly_dates),
        'pe_ratio': pd.Series(18.0 + pd.Series(range(220), index=weekly_dates).values * 0.02, index=weekly_dates),
        'forward_eps': pd.Series(200.0 + pd.Series(range(220), index=weekly_dates).values * 0.25, index=weekly_dates),
        'reserve_balances': pd.Series(3.1e12 - pd.Series(range(220), index=weekly_dates).values * 4.0e9, index=weekly_dates),
        'reverse_repo': pd.Series(6.0e11 + pd.Series(range(220), index=weekly_dates).values * 1.0e9, index=weekly_dates),
        'fed_lending': pd.Series(5.0e10 + pd.Series(range(220), index=weekly_dates).values * 1.0e8, index=weekly_dates),
        'real_yield': pd.Series(1.2 + pd.Series(range(220), index=weekly_dates).values * 0.002, index=weekly_dates),
        'breakeven': pd.Series(2.1 + pd.Series(range(220), index=weekly_dates).values * 0.001, index=weekly_dates),
        'vix': pd.Series(18.0 + pd.Series(range(900), index=daily_dates).values * 0.01, index=daily_dates),
        'sp500': pd.Series(4200.0 + pd.Series(range(900), index=daily_dates).values * 2.0, index=daily_dates),
    }


def _sample_regime_result():
    return RegimeResult(
        primary_regime=Regime.EXPANSION,
        scores=RegimeScore(expansion=72, late_cycle=48, contraction=22, stress=10),
        explanations=['신용 성장 유지', '스프레드 안정', '변동성 통제'],
        confidence=0.78,
        data_quality_warning=None,
    )


def _monkeypatch_streamlit(monkeypatch):
    for attr in ['warning', 'success', 'info', 'caption', 'markdown', 'write', 'plotly_chart', 'metric', 'title']:
        monkeypatch.setattr(st, attr, _noop)
    monkeypatch.setattr(st, 'columns', _dummy_columns)
    monkeypatch.setattr(st, 'expander', lambda *args, **kwargs: DummyBlock())
    monkeypatch.setattr(st, 'form', lambda *args, **kwargs: DummyBlock())
    monkeypatch.setattr(st, 'slider', lambda *args, **kwargs: kwargs.get('value', kwargs.get('min_value')))
    monkeypatch.setattr(st, 'rerun', _noop)


def test_build_view_context_reports_missing_critical_indicators():
    data_dict = {'vix': pd.Series([20.0], index=[pd.Timestamp('2024-01-01')])}

    context = build_view_context(data_dict, use_sample=True, fed_bs_enabled=False, custom_indicator_count=0)

    assert context['load_meta']['source_mode'] == '샘플 데이터'
    assert 'Commercial Bank Credit' in context['load_meta']['missing_critical_indicators']


def test_build_dashboard_metrics_extracts_core_metrics():
    metrics = build_dashboard_metrics(_sample_data_dict())

    assert metrics['credit_growth_3m'] is not None
    assert metrics['spread_zscore'] is not None
    assert metrics['vix_percentile'] is not None
    assert metrics['qt_pace'] is not None
    assert metrics['reserve_regime'] is not None


def test_redesigned_sections_render_without_exceptions(monkeypatch):
    _monkeypatch_streamlit(monkeypatch)
    st.session_state.clear()

    data_dict = _sample_data_dict()
    regime_result = _sample_regime_result()
    regime_history_df = pd.DataFrame({
        'regime': ['Expansion', 'Late-cycle', 'Expansion'],
        'confidence': [0.7, 0.6, 0.8],
        'expansion': [70, 50, 72],
        'late_cycle': [20, 60, 25],
        'contraction': [10, 20, 15],
        'stress': [5, 10, 8],
    }, index=pd.to_datetime(['2024-01-31', '2024-02-29', '2024-03-31']))

    context = build_view_context(data_dict, use_sample=False, fed_bs_enabled=True, custom_indicator_count=1)
    render_command_center(data_dict, regime_result, regime_history_df, context['load_meta'], AlertConfig())
    for diagnostic_view in DIAGNOSTIC_VIEW_OPTIONS:
        render_diagnostics(data_dict, regime_result, AlertConfig(), diagnostic_view)
    render_action_center(data_dict, regime_result)
