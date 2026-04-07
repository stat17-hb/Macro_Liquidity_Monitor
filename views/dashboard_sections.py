"""
Top-level dashboard sections for the redesigned app shell.
"""
from dataclasses import asdict
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MINIMUM_INDICATORS, REGIME_DESCRIPTIONS, Regime
from components.cards import render_alert_card, render_vulnerability_card
from components.charts import (
    create_multi_line_chart,
    create_regime_gauge,
    create_regime_history_chart,
    create_timeseries_chart,
    create_valuation_scatter,
)
from components.dashboard_ui import (
    render_action_list,
    render_headline_card,
    render_kpi_strip,
    render_signal_panel,
    render_status_bar,
)
from components.reports import (
    generate_belief_analysis,
    generate_daily_summary,
    generate_fundamental_check,
    generate_vulnerability_report,
    generate_watch_next,
    generate_what_changed,
)
from indicators.alerts import (
    AlertConfig,
    AlertEngine,
    check_belief_overheating,
    check_collateral_stress,
)
from indicators.derived_metrics import (
    calculate_fed_lending_stress,
    calculate_qt_pace,
    classify_reserve_regime,
    detect_money_market_stress,
)
from indicators.transforms import (
    calc_1m_change,
    calc_3m_annualized,
    calc_percentile,
    calc_yoy,
    calc_zscore,
    calc_zscore_change,
)

PRIMARY_SECTION_OPTIONS = ['Command Center', 'Diagnostics', 'Action Center']
DIAGNOSTIC_VIEW_OPTIONS = ['Liquidity Engine', 'Collateral Stress', 'Belief & Leverage', 'QT Monitor']

FRAMEWORK_MARKDOWN = """
### Framework

- **유동성**: 돈의 양이 아니라 대차대조표 확장과 수축으로 읽습니다.
- **가격**: 한계 투자자의 신념과 펀딩 여건이 가격을 움직입니다.
- **목표**: 가격 설명보다 취약 지점과 수축 경로를 조기에 탐지합니다.

이 앱은 `요약 → 진단 → 실행` 흐름으로 구성되어 있습니다.
"""

PLAYBOOKS = {
    Regime.EXPANSION: [
        "리스크 온 포지션은 유지하되 스프레드 반전 여부를 매주 점검합니다.",
        "레버리지 확장이 실적 개선을 앞서지 않는지 확인합니다.",
        "Fed 자산 축소가 재가속되면 성장주 듀레이션 리스크를 낮춥니다.",
    ],
    Regime.LATE_CYCLE: [
        "밸류에이션 익스포저를 줄이고 실적 확인 전 추격 매수를 피합니다.",
        "크레딧 스프레드와 변동성이 동시에 악화되는지 먼저 확인합니다.",
        "낙관 시나리오보다 자금조달 경색 경로를 우선 점검합니다.",
    ],
    Regime.CONTRACTION: [
        "신용 둔화와 스프레드 확대가 이어지면 방어적 포지션 비중을 높입니다.",
        "QT, 준비금, RRP 동학을 함께 보며 유동성 압박의 근원을 확인합니다.",
        "낙폭보다 담보 품질 저하와 펀딩 비용 상승을 우선 모니터링합니다.",
    ],
    Regime.STRESS: [
        "담보가치 훼손과 강제 청산 신호가 번지는지 즉시 확인합니다.",
        "유동성 좋은 자산 중심으로 리스크를 재정렬하고 레버리지를 줄입니다.",
        "Fed 대출 활성화와 QT 완화 신호가 나오는지 빠르게 추적합니다.",
    ],
}


def _latest(series: Optional[pd.Series]) -> Optional[float]:
    if series is None or len(series) == 0:
        return None
    value = series.iloc[-1]
    if pd.isna(value):
        return None
    return float(value)


def _safe_percent_rank(value: Optional[float]) -> str:
    return f"{value:.0f}%ile" if value is not None else "—"


def _build_alert_config_from_session() -> AlertConfig:
    stored = st.session_state.get('alert_config')
    if isinstance(stored, dict):
        return AlertConfig(**stored)
    if isinstance(stored, AlertConfig):
        return stored
    return AlertConfig()


def _store_alert_config(config: AlertConfig) -> None:
    st.session_state['alert_config'] = asdict(config)


def _ensure_alert_form_state() -> None:
    defaults = asdict(_build_alert_config_from_session())
    for key, value in defaults.items():
        session_key = f"alert_form_{key}"
        if session_key not in st.session_state:
            st.session_state[session_key] = value


