"""
Centralized styles and color palette for the Liquidity Dashboard.
유동성 대시보드 통합 스타일 시스템

모든 컬러 팔레트, CSS, 스타일 컴포넌트를 중앙 집중화하여 관리합니다.
"""
import streamlit as st
from typing import Optional


# ============================================================================
# COLOR PALETTE - 중앙 집중화된 색상 정의
# ============================================================================

COLOR_PALETTE = {
    # Primary colors
    'primary': '#3b82f6',          # Blue - 주요 액션, 링크
    'primary_light': '#60a5fa',    # Light Blue
    'primary_dark': '#2563eb',     # Dark Blue
    
    # Secondary colors
    'secondary': '#8b5cf6',        # Purple - 보조 요소
    'secondary_light': '#a78bfa',  # Light Purple
    
    # Status colors
    'success': '#22c55e',          # Green - 성공, 안전, 확장
    'success_dark': '#16a34a',     # Dark Green
    'warning': '#f59e0b',          # Amber - 경고, 주의
    'warning_light': '#fbbf24',    # Light Amber
    'danger': '#ef4444',           # Red - 위험, 오류
    'danger_dark': '#dc2626',      # Dark Red
    'danger_darker': '#7f1d1d',    # Very Dark Red - Stress
    
    # Neutral colors
    'neutral': '#6b7280',          # Gray - 비활성, 중립
    'neutral_light': '#9ca3af',    # Light Gray
    'neutral_dark': '#4b5563',     # Dark Gray
    
    # Background colors (Dark theme - Pure Black)
    'bg_base': '#0a0a0a',          # 가장 어두운 배경 (순수 블랙)
    'bg_card': '#171717',          # 카드 배경
    'bg_elevated': '#262626',      # 강조 배경
    'bg_hover': '#3a3a3a',         # 호버 상태
    
    # Border colors (Neutral Gray)
    'border': '#2a2a2a',           # 기본 테두리
    'border_light': '#3a3a3a',     # 밝은 테두리
    
    # Text colors (Neutral)
    'text_primary': '#fafafa',     # 주요 텍스트 (거의 흰색)
    'text_secondary': '#e5e5e5',   # 보조 텍스트
    'text_muted': '#a3a3a3',       # 흐린 텍스트
    'text_disabled': '#737373',    # 비활성 텍스트
    
    # Chart colors
    'grid': '#2a2a2a',             # 차트 그리드 라인
    'chart_bg': 'rgba(0,0,0,0)',   # 투명 차트 배경
}

# Regime-specific colors (레짐별 색상)
REGIME_COLORS = {
    'Expansion': COLOR_PALETTE['success'],
    'Late-cycle': COLOR_PALETTE['warning'],
    'Contraction': COLOR_PALETTE['danger'],
    'Stress': COLOR_PALETTE['danger_darker'],
}

# Alert level colors (알림 레벨별 색상)
ALERT_COLORS = {
    'Green': COLOR_PALETTE['success'],
    'Yellow': COLOR_PALETTE['warning'],
    'Red': COLOR_PALETTE['danger'],
}


# ============================================================================
# GLOBAL CSS - 앱 전체 스타일
# ============================================================================

