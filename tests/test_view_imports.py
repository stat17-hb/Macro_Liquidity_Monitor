"""Smoke tests for view-module imports."""
import importlib
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


VIEW_MODULES = [
    'views.balance_sheet',
    'views.collateral',
    'views.marginal_belief',
    'views.leverage',
    'views.alerts',
    'views.qt_monitoring',
]


def test_view_imports_do_not_render_streamlit_ui(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Streamlit UI was rendered during module import")

    for attr in ['title', 'markdown', 'warning', 'info', 'success', 'metric']:
        monkeypatch.setattr(st, attr, fail)

    for module_name in VIEW_MODULES:
        sys.modules.pop(module_name, None)
        importlib.import_module(module_name)
