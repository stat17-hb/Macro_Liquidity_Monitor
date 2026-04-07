"""Tests for report generation helpers."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime
from components.reports import generate_vulnerability_report


def test_vulnerability_report_includes_valuation_and_rate_risks():
    metrics = {
        'credit_growth_3m': None,
        'spread_zscore': 0.0,
        'vix_percentile': 50.0,
        'pe_zscore': 1.8,
        'real_yield': -0.5,
    }

    vulnerabilities = generate_vulnerability_report(Regime.EXPANSION, metrics)
    titles = [item['title'] for item in vulnerabilities]

    assert '밸류에이션 과열' in titles
    assert '금리 상승 취약' in titles
