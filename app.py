"""
Liquidity Monitoring Dashboard - Main Entry Point
유동성 모니터링 대시보드 - 메인 앱
"""
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PAGE_CONFIG, config
from data_pipeline import build_dashboard_dataset, get_regime_inputs
from indicators import RegimeClassifier
from loaders import CSVLoader
from components.styles import get_global_css
from views.dashboard_sections import (
    DIAGNOSTIC_VIEW_OPTIONS,
    PRIMARY_SECTION_OPTIONS,
    build_view_context,
    render_action_center,
    render_command_center,
    render_diagnostics,
    render_framework_expander,
)


st.set_page_config(
    page_title=PAGE_CONFIG['page_title'],
    page_icon=PAGE_CONFIG['page_icon'],
    layout=PAGE_CONFIG['layout'],
    initial_sidebar_state=PAGE_CONFIG['initial_sidebar_state'],
)
st.markdown(get_global_css(), unsafe_allow_html=True)


def _initialize_session_state() -> None:
    if 'custom_indicator_frames' not in st.session_state:
        st.session_state['custom_indicator_frames'] = []
    if 'ui_state' not in st.session_state:
        st.session_state['ui_state'] = {
            'primary_section': 'Command Center',
            'diagnostic_view': 'Liquidity Engine',
            'global_timeframe': '3Y',
            'show_framework': False,
        }
    if 'last_refresh_at' not in st.session_state:
        st.session_state['last_refresh_at'] = pd.Timestamp.now()


def _render_sidebar() -> tuple[bool, bool]:
    ui_state = st.session_state['ui_state']

    with st.sidebar:
        st.title("Liquidity Monitor")

        st.subheader("데이터 소스")
        use_sample = st.checkbox(
            "샘플 데이터 사용",
            value=False,
            help="체크 해제 시 실시간 데이터 로딩을 시도합니다.",
        )
        load_fed_balance_sheet = st.checkbox(
            "Fed 대차대조표 포함",
            value=True,
            help="Reserve Balances, Reverse Repo, TGA, Fed Lending 포함",
        )
        timeframe = st.segmented_control(
            "전역 시간 범위",
            options=['6M', '1Y', '3Y', '5Y', 'Full'],
            default=ui_state.get('global_timeframe', '3Y'),
            selection_mode='single',
        )
        if timeframe:
            ui_state['global_timeframe'] = timeframe

        if st.button("데이터 새로고침", type="primary", use_container_width=True):
            st.session_state['custom_indicator_frames'] = []
            st.session_state['last_refresh_at'] = pd.Timestamp.now()
            st.cache_data.clear()
            st.rerun()

        st.subheader("커스텀 CSV")
        uploaded_file = st.file_uploader(
            "CSV 파일 업로드",
            type=['csv'],
            help="날짜와 값 컬럼이 포함된 CSV 파일",
        )

        if uploaded_file:
            indicator_name = st.text_input("지표 이름", value="Custom")
            if st.button("지표 추가", use_container_width=True):
                try:
                    csv_loader = CSVLoader()
                    indicator_name = indicator_name.strip() or "Custom"
                    upload_df = csv_loader.read_upload_to_dataframe(uploaded_file)
                    validation = csv_loader.validate_upload(upload_df)

                    if not validation['valid']:
                        for error in validation['errors']:
                            st.error(f"업로드 검증 실패: {error}")
                    else:
                        custom_df = csv_loader.load_from_dataframe(upload_df, indicator_name)
                        existing_frames = [
                            frame for frame in st.session_state['custom_indicator_frames']
                            if frame.empty or frame['indicator'].iloc[0] != indicator_name
                        ]
                        existing_frames.append(custom_df)
                        st.session_state['custom_indicator_frames'] = existing_frames
                        st.success(f"{len(custom_df)} 행 로드됨")
                except Exception as error:
                    st.error(f"로드 실패: {error}")

        if st.session_state['custom_indicator_frames']:
            custom_names = [
                frame['indicator'].iloc[0]
                for frame in st.session_state['custom_indicator_frames']
                if not frame.empty
            ]
            st.caption(f"세션 사용자 지표: {', '.join(custom_names)}")

    return use_sample, load_fed_balance_sheet


_initialize_session_state()
use_sample, load_fed_balance_sheet = _render_sidebar()

df, data_dict, load_status = build_dashboard_dataset(
    use_sample=use_sample,
    load_fed_balance_sheet=load_fed_balance_sheet,
    fred_api_key=config.fred_api_key,
    custom_frames=st.session_state['custom_indicator_frames'],
)

classifier = RegimeClassifier()
regime_data = get_regime_inputs(data_dict)
regime_result = classifier.classify(regime_data)

try:
    regime_history_df = classifier.classify_history(regime_data, lookback_years=2)
except Exception:
    regime_history_df = None

st.session_state['data'] = df
st.session_state['data_dict'] = data_dict
st.session_state['regime_result'] = regime_result
st.session_state['regime_history_df'] = regime_history_df

view_context = build_view_context(
    data_dict=data_dict,
    use_sample=use_sample,
    fed_bs_enabled=load_fed_balance_sheet,
    custom_indicator_count=len(st.session_state['custom_indicator_frames']),
)
view_context['load_meta']['refreshed_at'] = st.session_state['last_refresh_at']

st.title("유동성 모니터링 대시보드")
st.caption("데스크톱 분석용 커맨드 센터")
render_framework_expander()

error_statuses = [status for status in load_status if any(keyword in status for keyword in ['실패', '필요', '미설치'])]
info_statuses = [status for status in load_status if status not in error_statuses]
if error_statuses:
    st.warning(' | '.join(error_statuses))
if info_statuses:
    st.caption(' · '.join(info_statuses))

primary_section = st.segmented_control(
    "Primary View",
    options=PRIMARY_SECTION_OPTIONS,
    default=st.session_state['ui_state'].get('primary_section', 'Command Center'),
    selection_mode='single',
    label_visibility='collapsed',
)
if primary_section:
    st.session_state['ui_state']['primary_section'] = primary_section

if st.session_state['ui_state']['primary_section'] == 'Diagnostics':
    diagnostic_view = st.segmented_control(
        "Diagnostics",
        options=DIAGNOSTIC_VIEW_OPTIONS,
        default=st.session_state['ui_state'].get('diagnostic_view', 'Liquidity Engine'),
        selection_mode='single',
        label_visibility='collapsed',
    )
    if diagnostic_view:
        st.session_state['ui_state']['diagnostic_view'] = diagnostic_view

st.session_state['ui_state']['show_framework'] = False

if st.session_state['ui_state']['primary_section'] == 'Command Center':
    render_command_center(
        data_dict=data_dict,
        regime_result=regime_result,
        regime_history_df=regime_history_df,
        load_meta=view_context['load_meta'],
        alert_config=view_context['alert_config'],
    )
elif st.session_state['ui_state']['primary_section'] == 'Diagnostics':
    render_diagnostics(
        data_dict=data_dict,
        regime_result=regime_result,
        alert_config=view_context['alert_config'],
        diagnostic_view=st.session_state['ui_state']['diagnostic_view'],
    )
else:
    render_action_center(
        data_dict=data_dict,
        regime_result=regime_result,
    )
