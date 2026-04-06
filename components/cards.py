"""
Card components for Streamlit display.
Streamlit 카드 컴포넌트

핵심 컴포넌트:
- 레짐 배지
- 지표 카드 (변화량, 임계치 표시)
- 알림 카드
- 취약 지점 카드
"""
from typing import Optional, List, Dict, Any
import streamlit as st

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime, AlertLevel, REGIME_COLORS, ALERT_COLORS, REGIME_DESCRIPTIONS
from components.styles import COLOR_PALETTE


def render_regime_badge(
    regime: Regime,
    explanations: Optional[List[str]] = None,
    confidence: float = 0.0,
) -> None:
    """
    Render the regime badge at the top of the page.
    레짐 배지 렌더링
    
    Args:
        regime: Current regime
        explanations: List of explanation lines
        confidence: Confidence score (0-1)
    """
    color = REGIME_COLORS.get(regime, '#666666')
    description = REGIME_DESCRIPTIONS.get(regime, '')
    
    # Badge HTML
    badge_html = f"""
    <div style="
        background: linear-gradient(135deg, {color}1a, {color}33);
        border: 1px solid {color}4d;
        border-radius: 24px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        backdrop-filter: blur(8px);
        transition: transform 0.3s ease;
    " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="
                background: {color};
                color: white;
                padding: 10px 20px;
                border-radius: 24px;
                font-weight: 800;
                font-size: 1.3em;
                box-shadow: 0 4px 12px {color}66;
            ">
                {regime.value}
            </div>
            <div style="
                background: rgba(255,255,255,0.1);
                color: #f5f5f7;
                padding: 6px 12px;
                border-radius: 12px;
                font-size: 0.9em;
                font-weight: 600;
            ">
                Confidence: {confidence*100:.0f}%
            </div>
        </div>
        <p style="color: #ebebf5; margin-top: 16px; margin-bottom: 12px; font-size: 1.05em; font-weight: 500;">
            {description}
        </p>
    """
    
    if explanations:
        badge_html += '<div style="margin-top: 16px; display: flex; flex-direction: column; gap: 8px;">'
        for exp in explanations[:3]:
            badge_html += f'<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 8px 12px; color: #ebebf599; font-size: 0.95em;">• {exp}</div>'
        badge_html += '</div>'
    
    badge_html += '</div>'
    
    st.markdown(badge_html, unsafe_allow_html=True)


