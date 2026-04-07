"""
Dashboard-focused UI primitives built mostly with native Streamlit containers.
"""
from typing import Iterable, List, Mapping, Optional

import streamlit as st


def bordered_container():
    """Return a bordered container when supported by the Streamlit version."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def _render_stat(label: str, value: str, help_text: Optional[str] = None) -> None:
    st.caption(label)
    st.markdown(f"**{value}**")
    if help_text:
        st.caption(help_text)


def render_status_bar(
    load_meta: Mapping[str, object],
    regime_label: str,
    confidence: float,
    alert_count: int,
) -> None:
    """Render a compact dashboard status strip."""
    with bordered_container():
        cols = st.columns(5)
        with cols[0]:
            refreshed_at = load_meta.get('refreshed_at')
            refreshed_text = ''
            if hasattr(refreshed_at, 'strftime'):
                refreshed_text = f"새로고침 {refreshed_at.strftime('%H:%M')}"
            _render_stat("데이터 시점", str(load_meta.get('latest_data_point_display', '—')), refreshed_text or None)
        with cols[1]:
            _render_stat("데이터 모드", str(load_meta.get('source_mode', '—')))
        with cols[2]:
            _render_stat("현재 레짐", regime_label, f"신뢰도 {confidence:.0%}")
        with cols[3]:
            fed_bs = "포함" if load_meta.get('fed_bs_enabled') else "기본"
            _render_stat("Fed BS 확장", fed_bs)
        with cols[4]:
            _render_stat(
                "활성 경고",
                f"{alert_count}개",
                f"사용자 지표 {load_meta.get('custom_indicator_count', 0)}개",
            )

        missing = load_meta.get('missing_critical_indicators', [])
        if missing:
            st.caption(f"핵심 지표 누락: {', '.join(missing)}")


def render_headline_card(
    title: str,
    summary: str,
    explanations: Optional[Iterable[str]] = None,
    watch_label: Optional[str] = None,
) -> None:
    """Render the top headline card for the command center."""
    with bordered_container():
        left, right = st.columns([1.5, 1.0])
        with left:
            st.markdown(f"### {title}")
            st.write(summary)
        with right:
            st.caption(watch_label or "핵심 신호")
            for line in list(explanations or [])[:3]:
                st.markdown(f"- {line}")


def render_kpi_strip(items: List[Mapping[str, object]]) -> None:
    """Render up to four KPI metrics in a fixed-width strip."""
    if not items:
        return

    cols = st.columns(min(len(items), 4))
    for col, item in zip(cols, items[:4]):
        with col:
            st.metric(
                label=str(item.get('label', '—')),
                value=str(item.get('value', '—')),
                delta=item.get('delta'),
                delta_color=str(item.get('delta_color', 'normal')),
                help=item.get('help'),
                border=True,
            )


def render_signal_panel(
    title: str,
    lines: Iterable[str],
    caption: Optional[str] = None,
) -> None:
    """Render a short text panel for synthesized signals."""
    with bordered_container():
        st.markdown(f"#### {title}")
        if caption:
            st.caption(caption)
        for line in lines:
            st.markdown(f"- {line}")


def render_action_list(
    title: str,
    items: Iterable[str],
    caption: Optional[str] = None,
) -> None:
    """Render a compact action list."""
    with bordered_container():
        st.markdown(f"#### {title}")
        if caption:
            st.caption(caption)
        for idx, item in enumerate(items, start=1):
            st.markdown(f"{idx}. {item}")
