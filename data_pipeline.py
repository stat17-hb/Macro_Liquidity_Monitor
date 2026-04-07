"""
Shared data loading and assembly pipeline for the dashboard.
"""
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

from config import INDICATOR_LABEL_TO_KEY
from loaders import FREDLoader, SampleDataLoader, YFinanceLoader


REQUIRED_DATA_COLUMNS = ['date', 'value', 'indicator']


@st.cache_data(ttl=3600 * 6)
def load_source_data(
    use_sample: bool = True,
    load_fed_balance_sheet: bool = False,
    fred_api_key: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """Load base dashboard data from sample or live sources."""
    if use_sample:
        return SampleDataLoader().load_all(), ["샘플 데이터를 사용합니다."]

    data_frames: List[pd.DataFrame] = []
    load_status: List[str] = []

    fred = FREDLoader(api_key=fred_api_key)
    if fred.is_ready():
        try:
            fred_data = fred.load_all_minimum_set()

            if load_fed_balance_sheet and not fred_data.empty:
                try:
                    fed_bs_extra = fred.load('H41RESPPALDNNWW')
                    if not fed_bs_extra.empty:
                        fred_data = pd.concat(
                            [fred_data, fed_bs_extra],
                            ignore_index=True,
                        )
                except Exception:
                    pass

            if not fred_data.empty:
                data_frames.append(fred_data)
                indicator_count = len(fred_data['indicator'].unique())
                load_status.append(f"FRED: {indicator_count}개 지표 로딩됨")
        except Exception as error:
            load_status.append(f"FRED: 로딩 실패 - {error}")
    else:
        load_status.append(f"FRED: {fred.get_status_message()}")

    yf = YFinanceLoader()
    if yf.is_available():
        try:
            yf_data = yf.load_all_minimum_set()
            if not yf_data.empty:
                data_frames.append(yf_data)
                indicator_count = len(yf_data['indicator'].unique())
                load_status.append(f"yfinance: {indicator_count}개 지표 로딩됨")
        except Exception as error:
            load_status.append(f"yfinance: 로딩 실패 - {error}")

    if data_frames:
        return pd.concat(data_frames, ignore_index=True), load_status

    load_status.append("실시간 데이터를 가져올 수 없어 샘플 데이터를 사용합니다.")
    return SampleDataLoader().load_all(), load_status


def merge_indicator_frames(
    base_df: pd.DataFrame,
    custom_frames: Optional[Sequence[pd.DataFrame]] = None,
) -> pd.DataFrame:
    """Merge standardized custom indicator frames into the base dataset."""
    frames: List[pd.DataFrame] = []

    if base_df is not None and not base_df.empty:
        frames.append(base_df.loc[:, REQUIRED_DATA_COLUMNS].copy())

    for frame in custom_frames or []:
        if frame is None or frame.empty:
            continue
        frames.append(frame.loc[:, REQUIRED_DATA_COLUMNS].copy())

    if not frames:
        return pd.DataFrame(columns=REQUIRED_DATA_COLUMNS)

    combined_df = pd.concat(frames, ignore_index=True)
    combined_df['_merge_order'] = range(len(combined_df))
    combined_df['date'] = pd.to_datetime(combined_df['date'])
    combined_df = combined_df.dropna(subset=REQUIRED_DATA_COLUMNS)
    combined_df = combined_df.sort_values(
        ['indicator', 'date', '_merge_order'],
        kind='mergesort',
    )
    combined_df = combined_df.drop_duplicates(
        subset=['indicator', 'date'],
        keep='last',
    )
    combined_df = combined_df.drop(columns=['_merge_order'])
    return combined_df.reset_index(drop=True)


def _normalize_indicator_key(indicator: str) -> str:
    return indicator.strip().lower().replace(' ', '_')


def prepare_data_dict(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Convert long-format DataFrame to dict of aligned series."""
    data_dict: Dict[str, pd.Series] = {}

    if df is None or df.empty:
        return data_dict

    working_df = df.loc[:, REQUIRED_DATA_COLUMNS].copy()
    working_df['date'] = pd.to_datetime(working_df['date'])

    for indicator in working_df['indicator'].dropna().unique():
        indicator_df = working_df[working_df['indicator'] == indicator].copy()
        indicator_df = indicator_df.sort_values('date')
        indicator_df = indicator_df.drop_duplicates(subset='date', keep='last')
        series = pd.Series(
            indicator_df['value'].values,
            index=pd.DatetimeIndex(indicator_df['date']),
            name=indicator,
        )

        key = INDICATOR_LABEL_TO_KEY.get(indicator, _normalize_indicator_key(indicator))
        data_dict[key] = series

    if 'bank_credit' in data_dict:
        data_dict['credit'] = data_dict['bank_credit']
        data_dict['credit_growth'] = data_dict['bank_credit']

    if 'hy_spread' in data_dict:
        data_dict['spread'] = data_dict['hy_spread']
    elif 'hy_etf' in data_dict:
        data_dict['spread'] = data_dict['hy_etf']

    if 'sp500' in data_dict:
        data_dict['equity'] = data_dict['sp500']

    if 'pe_ratio' in data_dict:
        data_dict['valuation'] = data_dict['pe_ratio']

    if 'forward_eps' in data_dict:
        data_dict['earnings'] = data_dict['forward_eps']

    return data_dict


def get_regime_inputs(data_dict: Dict[str, pd.Series]) -> Dict[str, Optional[pd.Series]]:
    """Build the canonical regime classifier input dict."""
    return {
        'credit_growth': data_dict.get('credit_growth'),
        'spread': data_dict.get('spread'),
        'vix': data_dict.get('vix'),
        'equity': data_dict.get('equity'),
    }


def build_dashboard_dataset(
    use_sample: bool = True,
    load_fed_balance_sheet: bool = False,
    fred_api_key: Optional[str] = None,
    custom_frames: Optional[Sequence[pd.DataFrame]] = None,
) -> Tuple[pd.DataFrame, Dict[str, pd.Series], List[str]]:
    """Load, merge, and normalize all dashboard data."""
    base_df, load_status = load_source_data(
        use_sample=use_sample,
        load_fed_balance_sheet=load_fed_balance_sheet,
        fred_api_key=fred_api_key,
    )
    combined_df = merge_indicator_frames(base_df, custom_frames=custom_frames)
    data_dict = prepare_data_dict(combined_df)
    return combined_df, data_dict, load_status