def get_global_css() -> str:
    """
    Return the global CSS styles for the application.
    앱 전체에 적용되는 글로벌 CSS 반환
    """
    c = COLOR_PALETTE
    
    return f"""
    <style>
        /* ========== Force Dark Mode ========== */
        :root {{
            color-scheme: dark !important;
        }}
        
        /* ========== Base App Styling ========== */
        .stApp {{
            background: {c['bg_base']} !important;
            color: {c['text_primary']} !important;
        }}
        
        /* Override any light mode styles */
        .stApp, .main, .block-container, [data-testid="stAppViewContainer"],
        [data-testid="stHeader"], [data-testid="stToolbar"],
        [data-testid="stMainBlockContainer"] {{
            background-color: {c['bg_base']} !important;
        }}
        
        /* Main content area */
        .main .block-container {{
            background-color: {c['bg_base']} !important;
            color: {c['text_primary']} !important;
        }}
        
        /* ========== Sidebar Styling ========== */
        [data-testid="stSidebar"] {{
            background: {c['bg_base']};
            border-right: 1px solid {c['border']};
        }}
        
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] .stMarkdown span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCheckbox label span {{
            color: {c['text_muted']} !important;
            font-weight: 500;
        }}
        
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {{
            color: {c['text_primary']} !important;
        }}
        
        [data-testid="stSidebar"] a {{
            color: {c['primary']} !important;
            font-weight: 600;
        }}
        
        /* ========== Main Content Headers ========== */
        h1, h2, h3 {{
            color: {c['text_primary']} !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        /* ========== Body Text ========== */
        p, span, label, .stMarkdown {{
            color: {c['text_secondary']} !important;
        }}
        
        /* ========== Metric Cards ========== */
        [data-testid="stMetricValue"] {{
            color: {c['text_primary']} !important;
            font-weight: 700;
        }}
        
        [data-testid="stMetricLabel"] {{
            color: {c['text_muted']} !important;
        }}
        
        /* ========== Buttons ========== */
        .stButton > button {{
            background: linear-gradient(135deg, {c['bg_elevated']} 0%, {c['bg_card']} 100%);
            color: white !important;
            border: 1px solid {c['border_light']};
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        
        .stButton > button:hover {{
            background: linear-gradient(135deg, {c['bg_hover']} 0%, {c['bg_elevated']} 100%);
            border-color: {c['neutral']};
            transform: translateY(-1px);
        }}
        
        /* ========== Alert Boxes ========== */
        .stAlert {{
            background-color: {c['bg_card']};
            border: 1px solid {c['bg_elevated']};
            border-radius: 8px;
        }}
        
        /* ========== Page Links ========== */
        [data-testid="stPageLink"] {{
            background: linear-gradient(135deg, {c['bg_card']} 0%, {c['bg_elevated']} 100%);
            border: 1px solid {c['border_light']};
            border-radius: 8px;
            padding: 8px 16px;
            margin: 4px 0;
            transition: all 0.3s ease;
        }}
        
        [data-testid="stPageLink"]:hover {{
            background: linear-gradient(135deg, {c['bg_elevated']} 0%, {c['bg_hover']} 100%);
            border-color: {c['primary']};
            transform: translateY(-2px);
        }}
        
        [data-testid="stPageLink"] p {{
            color: {c['text_primary']} !important;
            font-weight: 600;
        }}
        
        /* ========== Hide Streamlit Branding ========== */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* ========== Sidebar Home Link (app -> 홈) ========== */
        [data-testid="stSidebarNav"] ul li:first-child a span,
        [data-testid="stSidebarNav"] a[href="/"] span,
        [data-testid="stSidebarNav"] a[href="./"] span {{
            font-size: 0 !important;
        }}
        [data-testid="stSidebarNav"] ul li:first-child a span::before,
        [data-testid="stSidebarNav"] a[href="/"] span::before,
        [data-testid="stSidebarNav"] a[href="./"] span::before {{
            content: "🏠 홈";
            font-size: 1rem;
            visibility: visible;
            color: {c['text_primary']};
            font-weight: 600;
        }}
        
        /* Also target by content if needed */
        [data-testid="stSidebarNav"] li a span {{
            /* Ensure proper text display */
        }}
        
        /* ========== Custom Scrollbar ========== */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-thumb {{
            background: {c['bg_elevated']};
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-track {{
            background: {c['bg_base']};
        }}
        
        /* ========== Tab Styling ========== */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 12px;
            padding-bottom: 4px;
            border-bottom: 1px solid {c['border']};
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            color: {c['text_muted']};
            border-radius: 8px 8px 0 0;
            padding: 10px 16px;
            transition: all 0.2s ease;
            border: 1px solid transparent;
            border-bottom: none;
        }}
        
        .stTabs [data-baseweb="tab"]:hover {{
            background-color: {c['bg_hover']};
            color: {c['text_primary']};
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {c['bg_elevated']};
            color: {c['primary']} !important;
            border: 1px solid {c['border']};
            border-bottom: 3px solid {c['primary']};
            font-weight: bold;
        }}
        
        .stTabs [data-baseweb="tab-highlight"] {{
            display: none;
        }}
        
        /* ========== Expander Styling ========== */
        .streamlit-expanderHeader {{
            background-color: {c['bg_card']};
            border-radius: 8px;
        }}
        
        .streamlit-expanderContent {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-top: none;
            border-radius: 0 0 8px 8px;
        }}
        
        /* ========== Divider ========== */
        hr {{
            border-color: {c['border']};
        }}
        
        /* ========== Metric Container - Force Dark Background ========== */
        [data-testid="stMetric"],
        [data-testid="metric-container"] {{
            background-color: {c['bg_card']} !important;
            padding: 16px !important;
            border-radius: 8px !important;
            border: 1px solid {c['border']} !important;
        }}
        
        /* ========== Column Containers ========== */
        [data-testid="column"] > div {{
            background-color: transparent !important;
        }}
        
        /* ========== All Card Backgrounds ========== */
        .stMarkdown, .element-container {{
            background-color: transparent !important;
        }}
        
        /* ========== File Uploader ========== */
        [data-testid="stFileUploader"] {{
            background-color: {c['bg_card']};
            border: 1px dashed {c['border_light']};
            border-radius: 8px;
            padding: 16px;
        }}
        
        /* ========== Text Input ========== */
        .stTextInput > div > div {{
            background-color: {c['bg_card']};
            border-color: {c['border']};
        }}
        
        /* ========== Checkbox ========== */
        .stCheckbox {{
            background-color: transparent;
        }}
        
        /* ========== Block Quote (Philosophy) ========== */
        blockquote {{
            background-color: {c['bg_card']};
            border-left: 4px solid {c['primary']};
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            margin: 8px 0;
        }}
        
        blockquote p {{
            color: {c['text_secondary']} !important;
        }}
    </style>
    """


