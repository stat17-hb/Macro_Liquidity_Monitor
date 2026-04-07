"""Tests for dashboard data assembly pipeline."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline import get_regime_inputs, merge_indicator_frames, prepare_data_dict


def test_custom_indicator_frames_are_merged_into_data_dict():
    base_df = pd.DataFrame({
        'date': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'value': [15.0, 16.0],
        'indicator': ['VIX', 'VIX'],
    })
    custom_df = pd.DataFrame({
        'date': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'value': [100.0, 101.0],
        'indicator': ['Custom Liquidity', 'Custom Liquidity'],
    })

    combined_df = merge_indicator_frames(base_df, [custom_df])
    data_dict = prepare_data_dict(combined_df)

    assert 'vix' in data_dict
    assert 'custom_liquidity' in data_dict
    assert data_dict['custom_liquidity'].iloc[-1] == 101.0


def test_custom_rows_override_base_values_for_same_indicator_and_date():
    base_df = pd.DataFrame({
        'date': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'value': [15.0, 16.0],
        'indicator': ['VIX', 'VIX'],
    })
    custom_df = pd.DataFrame({
        'date': pd.to_datetime(['2024-01-02']),
        'value': [30.0],
        'indicator': ['VIX'],
    })

    combined_df = merge_indicator_frames(base_df, [custom_df])
    data_dict = prepare_data_dict(combined_df)

    assert len(combined_df) == 2
    assert data_dict['vix'].loc[pd.Timestamp('2024-01-02')] == 30.0


def test_prepare_data_dict_adds_canonical_regime_aliases():
    df = pd.DataFrame({
        'date': pd.to_datetime([
            '2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01',
        ]),
        'value': [100.0, 3.5, 20.0, 5000.0],
        'indicator': ['Bank Credit', 'HY Spread', 'VIX', 'S&P 500'],
    })

    data_dict = prepare_data_dict(df)
    regime_inputs = get_regime_inputs(data_dict)

    assert data_dict['credit'] is data_dict['bank_credit']
    assert data_dict['credit_growth'] is data_dict['bank_credit']
    assert data_dict['spread'] is data_dict['hy_spread']
    assert data_dict['equity'] is data_dict['sp500']
    assert regime_inputs['credit_growth'] is data_dict['credit_growth']
    assert regime_inputs['spread'] is data_dict['spread']
