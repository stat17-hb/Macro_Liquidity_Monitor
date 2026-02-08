"""
Sample data generator for offline demo.
오프라인 데모용 샘플 데이터 생성기

네트워크 없이도 앱이 동작하도록 합성 데이터 생성
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import pandas as pd
import numpy as np

from .base import DataLoader, DataSchema


def generate_sample_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    seed: int = 42,
) -> Dict[str, pd.DataFrame]:
    """
    Generate synthetic sample data for all minimum set indicators.
    
    The data is designed to show realistic patterns:
    - Expansion phase (2020-2021): Credit growth, low spreads, low VIX
    - Late-cycle phase (2021-2022): Valuation stretched, earnings lagging
    - Contraction phase (2022-2023): Credit tightening, spread widening
    - Stress events: Periodic spikes
    
    Args:
        start_date: Start date (default: 5 years ago)
        end_date: End date (default: today)
        seed: Random seed for reproducibility
        
    Returns:
        Dict mapping indicator names to DataFrames
    """
    np.random.seed(seed)
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=365 * 5)
    
    # Generate date range (weekly for most, daily for VIX/S&P)
    dates_weekly = pd.date_range(start=start_date, end=end_date, freq='W')
    dates_daily = pd.date_range(start=start_date, end=end_date, freq='B')
    
    n_weekly = len(dates_weekly)
    n_daily = len(dates_daily)
    
    # Time indices normalized to [0, 1]
    t_weekly = np.linspace(0, 1, n_weekly)
    t_daily = np.linspace(0, 1, n_daily)
    
    # ---------------------------------------------------------------------
    # Generate synthetic indicators
    # ---------------------------------------------------------------------
    
    data = {}
    
    # Fed Total Assets (trillions) - expansion then plateau
    fed_trend = 4.0 + 4.0 * (1 - np.exp(-3 * t_weekly)) + np.random.normal(0, 0.1, n_weekly).cumsum() * 0.01
    fed_trend = np.maximum(fed_trend, 4.0)  # Floor at 4T
    data['Fed Total Assets'] = pd.DataFrame({
        'date': dates_weekly,
        'value': fed_trend * 1e12,  # In dollars
        'indicator': 'Fed Total Assets',
    })
    
    # Bank Credit (trillions) - follows Fed with lag
    bank_trend = 10.0 + 2.0 * t_weekly + 0.5 * np.sin(2 * np.pi * t_weekly * 2)
    bank_trend += np.random.normal(0, 0.05, n_weekly).cumsum() * 0.01
    data['Bank Credit'] = pd.DataFrame({
        'date': dates_weekly,
        'value': bank_trend * 1e12,
        'indicator': 'Bank Credit',
    })
    
    # M2 (trillions) - massive expansion 2020, then flat/decline
    m2_trend = 15.0 + 6.0 * (1 - np.exp(-5 * t_weekly)) - 0.5 * np.maximum(t_weekly - 0.6, 0)
    m2_trend += np.random.normal(0, 0.02, n_weekly).cumsum() * 0.01
    data['M2'] = pd.DataFrame({
        'date': dates_weekly,
        'value': m2_trend * 1e12,
        'indicator': 'M2',
    })
    
    # HY Spread (bps) - low in expansion, spikes in stress
    hy_base = 400 - 100 * t_weekly + 200 * np.maximum(t_weekly - 0.4, 0) ** 2
    # Add stress spikes
    hy_spikes = np.zeros(n_weekly)
    spike_idx = [int(n_weekly * 0.15), int(n_weekly * 0.5), int(n_weekly * 0.85)]
    for idx in spike_idx:
        if idx < n_weekly:
            spike_len = min(8, n_weekly - idx)
            hy_spikes[idx:idx+spike_len] = np.exp(-np.arange(spike_len) * 0.3) * 200
    hy_spread = hy_base + hy_spikes + np.random.normal(0, 20, n_weekly)
    hy_spread = np.clip(hy_spread, 200, 1000)
    data['HY Spread'] = pd.DataFrame({
        'date': dates_weekly,
        'value': hy_spread / 100,  # As percentage
        'indicator': 'HY Spread',
    })
    
    # IG Spread (bps) - similar pattern but lower magnitude
    ig_spread = hy_spread * 0.3 + np.random.normal(0, 5, n_weekly)
    ig_spread = np.clip(ig_spread, 50, 300)
    data['IG Spread'] = pd.DataFrame({
        'date': dates_weekly,
        'value': ig_spread / 100,
        'indicator': 'IG Spread',
    })
    
    # VIX - daily, mean-reverting with spikes
    vix = np.zeros(n_daily)
    vix[0] = 18
    for i in range(1, n_daily):
        vix[i] = vix[i-1] + 0.1 * (18 - vix[i-1]) + np.random.normal(0, 1.5)
    # Add stress spikes
    spike_days = [int(n_daily * 0.15), int(n_daily * 0.5), int(n_daily * 0.85)]
    for idx in spike_days:
        if idx < n_daily:
            spike_len = min(20, n_daily - idx)
            vix[idx:idx+spike_len] += np.exp(-np.arange(spike_len) * 0.1) * 25
    vix = np.clip(vix, 10, 80)
    data['VIX'] = pd.DataFrame({
        'date': dates_daily,
        'value': vix,
        'indicator': 'VIX',
    })
    
    # S&P 500 - upward trend with corrections
    sp500_returns = np.random.normal(0.0003, 0.01, n_daily)
    # Add corrections
    correction_starts = [int(n_daily * 0.15), int(n_daily * 0.5)]
    for idx in correction_starts:
        if idx < n_daily:
            corr_len = min(40, n_daily - idx)
            sp500_returns[idx:idx+corr_len] -= 0.008 * np.exp(-np.arange(corr_len) * 0.05)
    sp500 = 3000 * np.exp(np.cumsum(sp500_returns) + 0.08 * t_daily)  # 8% trend
    data['S&P 500'] = pd.DataFrame({
        'date': dates_daily,
        'value': sp500,
        'indicator': 'S&P 500',
    })
    
    # Real Yield 10Y (%) - negative in 2020-21, rising 2022+
    real_yield = -1.0 + 2.5 * (t_weekly - 0.3) ** 2 + np.random.normal(0, 0.1, n_weekly)
    real_yield = np.clip(real_yield, -1.5, 2.5)
    data['Real Yield 10Y'] = pd.DataFrame({
        'date': dates_weekly,
        'value': real_yield,
        'indicator': 'Real Yield 10Y',
    })
    
    # Breakeven 10Y (%) - inflation expectations
    breakeven = 2.0 + 0.5 * np.sin(4 * np.pi * t_weekly) + np.random.normal(0, 0.1, n_weekly)
    breakeven = np.clip(breakeven, 1.0, 3.5)
    data['Breakeven 10Y'] = pd.DataFrame({
        'date': dates_weekly,
        'value': breakeven,
        'indicator': 'Breakeven 10Y',
    })
    
    # Forward EPS (S&P 500) - lagging indicator
    eps_trend = 180 + 30 * t_weekly + 10 * np.sin(2 * np.pi * t_weekly)
    eps_trend += np.random.normal(0, 2, n_weekly).cumsum() * 0.05
    data['Forward EPS'] = pd.DataFrame({
        'date': dates_weekly,
        'value': eps_trend,
        'indicator': 'Forward EPS',
    })
    
    # P/E Ratio - derived but could be standalone
    # Match weekly dates with closest S&P price
    sp500_weekly = sp500[::5][:n_weekly]  # Approximate weekly
    if len(sp500_weekly) > len(eps_trend):
        sp500_weekly = sp500_weekly[:len(eps_trend)]
    elif len(sp500_weekly) < len(eps_trend):
        eps_trend = eps_trend[:len(sp500_weekly)]
        dates_pe = dates_weekly[:len(sp500_weekly)]
    else:
        dates_pe = dates_weekly

    pe_ratio = sp500_weekly / eps_trend
    data['PE Ratio'] = pd.DataFrame({
        'date': dates_pe,
        'value': pe_ratio,
        'indicator': 'PE Ratio',
    })

    # =====================================================================
    # Fed Balance Sheet Indicators (new)
    # =====================================================================

    # Reserve Balances (WRESBAL) - billions
    # Pattern: ~3500B in 2020, decline to ~3200B by 2025
    resbal_trend = 3500 - 300 * t_weekly + 50 * np.sin(2 * np.pi * t_weekly)
    resbal_trend += np.random.normal(0, 10, n_weekly).cumsum() * 0.5
    resbal_trend = np.clip(resbal_trend, 3000, 3800)
    data['Reserve Balances'] = pd.DataFrame({
        'date': dates_weekly,
        'value': resbal_trend * 1e9,  # In dollars
        'indicator': 'Reserve Balances',
    })

    # Reverse Repo (RRPONTSYD) - billions
    # Pattern: Near 0 in 2020-2021, spike to 2300B in 2022-2023, decline to ~500B by 2025
    # Use logistic curve with spike
    rrp_base = 2300 / (1 + np.exp(-10 * (t_weekly - 0.4)))  # Logistic rise from 2020 to 2023
    rrp_decline = np.maximum(0, 2300 - 1800 * np.maximum(t_weekly - 0.6, 0))  # Decline from 2023
    rrp_combined = rrp_base * (1 - np.maximum(t_weekly - 0.6, 0)) + rrp_decline * np.maximum(t_weekly - 0.6, 0)
    rrp_combined += np.random.normal(0, 20, n_weekly)
    rrp_combined = np.clip(rrp_combined, 0, 2500)
    data['Reverse Repo'] = pd.DataFrame({
        'date': dates_weekly,
        'value': rrp_combined * 1e9,  # In dollars
        'indicator': 'Reverse Repo',
    })

    # TGA Balance (WTREGEN) - Treasury General Account - billions
    # Range 200B-800B with irregular patterns (government spending cycles)
    # Implement as oscillating around 500B with quarterly patterns
    tga_base = 500 + 150 * np.sin(8 * np.pi * t_weekly)  # ~2 year cycle at 8*pi frequency
    tga_irregular = 100 * np.sin(12 * np.pi * t_weekly)  # Higher frequency noise
    tga_combined = tga_base + tga_irregular
    tga_combined += np.random.normal(0, 15, n_weekly)
    tga_combined = np.clip(tga_combined, 200, 800)
    data['TGA Balance'] = pd.DataFrame({
        'date': dates_weekly,
        'value': tga_combined * 1e9,  # In dollars
        'indicator': 'TGA Balance',
    })

    # Fed Lending (WLCFLPCL) - billions
    # Pattern: Near 0 normally, spike to 150B during SVB crisis (March 2023), return to ~10B
    # March 2023 is roughly at t=0.35 (1.75 years into 5-year period)
    crisis_idx = int(n_weekly * 0.35)
    fed_lending = np.ones(n_weekly) * 5  # Baseline ~5B

    # Add SVB crisis spike centered at March 2023
    crisis_width = 12  # ~12 weeks for crisis window
    for i in range(max(0, crisis_idx - crisis_width), min(n_weekly, crisis_idx + 2*crisis_width)):
        distance = abs(i - crisis_idx) / crisis_width
        fed_lending[i] += 150 * np.exp(-2 * distance ** 2)  # Gaussian spike, peak 150B

    fed_lending += np.random.normal(0, 2, n_weekly)
    fed_lending = np.clip(fed_lending, 0, 160)
    data['Fed Lending'] = pd.DataFrame({
        'date': dates_weekly,
        'value': fed_lending * 1e9,  # In dollars
        'indicator': 'Fed Lending',
    })

    return data


class SampleDataLoader(DataLoader):
    """
    Sample data loader for offline demo.
    
    Uses synthetic data when real data sources are unavailable.
    """
    
    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        seed: int = 42,
    ):
        super().__init__(schema)
        self.seed = seed
        self._sample_data: Optional[Dict[str, pd.DataFrame]] = None
    
    def _ensure_data_loaded(self) -> None:
        """Ensure sample data is generated."""
        if self._sample_data is None:
            self._sample_data = generate_sample_data(seed=self.seed)
    
    def load(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load sample data for a given indicator.
        
        Args:
            ticker: Indicator name (e.g., 'VIX', 'Fed Total Assets')
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            DataFrame with columns: date, value, indicator
        """
        self._ensure_data_loaded()
        
        # Map common tickers to sample data keys
        ticker_map = {
            'WALCL': 'Fed Total Assets',
            'TOTBKCR': 'Bank Credit',
            'M2SL': 'M2',
            'BAMLH0A0HYM2': 'HY Spread',
            'BAMLC0A0CM': 'IG Spread',
            '^VIX': 'VIX',
            '^GSPC': 'S&P 500',
            'DFII10': 'Real Yield 10Y',
            'T10YIE': 'Breakeven 10Y',
            'WRESBAL': 'Reserve Balances',
            'RRPONTSYD': 'Reverse Repo',
            'WTREGEN': 'TGA Balance',
            'WLCFLPCL': 'Fed Lending',
        }
        
        # Try to find matching data
        key = ticker_map.get(ticker, ticker)
        
        if key not in self._sample_data:
            raise ValueError(f"Sample data not available for: {ticker}")
        
        df = self._sample_data[key].copy()
        
        # Filter by date range
        if start_date:
            df = df[df['date'] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df['date'] <= pd.Timestamp(end_date)]
        
        return df.reset_index(drop=True)
    
    def load_all(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load all sample data as a single DataFrame.
        
        Returns:
            Combined DataFrame in long format
        """
        self._ensure_data_loaded()
        
        dfs = []
        for key, df in self._sample_data.items():
            filtered = df.copy()
            if start_date:
                filtered = filtered[filtered['date'] >= pd.Timestamp(start_date)]
            if end_date:
                filtered = filtered[filtered['date'] <= pd.Timestamp(end_date)]
            dfs.append(filtered)
        
        return pd.concat(dfs, ignore_index=True)
    
    def get_available_indicators(self) -> list:
        """Get list of available sample indicators."""
        self._ensure_data_loaded()
        return list(self._sample_data.keys())
    
    def is_available(self) -> bool:
        """Sample data is always available."""
        return True
