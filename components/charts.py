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
import streamlit as st

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime, REGIME_COLORS

# Color palette for consistency - aligned with the app shell
COLORS = {
    'primary': '#60a5fa',      # Blue
    'secondary': '#38bdf8',    # Sky
    'success': '#34d399',      # Green
    'warning': '#f59e0b',      # Amber
    'danger': '#f87171',       # Red
    'neutral': '#94a3b8',      # Slate
    'bg_dark': '#111827',      # Dark background
    'bg_light': '#e2e8f0',     # Light background
    'grid': 'rgba(255,255,255,0.05)', # Ultra soft grid lines
}

SERIES_COLORS = [
    '#60a5fa',
    '#38bdf8',
    '#34d399',
    '#f59e0b',
    '#f87171',
    '#a3e635',
]

TIMEFRAME_TO_OFFSET = {
    '6M': pd.DateOffset(months=6),
    '1Y': pd.DateOffset(years=1),
    '3Y': pd.DateOffset(years=3),
    '5Y': pd.DateOffset(years=5),
    'Full': None,
}

HEIGHT_PRESETS = {
    'compact': 320,
    'default': 400,
    'tall': 480,
}


def get_active_timeframe(timeframe: Optional[str] = None) -> str:
    """Resolve the active chart timeframe."""
    if timeframe:
        return timeframe
    ui_state = st.session_state.get('ui_state', {})
    return ui_state.get('global_timeframe', 'Full')


def filter_series_by_timeframe(
    series: Optional[pd.Series],
    timeframe: Optional[str] = None,
) -> Optional[pd.Series]:
    """Slice a series to the active timeframe."""
    if series is None or len(series) == 0:
        return series

    active_timeframe = get_active_timeframe(timeframe)
    offset = TIMEFRAME_TO_OFFSET.get(active_timeframe)
    if offset is None:
        return series

    last_index = pd.to_datetime(series.index.max())
    cutoff = last_index - offset
    return series[series.index >= cutoff]


def filter_dataframe_by_timeframe(
    df: pd.DataFrame,
    date_col: str = 'date',
    timeframe: Optional[str] = None,
) -> pd.DataFrame:
    """Slice a dataframe by datetime column to the active timeframe."""
    if df is None or df.empty or date_col not in df.columns:
        return df

    active_timeframe = get_active_timeframe(timeframe)
    offset = TIMEFRAME_TO_OFFSET.get(active_timeframe)
    if offset is None:
        return df

    working_df = df.copy()
    working_df[date_col] = pd.to_datetime(working_df[date_col])
    last_date = pd.to_datetime(working_df[date_col].max())
    cutoff = last_date - offset
    return working_df[working_df[date_col] >= cutoff]


def _resolve_height(height: int, height_preset: Optional[str]) -> int:
    if height_preset and height_preset in HEIGHT_PRESETS:
        return HEIGHT_PRESETS[height_preset]
    return height


def _apply_threshold_lines(
    fig: go.Figure,
    threshold_lines: Optional[List[Dict[str, Union[float, str, int]]]] = None,
) -> None:
    for line in threshold_lines or []:
        fig.add_hline(
            y=float(line['value']),
            line_dash=str(line.get('dash', 'dash')),
            line_color=str(line.get('color', COLORS['neutral'])),
            opacity=float(line.get('opacity', 0.55)),
            annotation_text=line.get('label'),
            annotation_position=str(line.get('annotation_position', 'right')),
        )


def _annotate_latest_points(fig: go.Figure, max_annotations: int = 3) -> None:
    added = 0
    for trace in fig.data:
        if added >= max_annotations:
            break
        if getattr(trace, 'type', None) != 'scatter':
            continue
        if len(trace.x) == 0 or len(trace.y) == 0:
            continue
        latest_x = trace.x[-1]
        latest_y = trace.y[-1]
        if pd.isna(latest_y):
            continue

        if isinstance(latest_y, (int, float, np.integer, np.floating)):
            latest_text = f"{latest_y:,.2f}"
        else:
            latest_text = str(latest_y)

        fig.add_annotation(
            x=latest_x,
            y=latest_y,
            text=f"{trace.name}: {latest_text}",
            showarrow=False,
            xanchor='left',
            yanchor='middle',
            font=dict(size=11, color=getattr(trace.line, 'color', COLORS['neutral'])),
            bgcolor='rgba(15, 23, 42, 0.75)',
        )
        added += 1


def _apply_common_layout(fig: go.Figure, title: str, height: int) -> None:
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        height=height,
        margin=dict(l=40, r=40, t=56, b=40),
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(showgrid=True, gridcolor=COLORS['grid'], gridwidth=0.5),
        yaxis=dict(showgrid=True, gridcolor=COLORS['grid'], gridwidth=0.5),
    )