def build_dashboard_metrics(data_dict: Dict[str, pd.Series]) -> Dict[str, Optional[float]]:
    """Compute the common metric set used across the redesigned sections."""
    metrics: Dict[str, Optional[float]] = {
        'credit_growth_3m': None,
        'spread_zscore': None,
        'vix_percentile': None,
        'equity_1m': None,
        'pe_zscore': None,
        'eps_growth': None,
        'real_yield': None,
        'breakeven': None,
        'qt_pace': None,
        'reserve_regime': None,
        'money_market_stress': None,
        'pe_eps_gap': None,
    }

    if 'bank_credit' in data_dict:
        credit = data_dict['bank_credit']
        metrics['credit_growth_3m'] = _latest(calc_3m_annualized(credit, periods_3m=13))

    if 'hy_spread' in data_dict:
        spread = data_dict['hy_spread']
        metrics['spread_zscore'] = _latest(calc_zscore(spread, window_years=3, periods_per_year=52))

    if 'vix' in data_dict:
        vix = data_dict['vix']
        metrics['vix_percentile'] = _latest(calc_percentile(vix, window_years=3, periods_per_year=252))

    if 'sp500' in data_dict:
        equity = data_dict['sp500']
        metrics['equity_1m'] = _latest(calc_1m_change(equity))

    if 'pe_ratio' in data_dict:
        pe = data_dict['pe_ratio']
        metrics['pe_zscore'] = _latest(calc_zscore(pe, window_years=3, periods_per_year=52))

    if 'forward_eps' in data_dict:
        eps = data_dict['forward_eps']
        latest_eps = _latest(calc_1m_change(eps))
        metrics['eps_growth'] = latest_eps * 12 if latest_eps is not None else None
        if 'pe_ratio' in data_dict:
            pe_z = calc_zscore(data_dict['pe_ratio'], window_years=3, periods_per_year=52)
            eps_z = calc_zscore(eps, window_years=3, periods_per_year=52)
            common_idx = pe_z.index.intersection(eps_z.index)
            if len(common_idx) > 0:
                metrics['pe_eps_gap'] = _latest(pe_z.loc[common_idx] - eps_z.loc[common_idx])

    if 'real_yield' in data_dict:
        metrics['real_yield'] = _latest(data_dict['real_yield'])
    if 'breakeven' in data_dict:
        metrics['breakeven'] = _latest(data_dict['breakeven'])
    if 'fed_assets' in data_dict:
        metrics['qt_pace'] = _latest(calculate_qt_pace(data_dict['fed_assets'], periods_1m=4))
    if 'reserve_balances' in data_dict:
        reserve_regime = classify_reserve_regime(
            data_dict['reserve_balances'] / 1e9,
            reverse_repo=(data_dict.get('reverse_repo') / 1e9) if 'reverse_repo' in data_dict else None,
        )
        metrics['reserve_regime'] = reserve_regime.iloc[-1] if len(reserve_regime) > 0 else None
    if 'reverse_repo' in data_dict:
        mm_stress = detect_money_market_stress(data_dict['reverse_repo'] / 1e9)
        metrics['money_market_stress'] = _latest(mm_stress['stress_score'])

    return metrics


def _active_alerts(data_dict: Dict[str, pd.Series], alert_config: AlertConfig) -> List:
    return AlertEngine(alert_config).check_all_alerts(data_dict)


def _build_load_meta(
    data_dict: Dict[str, pd.Series],
    use_sample: bool,
    fed_bs_enabled: bool,
    custom_indicator_count: int,
) -> Dict[str, object]:
    latest_dates = []
    for series in data_dict.values():
        if series is not None and len(series) > 0:
            latest_dates.append(pd.to_datetime(series.index.max()))

    missing = []
    for key in ['bank_credit', 'hy_spread', 'vix', 'sp500']:
        if key not in data_dict:
            missing.append(MINIMUM_INDICATORS[key].name)

    latest_data_point = max(latest_dates) if latest_dates else None
    return {
        'latest_data_point': latest_data_point,
        'latest_data_point_display': latest_data_point.strftime('%Y-%m-%d') if latest_data_point else '—',
        'source_mode': '샘플 데이터' if use_sample else '실시간 데이터',
        'fed_bs_enabled': fed_bs_enabled,
        'custom_indicator_count': custom_indicator_count,
        'missing_critical_indicators': missing,
    }


def render_framework_expander() -> None:
    """Render the lightweight framework explanation."""
    with st.expander("Framework", expanded=False):
        st.markdown(FRAMEWORK_MARKDOWN)


