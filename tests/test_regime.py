"""Unit tests for regime classification."""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Regime
from indicators.regime import RegimeClassifier, calculate_regime_scores

@pytest.fixture
def expansion_data():
    dates = pd.date_range('2020-01-01', periods=300, freq='W')
    return {
        'credit_growth': pd.Series(np.linspace(100, 150, 300), index=dates),  # Growing
        'spread': pd.Series(np.linspace(5, 3, 300), index=dates),  # Tightening
        'vix': pd.Series(np.full(300, 15), index=dates),  # Low
    }

@pytest.fixture
def stress_data():
    dates = pd.date_range('2020-01-01', periods=800, freq='D')
    return {
        'credit_growth': pd.Series(np.linspace(100, 95, 800), index=dates),
        'spread': pd.Series(np.linspace(3, 8, 800), index=dates),
        'vix': pd.Series(np.linspace(15, 45, 800), index=dates),
        'equity': pd.Series(np.linspace(4000, 3500, 800), index=dates),
    }

def test_classifier_expansion(expansion_data):
    classifier = RegimeClassifier()
    result = classifier.classify(expansion_data)
    assert result.primary_regime in [Regime.EXPANSION, Regime.LATE_CYCLE]
    assert len(result.explanations) <= 3

def test_classifier_stress(stress_data):
    classifier = RegimeClassifier()
    result = classifier.classify(stress_data)
    assert result.primary_regime in [Regime.CONTRACTION, Regime.STRESS]

def test_regime_scores():
    dates = pd.date_range('2020-01-01', periods=200, freq='W')
    data = {'credit_growth': pd.Series(np.ones(200) * 100, index=dates)}
    scores = calculate_regime_scores(data)
    assert 0 <= scores.expansion <= 100
    assert 0 <= scores.stress <= 100

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