def render_metric_card(
    title: str,
    value: float,
    format_str: str = '{:.2f}',
    change_1w: Optional[float] = None,
    change_1m: Optional[float] = None,
    change_3m: Optional[float] = None,
    zscore: Optional[float] = None,
    threshold_warning: Optional[float] = None,
    threshold_danger: Optional[float] = None,
    invert: bool = False,
    unit: str = '',
) -> None:
    """
    Render a metric card with value and changes.
    지표 카드 렌더링
    
    Args:
        title: Card title
        value: Current value
        format_str: Format string for value
        change_1w: 1-week change (%)
        change_1m: 1-month change (%)
        change_3m: 3-month change (%)
        zscore: Z-score (optional)
        threshold_warning: Yellow threshold
        threshold_danger: Red threshold
        invert: If True, lower values are worse
        unit: Unit string (e.g., '%', 'bps')
    """
    # Determine status color
    status_color = COLOR_PALETTE['success']  # Default green
    
    if threshold_danger is not None and threshold_warning is not None:
        if invert:
            if value <= threshold_danger:
                status_color = COLOR_PALETTE['danger']
            elif value <= threshold_warning:
                status_color = COLOR_PALETTE['warning']
        else:
            if value >= threshold_danger:
                status_color = COLOR_PALETTE['danger']
            elif value >= threshold_warning:
                status_color = COLOR_PALETTE['warning']
    
    # Format value
    try:
        formatted_value = format_str.format(value)
    except Exception:
        formatted_value = str(value)
    
    # Build change indicators
    changes_html = ''
    if change_1w is not None or change_1m is not None or change_3m is not None:
        changes_html = '<div style="display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap;">'
        
        for label, change in [('1W', change_1w), ('1M', change_1m), ('3M', change_3m)]:
            if change is not None:
                change_color = COLOR_PALETTE['success'] if (change > 0) != invert else COLOR_PALETTE['danger']
                arrow = '↑' if change > 0 else '↓'
                changes_html += f'''
                    <div style="
                        background: {change_color}22;
                        color: {change_color};
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 0.8em;
                        font-weight: 700;
                        display: flex;
                        align-items: center;
                        gap: 4px;
                    ">
                        <span>{label}</span> <span>{arrow} {abs(change):.1f}%</span>
                    </div>
                '''
        
        changes_html += '</div>'
    
    # Z-score indicator
    zscore_html = ''
    if zscore is not None:
        z_color = COLOR_PALETTE['danger'] if abs(zscore) > 2 else (COLOR_PALETTE['warning'] if abs(zscore) > 1 else COLOR_PALETTE['success'])
        zscore_html = f'''
            <div style="
                margin-top: 6px;
                color: {z_color};
                font-size: 0.85em;
                font-weight: 600;
            ">
                Z-score: {zscore:+.2f}
            </div>
        '''
    
    # Card HTML
    card_html = f"""
    <div style="
        background-color: {COLOR_PALETTE['bg_card']};
        border-radius: 20px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease;
    " onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.2)';" onmouseout="this.style.transform='none'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)';">
        <div style="
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 6px;
            background-color: {status_color};
        "></div>
        <div style="color: {COLOR_PALETTE['text_muted']}; font-size: 0.95em; font-weight: 600; margin-bottom: 8px; margin-left: 4px;">
            {title}
        </div>
        <div style="
            color: {COLOR_PALETTE['text_primary']};
            font-size: 2em;
            font-weight: 800;
            margin-left: 4px;
            line-height: 1.2;
        ">
            {formatted_value}<span style="font-size: 0.6em; color: {COLOR_PALETTE['text_muted']}; margin-left: 4px;">{unit}</span>
        </div>
        <div style="margin-left: 4px;">
            {zscore_html}
            {changes_html}
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)


def render_alert_card(
    level: AlertLevel,
    title: str,
    message: str,
    additional_checks: Optional[List[str]] = None,
    timestamp: Optional[str] = None,
) -> None:
    """
    Render an alert card.
    알림 카드 렌더링
    
    Args:
        level: Alert level (Green/Yellow/Red)
        title: Alert title
        message: Alert message
        additional_checks: List of additional things to check
        timestamp: Alert timestamp
    """
    color = ALERT_COLORS.get(level, '#666666')
    icon = '🔴' if level == AlertLevel.RED else ('🟡' if level == AlertLevel.YELLOW else '🟢')
    
    checks_html = ''
    if additional_checks:
        checks_html = '<div style="margin-top: 8px; font-size: 0.85em; color: #9ca3af;">추가 확인: '
        checks_html += ', '.join(additional_checks[:2])
        checks_html += '</div>'
    
    time_html = ''
    if timestamp:
        time_html = f'<div style="font-size: 0.75em; color: #6b7280; margin-top: 8px;">{timestamp}</div>'
    
    card_html = f"""
    <div style="
        background: {color}1a;
        border-left: 4px solid {color};
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    ">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.2em;">{icon}</span>
            <span style="color: {color}; font-weight: bold;">{title}</span>
        </div>
        <p style="color: #d1d5db; margin-top: 8px; margin-bottom: 0; font-size: 0.9em;">
            {message}
        </p>
        {checks_html}
        {time_html}
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)


def render_vulnerability_card(
    rank: int,
    title: str,
    description: str,
    severity: str = 'medium',
    related_indicators: Optional[List[str]] = None,
) -> None:
    """
    Render a vulnerability/risk card.
    취약 지점 카드 렌더링
    """
    severity_colors = {
        'low': COLOR_PALETTE['success'],
        'medium': COLOR_PALETTE['warning'],
        'high': COLOR_PALETTE['danger'],
    }
    color = severity_colors.get(severity, '#f59e0b')
    
    # Simple text format for indicators
    indicators_text = ''
    if related_indicators:
        indicators_text = '관련 지표: ' + ', '.join(related_indicators[:3])
    
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, {COLOR_PALETTE['bg_card']}, {COLOR_PALETTE['bg_elevated']});
        border-left: 4px solid {color};
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.25s ease;
    " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="background:{color};color:white;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:1.1em;box-shadow: 0 4px 8px {color}66;">{rank}</div>
            <div style="color:{COLOR_PALETTE['text_primary']};font-weight:700;font-size:1.1em;">{title}</div>
        </div>
        <p style="color:{COLOR_PALETTE['text_secondary']};margin-top:16px;margin-bottom:0;font-size:1em;line-height:1.5;">{description}</p>
        <div style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 8px 12px; margin-top: 12px; color:{COLOR_PALETTE['text_muted']};font-size:0.85em;font-weight:500;">{indicators_text}</div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)



def render_data_quality_warning(
    message: str,
    details: Optional[List[str]] = None,
) -> None:
    """
    Render a data quality warning.
    데이터 품질 경고 렌더링
    """
    details_html = ''
    if details:
        details_html = '<ul style="margin-top: 8px; color: #9ca3af; font-size: 0.85em;">'
        for d in details:
            details_html += f'<li>{d}</li>'
        details_html += '</ul>'
    
    st.warning(f"""
    ⚠️ **데이터 품질 경고**
    
    {message}
    {details_html}
    """)