# ============================================================================
# PAGE HEADER COMPONENT - 페이지 헤더 컴포넌트
# ============================================================================

def render_page_header(
    icon: str,
    title: str,
    subtitle: str,
    philosophy: Optional[str] = None,
) -> None:
    """
    Render a consistent page header across all pages.
    모든 페이지에 일관된 헤더 렌더링
    
    Args:
        icon: Emoji icon for the page
        title: Page title
        subtitle: Short subtitle/description
        philosophy: Optional philosophy quote in blockquote style
    """
    st.title(f"{icon} {title}")
    st.markdown(subtitle)
    
    if philosophy:
        st.markdown(f"> {philosophy}")
    
    st.markdown("---")


# ============================================================================
# INFO CARD COMPONENT - 정보 카드 컴포넌트
# ============================================================================

def render_info_box(
    content: str,
    title: Optional[str] = None,
    border_color: Optional[str] = None,
) -> None:
    """
    Render a styled info box with optional title.
    스타일이 적용된 정보 박스 렌더링
    
    Args:
        content: Main content text
        title: Optional title
        border_color: Border accent color (default: primary)
    """
    c = COLOR_PALETTE
    border = border_color or c['primary']
    
    title_html = f'<h4 style="color: {c["text_muted"]}; margin-bottom: 8px;">{title}</h4>' if title else ''
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {c['bg_card']}, {c['bg_elevated']});
        border-left: 4px solid {border};
        border-radius: 0 12px 12px 0;
        padding: 16px 20px;
        margin-bottom: 16px;
    ">
        {title_html}
        <p style="color: {c['text_secondary']}; font-size: 1.05em; margin: 0;">
            {content}
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_numbered_list(
    items: list,
    accent_color: Optional[str] = None,
) -> None:
    """
    Render a styled numbered list.
    스타일이 적용된 번호 리스트 렌더링
    
    Args:
        items: List of text items
        accent_color: Color for the numbers (default: primary)
    """
    c = COLOR_PALETTE
    color = accent_color or c['primary']
    
    for i, item in enumerate(items, 1):
        st.markdown(f"""
        <div style="
            background: {c['bg_card']};
            border-left: 3px solid {color};
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: 0 8px 8px 0;
        ">
            <span style="color: {color}; font-weight: bold;">{i}.</span>
            <span style="color: {c['text_secondary']};">{item}</span>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# SCORE DISPLAY COMPONENT - 점수 표시 컴포넌트
# ============================================================================

def render_score_display(
    score: float,
    max_score: int = 100,
    label: Optional[str] = None,
) -> None:
    """
    Render a large centered score display.
    큰 점수를 중앙에 표시
    
    Args:
        score: Current score value
        max_score: Maximum score (default: 100)
        label: Optional label text
    """
    c = COLOR_PALETTE
    
    # Determine color based on score
    if score < 50:
        color = c['success']
    elif score < 75:
        color = c['warning']
    else:
        color = c['danger']
    
    label_html = f'<div style="color: {c["text_muted"]}; margin-top: 8px;">{label}</div>' if label else ''
    
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 24px;
        background: {c['bg_card']};
        border-radius: 12px;
        border: 2px solid {color};
    ">
        <span style="font-size: 3em; color: {color}; font-weight: bold;">{score:.0f}</span>
        <span style="font-size: 1.5em; color: {c['text_muted']};">/{max_score}</span>
        {label_html}
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# CHART COLORS - 차트 색상 참조
# ============================================================================

def get_chart_colors() -> dict:
    """
    Return colors optimized for Plotly charts.
    Plotly 차트에 최적화된 색상 반환
    """
    c = COLOR_PALETTE
    return {
        'primary': c['primary'],
        'secondary': c['secondary'],
        'success': c['success'],
        'warning': c['warning'],
        'danger': c['danger'],
        'neutral': c['neutral'],
        'bg_dark': c['bg_card'],
        'bg_light': c['text_secondary'],
        'grid': c['grid'],
    }
