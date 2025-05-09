"""
Data loading and processing module.
This module provides centralized data access functions for the application.
"""
from gold.data.loader import load_chart_data, load_profile_data, fetch_data

__all__ = ['load_chart_data', 'load_profile_data', 'fetch_data']
