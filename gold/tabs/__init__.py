"""
Tab implementation modules for the Gold Cyclical Profiles application.
Each tab's UI and logic is implemented in a separate module.
The seasonality functionality has been integrated into the monthly profile in cyclical_profiles.
"""
from gold.tabs.current_market import render_current_market_tab
from gold.tabs.cyclical_profiles import render_cyclical_profiles_tab
from gold.tabs.candle_charts import render_candle_charts_tab

__all__ = [
    'render_current_market_tab', 
    'render_cyclical_profiles_tab', 
    'render_candle_charts_tab'
]
