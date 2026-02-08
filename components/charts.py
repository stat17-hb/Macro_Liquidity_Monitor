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