def create_timeseries_chart(
    df: pd.DataFrame,
    title: str = '',
    date_col: str = 'date',
    value_col: str = 'value',
    indicator_col: Optional[str] = None,
    highlight_recent: bool = True,
    show_trend: bool = False,
    height: int = 400,
    timeframe: Optional[str] = None,
    height_preset: Optional[str] = None,
    threshold_lines: Optional[List[Dict[str, Union[float, str, int]]]] = None,
    latest_annotation: bool = False,
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
    if df is None or df.empty:
        return go.Figure()

    df = filter_dataframe_by_timeframe(df, date_col=date_col, timeframe=timeframe)
    resolved_height = _resolve_height(height, height_preset)
    fig = go.Figure()
    
    # Handle multi-indicator data
    if indicator_col and indicator_col in df.columns:
        indicators = df[indicator_col].unique()
        for i, ind in enumerate(indicators):
            ind_df = df[df[indicator_col] == ind].sort_values(date_col)
            color = SERIES_COLORS[i % len(SERIES_COLORS)]
            fig.add_trace(go.Scatter(
                x=ind_df[date_col],
                y=ind_df[value_col],
                name=ind,
                mode='lines',
                line=dict(color=color, width=2.2),
            ))
    else:
        df = df.sort_values(date_col)
        fig.add_trace(go.Scatter(
            x=df[date_col],
            y=df[value_col],
            name=title or 'Value',
            mode='lines',
            line=dict(color=COLORS['primary'], width=2.4),
        ))
    
    # Highlight recent 3 months
    if highlight_recent and len(df) > 63:
        recent_start = df[date_col].iloc[-63]
        fig.add_vrect(
            x0=recent_start, x1=df[date_col].iloc[-1],
            fillcolor="rgba(96, 165, 250, 0.08)",
            layer="below",
            line_width=0,
        )

    if show_trend and len(df) >= 2:
        trend = np.polyfit(np.arange(len(df)), df[value_col], deg=1)
        trend_values = trend[0] * np.arange(len(df)) + trend[1]
        fig.add_trace(go.Scatter(
            x=df[date_col],
            y=trend_values,
            name='Trend',
            mode='lines',
            line=dict(color=COLORS['neutral'], width=1.4, dash='dot'),
        ))

    _apply_threshold_lines(fig, threshold_lines)
    if latest_annotation:
        _annotate_latest_points(fig, max_annotations=1 if not indicator_col else 3)
    _apply_common_layout(fig, title, resolved_height)
    return fig


def create_multi_line_chart(
    data: Dict[str, pd.Series],
    title: str = '',
    normalize: bool = False,
    height: int = 400,
    secondary_y: Optional[List[str]] = None,
    timeframe: Optional[str] = None,
    height_preset: Optional[str] = None,
    threshold_lines: Optional[List[Dict[str, Union[float, str, int]]]] = None,
    latest_annotation: bool = False,
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
    resolved_height = _resolve_height(height, height_preset)
    
    if has_secondary:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()
    
    colors = SERIES_COLORS

    for i, (name, series) in enumerate(data.items()):
        if series is None or len(series) == 0:
            continue
            
        values = filter_series_by_timeframe(series.copy(), timeframe=timeframe)
        if values is None or len(values) == 0:
            continue
        if normalize and len(values) > 0:
            values = (values / values.iloc[0]) * 100
        
        is_secondary = name in secondary_y
        color = colors[i % len(colors)]
        
        trace = go.Scatter(
            x=values.index if hasattr(values, 'index') else range(len(values)),
            y=values,
            name=name,
            mode='lines',
            line=dict(color=color, width=2.2, dash='dash' if is_secondary else 'solid'),
        )
        
        if has_secondary:
            fig.add_trace(trace, secondary_y=is_secondary)
        else:
            fig.add_trace(trace)
    
    _apply_threshold_lines(fig, threshold_lines)
    if latest_annotation:
        _annotate_latest_points(fig)
    _apply_common_layout(fig, title, resolved_height)
    return fig


def create_zscore_heatmap(
    df: pd.DataFrame,
    date_col: str = 'date',
    indicator_col: str = 'indicator',
    zscore_col: str = 'zscore',
    title: str = 'Z-Score Heatmap',
    height: int = 400,
    timeframe: Optional[str] = None,
    height_preset: Optional[str] = None,
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
    if df is None or df.empty:
        return go.Figure()

    df = filter_dataframe_by_timeframe(df, date_col=date_col, timeframe=timeframe)
    resolved_height = _resolve_height(height, height_preset)

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
        height=resolved_height,
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
    timeframe: Optional[str] = None,
    height_preset: Optional[str] = None,
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
    resolved_height = _resolve_height(height, height_preset)

    # Align dates
    common_idx = valuation_change.index.intersection(earnings_change.index)
    val = valuation_change.loc[common_idx]
    earn = earnings_change.loc[common_idx]
    val = filter_series_by_timeframe(val, timeframe=timeframe)
    earn = filter_series_by_timeframe(earn, timeframe=timeframe)
    common_idx = val.index.intersection(earn.index)
    val = val.loc[common_idx]
    earn = earn.loc[common_idx]
    if len(common_idx) == 0:
        return go.Figure()
    
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
        height=resolved_height,
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
    timeframe: Optional[str] = None,
    height_preset: Optional[str] = None,
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

    resolved_height = _resolve_height(height, height_preset)
    regime_history_df = regime_history_df.copy()
    regime_history_df.index = pd.to_datetime(regime_history_df.index)
    active_timeframe = get_active_timeframe(timeframe)
    offset = TIMEFRAME_TO_OFFSET.get(active_timeframe)
    if offset is not None:
        cutoff = regime_history_df.index.max() - offset
        regime_history_df = regime_history_df[regime_history_df.index >= cutoff]
        if regime_history_df.empty:
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
        bands.append((band_start, pd.Timestamp.now(), band_regime))

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
                x=dates[i].isoformat(),
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
        title=dict(text='레짐 이력 (최근 2년)', font=dict(size=14, color='#f5f5f7')),
        height=resolved_height,
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
        title=dict(text='레짐 점수', font=dict(size=14, color='#f5f5f7')),
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