def render_command_center(
    data_dict: Dict[str, pd.Series],
    regime_result,
    regime_history_df: Optional[pd.DataFrame],
    load_meta: Dict[str, object],
    alert_config: AlertConfig,
) -> None:
    """Render the dashboard command center."""
    if not data_dict:
        st.warning("⚠️ 데이터가 없습니다.")
        return

    metrics = build_dashboard_metrics(data_dict)
    alerts = _active_alerts(data_dict, alert_config)
    summary = generate_daily_summary(
        regime=regime_result.primary_regime,
        credit_growth=metrics.get('credit_growth_3m'),
        spread_zscore=metrics.get('spread_zscore'),
        vix_percentile=metrics.get('vix_percentile'),
        equity_1m=metrics.get('equity_1m'),
    )

    render_status_bar(
        load_meta=load_meta,
        regime_label=regime_result.primary_regime.value,
        confidence=regime_result.confidence,
        alert_count=len(alerts),
    )

    render_headline_card(
        title=f"{regime_result.primary_regime.value} 레짐",
        summary=summary,
        explanations=regime_result.explanations,
        watch_label="현재 읽힌 핵심 신호",
    )

    render_kpi_strip([
        {'label': '신용 성장', 'value': f"{metrics['credit_growth_3m']:.1f}% ann" if metrics['credit_growth_3m'] is not None else '—'},
        {'label': 'HY 스프레드', 'value': f"z={metrics['spread_zscore']:.1f}" if metrics['spread_zscore'] is not None else '—'},
        {'label': 'VIX 백분위', 'value': _safe_percent_rank(metrics['vix_percentile'])},
        {'label': 'S&P 500 1M', 'value': f"{metrics['equity_1m']:+.1f}%" if metrics['equity_1m'] is not None else '—', 'delta_color': 'inverse'},
    ])

    left, right = st.columns(2)
    with left:
        render_signal_panel("What Changed", generate_what_changed(regime_result.primary_regime, metrics, alerts), caption="최근 변화의 핵심")
    with right:
        render_signal_panel("What Matters Next", generate_watch_next(regime_result.primary_regime, metrics, alerts), caption="다음 확인 포인트")

    st.markdown("### 취약 지점 Top 3")
    vulnerabilities = generate_vulnerability_report(regime_result.primary_regime, metrics, alerts=alerts)
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
        st.info("현재 핵심 취약 지점이 감지되지 않습니다.")

    st.markdown("### 레짐 전환 이력")
    if regime_history_df is not None and not regime_history_df.empty:
        hist_regimes = regime_history_df['regime'].tolist()
        hist_dates = regime_history_df.index.tolist()
        previous_regime = None
        last_transition_date = None
        for idx in range(len(hist_regimes) - 1, 0, -1):
            if hist_regimes[idx] != hist_regimes[idx - 1]:
                previous_regime = hist_regimes[idx - 1]
                last_transition_date = hist_dates[idx]
                break

        render_kpi_strip([
            {'label': '현재 레짐', 'value': regime_result.primary_regime.value},
            {'label': '신뢰도', 'value': f"{regime_result.confidence:.0%}"},
            {'label': '이전 레짐', 'value': previous_regime or '—'},
            {'label': '마지막 전환', 'value': last_transition_date.strftime('%Y-%m-%d') if last_transition_date else '—'},
        ])
        fig_history = create_regime_history_chart(regime_history_df, height=320, height_preset='compact')
        st.plotly_chart(fig_history, width="stretch")
    else:
        st.info("레짐 이력 데이터가 없습니다.")

    if regime_result.data_quality_warning:
        st.warning(f"⚠️ 데이터 품질 경고: {regime_result.data_quality_warning}")


def build_view_context(
    data_dict: Dict[str, pd.Series],
    use_sample: bool,
    fed_bs_enabled: bool,
    custom_indicator_count: int,
) -> Dict[str, object]:
    """Build the shared view context consumed by app.py."""
    return {
        'load_meta': _build_load_meta(
            data_dict=data_dict,
            use_sample=use_sample,
            fed_bs_enabled=fed_bs_enabled,
            custom_indicator_count=custom_indicator_count,
        ),
        'alert_config': _build_alert_config_from_session(),
    }


