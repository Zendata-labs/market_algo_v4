"""
Current Market Position tab implementation.
This module contains the UI and logic for the Current Market Position tab.
"""
import streamlit as st
import pandas as pd
import datetime as dt
import pytz

from gold import config
from gold.profiles import BUILDERS

def load_data(fetch_function, profile_key):
    """Load and prepare data for a specific profile"""
    blob_key = config.PROFILE_SOURCE[profile_key]
    blob_data = config.TIMEFRAME_FILES[blob_key]
    return fetch_function(blob_data)

def get_current_position(prof_key, current_time):
    """Determine the current position in a cyclical profile based on current time."""
    if prof_key == 'decennial':
        current_position = current_time.year % 10
        max_position = 10
    elif prof_key == 'presidential':
        # Presidential cycle: Year 1 starts in years like 1977, 1981, 1985, 1989, 1993, etc.
        # Year 4 (Election Year) is years like 1980, 1984, 1988, 1992, 1996, etc.
        # 2021-2024 was a cycle, so 2025 is Year 1 of new cycle
        # To calculate: Base from 1977, then find position in 4-year cycle
        year_in_cycle = ((current_time.year - 1977) % 4) + 1
        current_position = year_in_cycle
        max_position = 4
    elif prof_key == 'quarter':
        current_position = (current_time.month - 1) // 3 + 1
        max_position = 4
    elif prof_key == 'month':
        current_position = current_time.month
        max_position = 12
    elif prof_key == 'week_of_year':
        current_position = current_time.isocalendar()[1]
        max_position = 52
    elif prof_key == 'week_of_month':
        current_position = ((current_time.day - 1) // 7) + 1
        max_position = 4 if current_position <= 4 else 5
    elif prof_key == 'day_of_week':
        # Gold market trading hours (Eastern Time):
        # Open: Sunday 6:00 PM ET to Friday 5:00 PM ET
        # Closed: Friday 5:00 PM ET to Sunday 6:00 PM ET
        weekday = current_time.weekday()
        hour = current_time.hour
        minute = current_time.minute
        
        is_market_closed = False
        
        # Check if market is closed based on trading schedule
        if weekday == 5:  # Saturday - always closed
            is_market_closed = True
        elif weekday == 6 and (hour < 18):  # Sunday before 6:00 PM ET
            is_market_closed = True
        elif weekday == 4 and (hour >= 17):  # Friday after 5:00 PM ET
            is_market_closed = True
            
        if is_market_closed:
            current_position = "Market is closed today"
            max_position = ""
        else:
            # Market is open - show position 1-5 for weekdays
            # Sunday evening and Friday during day are treated as 1 and 5 respectively
            if weekday == 6:  # Sunday
                day_pos = 1  # Treat as first day
            else:  # Monday(0) to Friday(4)
                day_pos = weekday + 1
                
            current_position = day_pos
            max_position = 5
    elif prof_key == 'session':
        # Gold market trading hours (Eastern Time):
        # Open: Sunday 6:00 PM ET to Friday 5:00 PM ET
        # Closed: Friday 5:00 PM ET to Sunday 6:00 PM ET
        weekday = current_time.weekday()
        hour = current_time.hour
        minute = current_time.minute
        
        is_market_closed = False
        
        # Check if market is closed based on trading schedule
        if weekday == 5:  # Saturday - always closed
            is_market_closed = True
        elif weekday == 6 and (hour < 18):  # Sunday before 6:00 PM ET
            is_market_closed = True
        elif weekday == 4 and (hour >= 17):  # Friday after 5:00 PM ET
            is_market_closed = True
            
        if is_market_closed:
            current_position = "Market is closed today"
            max_position = ""
        else:
            # Market is open - show session
            # For simplicity, use 3 trading sessions: Asia, London, NY
            # 1 = Asia, 2 = London, 3 = NY (simplified)
            # Use hour to determine current session
            if 0 <= hour < 8:
                session_pos = 1  # Asia session
            elif 8 <= hour < 16:
                session_pos = 2  # London session
            else:
                session_pos = 3  # NY session
                
            current_position = session_pos
            max_position = 3
    else:
        # Default for unknown profile types
        current_position = 0
        max_position = 0
    
    return current_position, max_position

def render_current_market_tab(tab, fetch_function):
    """Render the Current Market Position tab content"""
    with tab:
        # Get current Eastern Time
        eastern = pytz.timezone('US/Eastern')
        current_time = dt.datetime.now(eastern)
        st.markdown(f"### Current Eastern Time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Create the Current Market Position table
        st.markdown("## Current Market Position 🔄")
        
        # Calculate current positions for all profiles
        positions_data = []
        
        for i, prof_key in enumerate(BUILDERS.keys()):
            # Get data for this profile (we don't actually use this data for positions, 
            # but keeping the function call for consistency)
            raw_data = load_data(fetch_function, prof_key)
            
            # Determine current position based on today's date
            current_position, max_position = get_current_position(prof_key, current_time)
            
            # Format the profile name for better display
            formatted_profile = prof_key.replace('_', ' ').title()
            
            if prof_key in ['day_of_week', 'session'] and current_position == "Market is closed today":
                positions_data.append({
                    'Profile': formatted_profile,
                    'Position': current_position
                })
            else:
                positions_data.append({
                    'Profile': formatted_profile,
                    'Position': f"{current_position} of {max_position}"
                })
        
        # Create and display the position table
        position_df = pd.DataFrame(positions_data)
        st.dataframe(position_df, use_container_width=True, hide_index=False)
        
        # Add some contextual explanation
        st.markdown("""
    The table above shows the current market position for each cyclical profile based on Eastern Time.
    These positions can help you align your trading strategies with historical seasonal patterns.
    Switch to the 'Cyclical Profiles' tab to explore detailed historical performance for each profile.
    """)
