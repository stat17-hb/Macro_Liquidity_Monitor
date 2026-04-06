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
    'success': '#10b981',          # Green - 성공, 안전, 확장 (에메랄드 그린)
    'success_dark': '#059669',     # Dark Green
    'warning': '#f59e0b',          # Amber - 경고, 주의
    'warning_light': '#fbbf24',    # Light Amber
    'danger': '#ef4444',           # Red - 위험, 오류
    'danger_dark': '#dc2626',      # Dark Red
    'danger_darker': '#7f1d1d',    # Very Dark Red - Stress
    
    # Neutral colors
    'neutral': '#6b7280',          # Gray - 비활성, 중립
    'neutral_light': '#9ca3af',    # Light Gray
    'neutral_dark': '#4b5563',     # Dark Gray
    
    # Background colors (Soft Dark Theme)
    'bg_base': '#121212',          # 앱 전체 배경 (매우 부드러운 다크 그레이)
    'bg_card': '#1e1e1e',          # 카드 배경 (살짝 입체감)
    'bg_elevated': '#2c2c2e',      # 강조 스택 (가장 튀어나온 요소)
    'bg_hover': '#323234',         # 호버 상태
    
    # Border colors (Neutral Gray, Very Subtle)
    'border': '#2c2c2e',           # 기본 테두리
    'border_light': '#3a3a3c',     # 밝은 테두리
    
    # Text colors (Neutral)
    'text_primary': '#f5f5f7',     # 주요 텍스트 (완전 흰색보다 눈이 편한 오프화이트)
    'text_secondary': '#ebebf599', # 보조 텍스트 (약 60% 불투명도)
    'text_muted': '#ebebf54d',     # 흐린 텍스트 (약 30% 불투명도)
    'text_disabled': '#737373',    # 비활성 텍스트
    
    # Chart colors
    'grid': '#2c2c2e',             # 차트 그리드 라인
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
        /* ========== Font Import ========== */
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

        /* ========== Force Dark Mode & Font ========== */
        :root {{
            color-scheme: dark !important;
        }}
        
        * {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif !important;
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
            padding-top: 3rem; /* Add some breathing room at top */
        }}
        
        /* ========== Sidebar Styling ========== */
        [data-testid="stSidebar"] {{
            background: {c['bg_card']};
            border-right: none;
            box-shadow: 2px 0 10px rgba(0,0,0,0.2);
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
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }}
        
        /* ========== Body Text ========== */
        p, span, label, .stMarkdown {{
            color: {c['text_secondary']} !important;
            line-height: 1.6;
        }}
        
        /* ========== Metric Cards ========== */
        [data-testid="stMetricValue"] {{
            color: {c['text_primary']} !important;
            font-weight: 800 !important;
            font-size: 2em !important;
        }}
        
        [data-testid="stMetricLabel"] {{
            color: {c['text_muted']} !important;
            font-weight: 500 !important;
            font-size: 0.95em !important;
            margin-bottom: 4px;
        }}
        
        /* ========== Buttons ========== */
        .stButton > button {{
            background: {c['bg_elevated']};
            color: {c['text_primary']} !important;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            padding: 10px 20px;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .stButton > button:hover {{
            background: {c['bg_hover']};
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            color: #fff !important;
        }}
        
        /* ========== Alert Boxes ========== */
        .stAlert {{
            background-color: {c['bg_card']};
            border: transparent !important;
            border-radius: 16px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        /* ========== Page Links ========== */
        [data-testid="stPageLink"] {{
            background: {c['bg_card']} !important;
            border: transparent !important;
            border-radius: 12px;
            padding: 10px 16px;
            margin: 6px 0;
            transition: all 0.25s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        [data-testid="stPageLink"]:hover {{
            background: {c['bg_hover']} !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
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
            background: transparent;
        }}
        
        /* ========== Tab Styling ========== */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 12px;
            padding-bottom: 4px;
            border-bottom: none;
            background-color: transparent;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            color: {c['text_muted']};
            border-radius: 20px;
            padding: 8px 16px;
            transition: all 0.25s ease;
            border: none;
            font-weight: 600;
        }}
        
        .stTabs [data-baseweb="tab"]:hover {{
            background-color: {c['bg_elevated']};
            color: {c['text_primary']};
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {c['bg_card']};
            color: {c['text_primary']} !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            border: 1px solid {c['border']};
            font-weight: 700;
        }}
        
        .stTabs [data-baseweb="tab-highlight"] {{
            display: none;
        }}
        
        /* ========== Expander Styling ========== */
        .streamlit-expanderHeader {{
            background-color: {c['bg_card']};
            border-radius: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.25s ease;
        }}
        .streamlit-expanderHeader:hover {{
            background-color: {c['bg_hover']};
        }}
        
        .streamlit-expanderContent {{
            background-color: {c['bg_card']};
            border: none;
            border-radius: 0 0 16px 16px;
        }}
        
        /* ========== Divider ========== */
        hr {{
            border: none;
            height: 0;
            margin: 0; /* Remove lines completely to rely on whitespace */
            background-color: transparent;
        }}
        
        /* ========== Metric Container - Soft UI ========== */
        [data-testid="stMetric"],
        [data-testid="metric-container"] {{
            background-color: {c['bg_card']} !important;
            padding: 20px !important;
            border-radius: 20px !important;
            border: transparent !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.15) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        
        [data-testid="stMetric"]:hover,
        [data-testid="metric-container"]:hover {{
            transform: translateY(-4px) !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
            background-color: {c['bg_hover']} !important;
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
            border: 2px dashed {c['border']};
            border-radius: 16px;
            padding: 20px;
            transition: all 0.25s ease;
        }}
        [data-testid="stFileUploader"]:hover {{
            border-color: {c['primary']};
            background-color: {c['bg_hover']};
        }}
        
        /* ========== Text Input ========== */
        .stTextInput > div > div {{
            background-color: {c['bg_card']};
            border-color: {c['border']};
            border-radius: 12px;
        }}
        
        /* ========== Checkbox ========== */
        .stCheckbox {{
            background-color: transparent;
        }}
        
        /* ========== Block Quote (Philosophy) ========== */
        blockquote {{
            background-color: {c['bg_card']};
            border-left: 4px solid {c['primary']};
            padding: 16px 20px;
            border-radius: 0 16px 16px 0;
            margin: 16px 0 24px 0;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        
        blockquote p {{
            color: {c['text_secondary']} !important;
            font-size: 1.05em;
            margin: 0;
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
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.15);
        transition: transform 0.25s ease;
    " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
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