def render_liquidity_engine(data_dict: Dict[str, pd.Series], regime_result) -> None:
    """Render liquidity-engine diagnostics."""
    if not data_dict:
        st.warning("⚠️ 데이터가 없습니다.")
        return

    metrics = build_dashboard_metrics(data_dict)
    bank_credit = data_dict.get('bank_credit')
    fed_assets = data_dict.get('fed_assets')
    m2 = data_dict.get('m2')

    st.markdown("### Snapshot")
    credit_acceleration = None
    if bank_credit is not None and len(bank_credit) > 26:
        credit_growth = calc_3m_annualized(bank_credit, periods_3m=13)
        if len(credit_growth) > 13:
            credit_acceleration = _latest(credit_growth.diff(13))

    render_kpi_strip([
        {'label': 'Fed 자산', 'value': f"${_latest(fed_assets) / 1e12:.2f}T" if _latest(fed_assets) is not None else '—'},
        {'label': '은행 신용', 'value': f"{metrics['credit_growth_3m']:.1f}% ann" if metrics['credit_growth_3m'] is not None else '—'},
        {'label': 'M2 YoY', 'value': f"{_latest(calc_yoy(m2, periods=52)):.1f}%" if m2 is not None and len(m2) > 52 else '—'},
        {'label': '신용 가속도', 'value': f"{credit_acceleration:+.1f}pt" if credit_acceleration is not None else '—', 'delta_color': 'inverse'},
    ])

    st.markdown("### Trend")
    col1, col2 = st.columns(2)
    with col1:
        level_data = {}
        if fed_assets is not None:
            level_data['Fed Assets (T)'] = fed_assets / 1e12
        if bank_credit is not None:
            level_data['Bank Credit (T)'] = bank_credit / 1e12
        if m2 is not None:
            level_data['M2 (T)'] = m2 / 1e12
        fig = create_multi_line_chart(
            level_data,
            title='대차대조표 규모',
            height_preset='compact',
            latest_annotation=True,
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        growth_data = {}
        if fed_assets is not None and len(fed_assets) > 13:
            growth_data['Fed Assets 3M ann'] = calc_3m_annualized(fed_assets, periods_3m=13)
        if bank_credit is not None and len(bank_credit) > 13:
            growth_data['Bank Credit 3M ann'] = calc_3m_annualized(bank_credit, periods_3m=13)
        if m2 is not None and len(m2) > 13:
            growth_data['M2 3M ann'] = calc_3m_annualized(m2, periods_3m=13)
        fig = create_multi_line_chart(
            growth_data,
            title='성장률 흐름',
            height_preset='compact',
            threshold_lines=[{'value': 0, 'label': '수축/확장 경계', 'color': '#94a3b8'}],
        )
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Pressure Points")
    col1, col2 = st.columns(2)
    with col1:
        zscore_data = {}
        if fed_assets is not None and len(fed_assets) > 156:
            zscore_data['Fed Assets Z'] = calc_zscore(fed_assets, window_years=3, periods_per_year=52)
        if bank_credit is not None and len(bank_credit) > 156:
            zscore_data['Bank Credit Z'] = calc_zscore(bank_credit, window_years=3, periods_per_year=52)
        if m2 is not None and len(m2) > 156:
            zscore_data['M2 Z'] = calc_zscore(m2, window_years=3, periods_per_year=52)
        fig = create_multi_line_chart(
            zscore_data,
            title='유동성 압력 Z-Score',
            height_preset='compact',
            threshold_lines=[
                {'value': 2, 'label': '과열', 'color': '#f59e0b'},
                {'value': -2, 'label': '위축', 'color': '#f87171'},
            ],
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        fig = create_regime_gauge(
            scores=regime_result.scores.to_dict(),
            primary_regime=regime_result.primary_regime.value,
            height=320,
        )
        st.plotly_chart(fig, width="stretch")


def _build_collateral_stress_series(data_dict: Dict[str, pd.Series]) -> Dict[str, object]:
    components = {}
    if 'vix' in data_dict and len(data_dict['vix']) > 756:
        components['VIX'] = calc_percentile(data_dict['vix'], window_years=3, periods_per_year=252)
    if 'hy_spread' in data_dict and len(data_dict['hy_spread']) > 156:
        components['HY Spread'] = calc_percentile(data_dict['hy_spread'], window_years=3, periods_per_year=52)
    if 'sp500' in data_dict and len(data_dict['sp500']) > 21:
        components['Equity Drawdown'] = calc_1m_change(data_dict['sp500']).clip(upper=0).abs() * 10

    if not components:
        return {'score': None, 'components': {}}

    aligned = pd.concat(components, axis=1)
    return {'score': aligned.mean(axis=1, skipna=True), 'components': components}


def render_collateral_stress(data_dict: Dict[str, pd.Series], alert_config: AlertConfig) -> None:
    """Render collateral stress diagnostics."""
    if not data_dict:
        st.warning("⚠️ 데이터가 없습니다.")
        return

    metrics = build_dashboard_metrics(data_dict)
    stress_bundle = _build_collateral_stress_series(data_dict)
    stress_score = _latest(stress_bundle['score']) if stress_bundle['score'] is not None else None
    alert = check_collateral_stress(data_dict, config=alert_config)

    spread_percentile = None
    if 'hy_spread' in data_dict and len(data_dict['hy_spread']) > 156:
        spread_percentile = _latest(calc_percentile(data_dict['hy_spread'], window_years=3, periods_per_year=52))

    st.markdown("### Snapshot")
    render_kpi_strip([
        {'label': '종합 스트레스', 'value': f"{stress_score:.0f}/100" if stress_score is not None else '—'},
        {'label': 'VIX 백분위', 'value': _safe_percent_rank(metrics['vix_percentile'])},
        {'label': 'HY 백분위', 'value': _safe_percent_rank(spread_percentile)},
        {'label': 'S&P 500 1M', 'value': f"{metrics['equity_1m']:+.1f}%" if metrics['equity_1m'] is not None else '—', 'delta_color': 'inverse'},
    ])

    if alert:
        render_alert_card(alert.level, alert.title, alert.format_message(), alert.additional_checks)

    component_values = {
        name: _latest(series)
        for name, series in stress_bundle['components'].items()
    }
    drivers = [
        f"{name}: {value:.0f}"
        for name, value in sorted(component_values.items(), key=lambda item: item[1] or -1, reverse=True)
        if value is not None
    ]
    render_signal_panel(
        "Stress Drivers",
        drivers or ["유효한 종합 스트레스 구성요소가 부족합니다."],
        caption="현재 부담이 큰 항목",
    )

    col1, col2 = st.columns(2)
    with col1:
        chart_data = {}
        if 'vix' in data_dict:
            chart_data['VIX'] = data_dict['vix']
        if 'hy_spread' in data_dict:
            chart_data['HY Spread (bps)'] = data_dict['hy_spread'] * 100
        fig = create_multi_line_chart(
            chart_data,
            title='변동성 및 스프레드',
            height_preset='compact',
            latest_annotation=True,
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        if 'sp500' in data_dict:
            sp_df = pd.DataFrame({
                'date': data_dict['sp500'].index,
                'value': data_dict['sp500'].values,
            })
            fig = create_timeseries_chart(
                sp_df,
                title='담보 자산 프록시',
                height_preset='compact',
                latest_annotation=True,
            )
            st.plotly_chart(fig, width="stretch")

    if stress_bundle['score'] is not None and len(stress_bundle['score']) > 0:
        score_df = pd.DataFrame({
            'date': stress_bundle['score'].index,
            'value': stress_bundle['score'].values,
        })
        fig = create_timeseries_chart(
            score_df,
            title='종합 담보 스트레스 점수',
            height_preset='compact',
            threshold_lines=[
                {'value': 40, 'label': '주의', 'color': '#f59e0b'},
                {'value': 65, 'label': '경계', 'color': '#f87171'},
            ],
            latest_annotation=True,
        )
        st.plotly_chart(fig, width="stretch")


def _calculate_leverage_score(data_dict: Dict[str, pd.Series]) -> float:
    scores = []
    if 'bank_credit' in data_dict:
        credit_growth = _latest(calc_3m_annualized(data_dict['bank_credit'], 13))
        if credit_growth is not None:
            scores.append(min(100.0, max(0.0, 30 + credit_growth * 4.5)))
    if 'hy_spread' in data_dict and len(data_dict['hy_spread']) > 10:
        spread = data_dict['hy_spread']
        spread_range = spread.max() - spread.min()
        if spread_range != 0:
            scores.append(100 - ((spread.iloc[-1] - spread.min()) / spread_range * 100))
    if 'vix' in data_dict and len(data_dict['vix']) > 10:
        vix = data_dict['vix']
        vix_range = vix.max() - vix.min()
        if vix_range != 0:
            scores.append(100 - ((vix.iloc[-1] - vix.min()) / vix_range * 100))
    return float(sum(scores) / len(scores)) if scores else 50.0


def render_belief_and_leverage(data_dict: Dict[str, pd.Series], alert_config: AlertConfig) -> None:
    """Render the combined belief and leverage workspace."""
    if not data_dict:
        st.warning("⚠️ 데이터가 없습니다.")
        return

    metrics = build_dashboard_metrics(data_dict)
    belief_alert = check_belief_overheating(data_dict, config=alert_config)
    leverage_score = _calculate_leverage_score(data_dict)

    st.markdown("### Snapshot")
    render_kpi_strip([
        {'label': '레버리지 점수', 'value': f"{leverage_score:.0f}/100"},
        {'label': 'P/E Z-Score', 'value': f"{metrics['pe_zscore']:+.1f}" if metrics['pe_zscore'] is not None else '—'},
        {'label': 'PE-EPS Gap', 'value': f"{metrics['pe_eps_gap']:+.2f}σ" if metrics['pe_eps_gap'] is not None else '—'},
        {'label': '실질금리', 'value': f"{metrics['real_yield']:+.2f}%" if metrics['real_yield'] is not None else '—'},
    ])

    if belief_alert:
        render_alert_card(
            belief_alert.level,
            belief_alert.title,
            belief_alert.format_message(),
            belief_alert.additional_checks,
        )

    col1, col2 = st.columns(2)
    with col1:
        rate_data = {}
        if 'real_yield' in data_dict:
            rate_data['실질금리 10Y'] = data_dict['real_yield']
        if 'breakeven' in data_dict:
            rate_data['기대 인플레이션 10Y'] = data_dict['breakeven']
        fig = create_multi_line_chart(
            rate_data,
            title='금리와 기대',
            height_preset='compact',
            threshold_lines=[{'value': 0, 'label': '제로', 'color': '#94a3b8'}],
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        valuation_data = {}
        if 'pe_ratio' in data_dict and len(data_dict['pe_ratio']) > 156:
            valuation_data['PE Z'] = calc_zscore(data_dict['pe_ratio'], window_years=3, periods_per_year=52)
        if 'forward_eps' in data_dict and len(data_dict['forward_eps']) > 156:
            valuation_data['EPS Z'] = calc_zscore(data_dict['forward_eps'], window_years=3, periods_per_year=52)
        fig = create_multi_line_chart(
            valuation_data,
            title='밸류에이션 vs 이익',
            height_preset='compact',
            threshold_lines=[{'value': 0, 'label': '중립', 'color': '#94a3b8'}],
        )
        st.plotly_chart(fig, width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        if 'pe_ratio' in data_dict and 'forward_eps' in data_dict:
            val_change = calc_zscore_change(data_dict['pe_ratio'], window_years=3, change_periods=4, periods_per_year=52)
            earn_change = calc_zscore_change(data_dict['forward_eps'], window_years=3, change_periods=4, periods_per_year=52)
            fig = create_valuation_scatter(
                val_change,
                earn_change,
                title='신념 과열 맵',
                height_preset='compact',
            )
            st.plotly_chart(fig, width="stretch")

    with col2:
        inferred_regime = Regime.LATE_CYCLE if metrics.get('pe_eps_gap') and metrics['pe_eps_gap'] > 0.5 else Regime.EXPANSION
        analysis = generate_belief_analysis(
            regime=inferred_regime,
            credit_growth=metrics.get('credit_growth_3m'),
            real_yield=metrics.get('real_yield'),
            breakeven=metrics.get('breakeven'),
            pe_zscore=metrics.get('pe_zscore'),
            eps_growth=metrics.get('eps_growth'),
        )
        render_signal_panel("Marginal Buyer Read", analysis, caption="한계 투자자 해석")

    checks = generate_fundamental_check(
        pe_zscore=metrics.get('pe_zscore'),
        eps_growth=metrics.get('eps_growth'),
        credit_growth=metrics.get('credit_growth_3m'),
    )
    checklist_lines = []
    for check_item, passed, explanation in checks:
        prefix = "PASS" if passed is True else ("CHECK" if passed is False else "DATA")
        checklist_lines.append(f"{prefix} | {check_item}: {explanation}")
    render_action_list("실물 뒷받침 체크리스트", checklist_lines or ["평가를 위한 데이터가 부족합니다."])


def _qt_pause_signal_summary(data_dict: Dict[str, pd.Series]) -> Dict[str, object]:
    warnings: List[str] = []
    level = "정상"
    if 'reserve_balances' in data_dict:
        latest_reserves = _latest(data_dict['reserve_balances'] / 1e9)
        if latest_reserves is not None and latest_reserves < 1500:
            warnings.append("준비금이 1.5T 아래로 접근")
    if 'reverse_repo' in data_dict:
        latest_rrp = _latest(data_dict['reverse_repo'] / 1e9)
        if latest_rrp is not None and latest_rrp > 1000:
            warnings.append("RRP 수요가 1T 상회")
    if 'fed_lending' in data_dict:
        latest_lending = _latest(data_dict['fed_lending'] / 1e9)
        if latest_lending is not None and latest_lending > 100:
            warnings.append("Fed 대출이 비정상적으로 활성화")
    if 'vix' in data_dict:
        latest_vix = _latest(data_dict['vix'])
        if latest_vix is not None and latest_vix > 25:
            warnings.append("변동성이 펀딩 불안으로 확산")

    if len(warnings) >= 3:
        level = "높음"
    elif len(warnings) == 2:
        level = "주의"

    return {'level': level, 'warnings': warnings}


def render_qt_monitor(data_dict: Dict[str, pd.Series]) -> None:
    """Render the condensed QT workspace."""
    if not data_dict:
        st.warning("⚠️ 데이터가 없습니다.")
        return

    qt_pace_series = calculate_qt_pace(data_dict['fed_assets'], periods_1m=4) if 'fed_assets' in data_dict else None
    reserve_regime = classify_reserve_regime(
        data_dict['reserve_balances'] / 1e9,
        reverse_repo=(data_dict.get('reverse_repo') / 1e9) if 'reverse_repo' in data_dict else None,
    ) if 'reserve_balances' in data_dict else None
    money_market = detect_money_market_stress(data_dict['reverse_repo'] / 1e9) if 'reverse_repo' in data_dict else None
    lending_stress = calculate_fed_lending_stress(data_dict['fed_lending'] / 1e9) if 'fed_lending' in data_dict else None
    pause_signal = _qt_pause_signal_summary(data_dict)

    st.markdown("### Snapshot")
    render_kpi_strip([
        {'label': 'QT 페이스', 'value': f"{_latest(qt_pace_series):+.2f}% 1M" if qt_pace_series is not None and _latest(qt_pace_series) is not None else '—'},
        {'label': '준비금 레짐', 'value': str(reserve_regime.iloc[-1]) if reserve_regime is not None and len(reserve_regime) > 0 else '—'},
        {'label': 'MM Stress', 'value': f"{_latest(money_market['stress_score']):.0f}/100" if money_market else '—'},
        {'label': 'Pause 신호', 'value': pause_signal['level']},
    ])

    col1, col2 = st.columns(2)
    with col1:
        qt_chart_data = {}
        if 'fed_assets' in data_dict:
            qt_chart_data['Fed Assets (T)'] = data_dict['fed_assets'] / 1e12
        if qt_pace_series is not None:
            qt_chart_data['QT Pace (%)'] = qt_pace_series
        fig = create_multi_line_chart(
            qt_chart_data,
            title='Fed 자산과 QT 페이스',
            secondary_y=['QT Pace (%)'] if 'QT Pace (%)' in qt_chart_data else None,
            height_preset='compact',
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        reserve_data = {}
        if 'reserve_balances' in data_dict:
            reserve_data['Reserve Balances (T)'] = data_dict['reserve_balances'] / 1e12
        if 'reverse_repo' in data_dict:
            reserve_data['Reverse Repo (T)'] = data_dict['reverse_repo'] / 1e12
        fig = create_multi_line_chart(
            reserve_data,
            title='준비금과 RRP',
            height_preset='compact',
            latest_annotation=True,
        )
        st.plotly_chart(fig, width="stretch")

    signal_lines = pause_signal['warnings'] or ["현재 주요 QT 일시중단 경고는 크지 않습니다."]
    if lending_stress:
        latest_lending_score = _latest(lending_stress['stress_score'])
        if latest_lending_score is not None:
            signal_lines.append(f"Fed 대출 스트레스 점수 {latest_lending_score:.0f}/100")
    render_signal_panel("Pause Signals", signal_lines, caption="현재 확인할 QT 중단 압력")

    with st.expander("QT Framework", expanded=False):
        st.markdown("""
        - `ΔReserves = ΔSOMA + ΔLending - ΔRRP - ΔTGA` 항등식으로 QT 압력을 읽습니다.
        - 준비금이 충분 구간에서 빠르게 이탈하거나 RRP 수요가 재확대되면 QT 부담이 커집니다.
        - Fed 대출 활성화는 은행 시스템 스트레스가 머니마켓으로 번질 가능성을 시사합니다.
        """)


def render_action_center(data_dict: Dict[str, pd.Series], regime_result) -> None:
    """Render alerts, playbook, checklist, and threshold controls."""
    if not data_dict:
        st.warning("⚠️ 데이터가 없습니다.")
        return

    _ensure_alert_form_state()
    notice = st.session_state.pop('alert_config_notice', None)
    if notice:
        st.success(notice)

    alert_config = _build_alert_config_from_session()
    alerts = _active_alerts(data_dict, alert_config)
    metrics = build_dashboard_metrics(data_dict)

    st.markdown("### 활성 알림")
    if alerts:
        for alert in alerts:
            render_alert_card(
                alert.level,
                alert.title,
                alert.format_message(),
                alert.additional_checks,
                timestamp=alert.timestamp.strftime('%Y-%m-%d %H:%M'),
            )
    else:
        st.success("✅ 현재 활성화된 알림이 없습니다.")

    col1, col2 = st.columns(2)
    with col1:
        render_action_list(
            "레짐별 플레이북",
            PLAYBOOKS.get(regime_result.primary_regime, ["현재 레짐에 맞는 플레이북이 없습니다."]),
            caption=REGIME_DESCRIPTIONS.get(regime_result.primary_regime, ''),
        )

    with col2:
        checklist_items = []
        for title, explanation, passed in [
            ("신용 성장", "신용 수축 여부 확인", metrics.get('credit_growth_3m')),
            ("스프레드", "신용 경색 여부 확인", metrics.get('spread_zscore')),
            ("변동성", "담보 스트레스 여부 확인", metrics.get('vix_percentile')),
        ]:
            checklist_items.append(f"{title}: {'데이터 부족' if passed is None else explanation}")
        render_action_list("체크리스트", checklist_items, caption="리스크 검토 순서")

    st.markdown("### 알림 임계치")
    with st.form("alert_threshold_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.slider("VIX 경고 백분위", min_value=50, max_value=100, key="alert_form_vix_percentile_yellow")
            st.slider("VIX 위험 백분위", min_value=60, max_value=100, key="alert_form_vix_percentile_red")
            st.slider("스프레드 경고 백분위", min_value=50, max_value=100, key="alert_form_spread_percentile_yellow")
            st.slider("스프레드 위험 백분위", min_value=60, max_value=100, key="alert_form_spread_percentile_red")
        with col2:
            st.slider("주가 1M 경고 하락폭", min_value=-20.0, max_value=0.0, step=0.5, key="alert_form_equity_drawdown_yellow")
            st.slider("주가 1M 위험 하락폭", min_value=-20.0, max_value=0.0, step=0.5, key="alert_form_equity_drawdown_red")
            st.slider("신념 과열 경고 gap", min_value=0.1, max_value=1.0, step=0.05, key="alert_form_belief_zscore_gap_yellow")
            st.slider("신념 과열 위험 gap", min_value=0.2, max_value=1.5, step=0.05, key="alert_form_belief_zscore_gap_red")
        apply_col, reset_col = st.columns(2)
        apply_clicked = apply_col.form_submit_button("설정 적용", type="primary")
        reset_clicked = reset_col.form_submit_button("기본값 복원")

    if apply_clicked:
        new_config = AlertConfig(
            belief_zscore_gap_yellow=st.session_state['alert_form_belief_zscore_gap_yellow'],
            belief_zscore_gap_red=st.session_state['alert_form_belief_zscore_gap_red'],
            vix_percentile_yellow=st.session_state['alert_form_vix_percentile_yellow'],
            vix_percentile_red=st.session_state['alert_form_vix_percentile_red'],
            spread_percentile_yellow=st.session_state['alert_form_spread_percentile_yellow'],
            spread_percentile_red=st.session_state['alert_form_spread_percentile_red'],
            equity_drawdown_yellow=st.session_state['alert_form_equity_drawdown_yellow'],
            equity_drawdown_red=st.session_state['alert_form_equity_drawdown_red'],
        )
        _store_alert_config(new_config)
        st.session_state['alert_config_notice'] = "세션 기준 알림 임계치를 적용했습니다."
        st.rerun()

    if reset_clicked:
        default_config = AlertConfig()
        _store_alert_config(default_config)
        for key, value in asdict(default_config).items():
            st.session_state[f"alert_form_{key}"] = value
        st.session_state['alert_config_notice'] = "알림 임계치를 기본값으로 복원했습니다."
        st.rerun()


def render_diagnostics(data_dict: Dict[str, pd.Series], regime_result, alert_config: AlertConfig, diagnostic_view: str) -> None:
    """Render the selected diagnostics workspace."""
    if diagnostic_view == 'Liquidity Engine':
        render_liquidity_engine(data_dict, regime_result)
    elif diagnostic_view == 'Collateral Stress':
        render_collateral_stress(data_dict, alert_config)
    elif diagnostic_view == 'Belief & Leverage':
        render_belief_and_leverage(data_dict, alert_config)
    else:
        render_qt_monitor(data_dict)
