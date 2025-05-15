"""
Cyclical Profiles tab implementation.
This module contains the UI and logic for the Cyclical Profiles tab.
"""
import streamlit as st
import pandas as pd
import datetime as dt
import plotly.express as px
import plotly.graph_objects as go

from gold import config
from gold.date_ui import get_date_range_for_profile
from gold.data.loader import load_profile_data
# Seasonality imports removed

# Seasonality data loading function removed

def render_cyclical_profiles_tab(tab, df, profile_key, metric, session_view_mode, session_filter, x="Label", chart_type="bar", year_controls=None, view_type="standard"):
    """Render the Cyclical Profiles tab content"""
    with tab:
        st.markdown("""
        Explore **gold's seasonality** across multiple time‑based profiles (month, week of year, day of week, session, etc.).
        The coloured **barcode** underneath the main chart gives you a quick visual of the cycle:
        <span style='background:#2e7d32;color:white;padding:2px 6px;border-radius:4px'>green</span>
        bars = average up months, <span style='background:#c62828;color:white;padding:2px 6px;border-radius:4px'>red</span>
        bars = average down months.
        """, unsafe_allow_html=True)
        
        # Seasonality chart handling removed
            
        # If day_of_week profile with volatility clock view, show the volatility clock
        if profile_key == "day_of_week" and view_type == "volatility_clock":
            # Import the volatility clock module
            from gold.volatility_clock import display_volatility_clock
            
            # Pass the exact metric name from the main app to ensure proper synchronization
            # This is important because the UI shows the selected metric name
            volatility_metric = metric
            
            # Log the metric being passed to the volatility clock
            print(f"Passing metric: {volatility_metric} to volatility clock")
            
            # The volatility_clock module will handle the conversion internally            
            # This ensures UI consistency between the main app and the volatility clock
            
            # Render the volatility clock view with the selected metric
            display_volatility_clock(default_metric=volatility_metric)
            return  # Exit early to avoid showing other charts
        
        # For all other profiles or month with bar chart, continue with standard view
        
        # Set date range based on the selected profile
        # Use a key prefix to avoid duplicate widget IDs
        key_prefix = f"{profile_key}_{chart_type}"
        start, end = get_date_range_for_profile(profile_key, key_prefix=key_prefix)
        
        # Error handling for invalid dates
        if start > end:
            st.error("Start date after End date")
            return
        
        # Use the profile data if already fetched, otherwise load it with date filters
        if df is not None and len(df) > 0:
            profile_df = df
        else:
            try:
                # Get profile data with date range filtering
                profile_df = load_profile_data(
                    profile_key, 
                    start, 
                    end,
                    view_mode=session_view_mode,
                    filter_type=session_filter
                )
                
                if profile_df.empty:
                    st.info("No data in selected date range")
                    return
            except Exception as e:
                st.error(f"Error loading data: {e}")
                return
        
        # Prepare profile data title based on selected date range
        data_title = st.empty()  # Placeholder for the title
        
        # Format date strings for display
        if start and end:
            # Format the date range string based on profile type
            if profile_key in ['hour', 'session']:
                # For intraday profiles, only show the date range in days
                date_range_str = f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}"
            elif profile_key in ['day_of_week', 'day_of_month']:
                # For daily profiles, show month and year only
                date_range_str = f"{start.strftime('%b %Y')} - {end.strftime('%b %Y')}"
            elif profile_key == 'month':
                # For monthly profile, show years only
                date_range_str = f"{start.strftime('%Y')} - {end.strftime('%Y')}"
            elif profile_key == 'quarter':
                # For quarterly profile, show years only
                date_range_str = f"{start.strftime('%Y')} - {end.strftime('%Y')}"
            else:
                # Default format for other profiles
                date_range_str = f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}"
            
            # Set the profile data title using the date range
            data_title.markdown(f"### Profile Data: {date_range_str}")
        
        # Create visualization based on selected metric and profile type
        if profile_key == "session":
            render_session_profile(profile_df, session_view_mode, session_filter)
        else:
            # Standard visualization for other profiles
            render_standard_profile(profile_df, metric, x, profile_key)

def create_ordered_profile_df(df, profile_key, session_view_mode):
    """Create a profile dataframe in the natural order for the profile type"""
    if profile_key == "month":
        # For monthly profile, explicitly create a new dataframe in Jan-Dec order
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        profile_df = pd.DataFrame()
        
        # Build dataframe in explicit month order
        for month in month_order:
            month_data = df[df["Label"] == month]
            if not month_data.empty:
                profile_df = pd.concat([profile_df, month_data])
    elif profile_key == "day_of_week":
        # For day of week, explicitly order Mon-Fri
        dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        profile_df = pd.DataFrame()
        
        for day in dow_order:
            day_data = df[df["Label"] == day]
            if not day_data.empty:
                profile_df = pd.concat([profile_df, day_data])
    elif profile_key == "session":
        # For session profile, special handling based on view mode
        if session_view_mode == "daily":
            # Order by weekday, then by session within each day
            profile_df = df.copy().sort_values(["Bucket", "Session"])
        else:
            # For combined view, order by session (Asia, London, NY)
            profile_df = df.copy().sort_values(["Session"])
    else:
        # For other profiles, sort by Bucket which should represent the natural profile order
        profile_df = df.copy().sort_values("Bucket")
    
    return profile_df

def render_session_profile(profile_df, session_view_mode, session_filter):
    """Render session-specific visualization"""
    if session_view_mode == "daily":
        # For daily view with 5 bars, each split into 3 sessions as stacked segments
        # Create a pivot table to get sessions as columns
        if "DayLabel" in profile_df.columns and "SessionLabel" in profile_df.columns:
            # Create a vibrant color palette for the three sessions (good for dark mode)
            session_colors = {
                "Asia": "#FF3333",    # Bright red
                "London": "#FFCC00",  # Golden yellow
                "NY": "#33CC33"       # Bright green
            }
            
            # Create a stacked bar chart with one bar per day, colored by session
            fig2 = px.bar(profile_df,
                        x="DayLabel",
                        y="AvgReturn",
                        color="SessionLabel",
                        color_discrete_map=session_colors,
                        barmode="stack",
                        height=500)
            
            # Customize layout
            fig2.update_layout(
                title="Daily Performance by Trading Session",
                xaxis_title="Day of Week",
                yaxis_title="Average Return",
                legend_title="Trading Session"
            )
            
            # Add annotations to explain the segments
            fig2.add_annotation(
                x=0.02, y=0.98,
                xref="paper", yref="paper",
                text="Each bar shows a day split into three sessions:",
                showarrow=False,
                font=dict(size=12), align="left"
            )
            
            y_pos = 0.93
            for session, color in session_colors.items():
                fig2.add_annotation(
                    x=0.02, y=y_pos,
                    xref="paper", yref="paper",
                    text=f"• {session}",
                    showarrow=False,
                    font=dict(size=12, color="black"),
                    bgcolor=color,
                    borderpad=4,
                    align="left"
                )
                y_pos -= 0.05
        else:
            # Fallback if the data structure is not as expected
            fig2 = px.bar(profile_df, x="Label", y="AvgReturn", color="col",
                        color_discrete_map="identity", height=400)
    else:
        # For combined view (1 bar with 3 sessions)
        # Create a vibrant color palette for the three sessions (good for dark mode)
        session_colors = {
            "Asia": "#FF3333",    # Bright red
            "London": "#FFCC00",  # Golden yellow
            "NY": "#33CC33"       # Bright green
        }
        
        # Use a constant value for x-axis to create a single bar
        profile_df["Segment"] = "Combined Sessions"
        
        # Create a stacked bar chart
        fig2 = px.bar(profile_df,
                    x="Segment",
                    y="AvgReturn",
                    color="SessionLabel",
                    color_discrete_map=session_colors,
                    barmode="stack",
                    height=500)
        
        # Add title based on filter
        filter_title = ""
        if session_filter != "All":
            filter_title = f" ({session_filter})"
            
        # Customize layout
        fig2.update_layout(
            title=f"Trading Sessions Performance{filter_title}",
            xaxis_title="",
            yaxis_title="Average Return",
            legend_title="Trading Session"
        )
        
        # Add annotations to explain the segments
        fig2.add_annotation(
            x=0.02, y=0.98,
            xref="paper", yref="paper",
            text="Single bar split into three trading sessions:",
            showarrow=False,
            font=dict(size=12), align="left"
        )
        
        y_pos = 0.93
        for session, color in session_colors.items():
            fig2.add_annotation(
                x=0.02, y=y_pos,
                xref="paper", yref="paper",
                text=f"• {session}",
                showarrow=False,
                font=dict(size=12, color="black"),
                bgcolor=color,
                borderpad=4,
                align="left"
            )
            y_pos -= 0.05
    
    fig2.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)

def render_standard_profile(profile_df, metric, x, profile_key):
    """Render standard visualization for non-session profiles"""
    # Original view - sorted by returns (reds/greens grouped together)
    st.subheader("Chart 1 - Grouped by Returns (Red/Green)")
    
    # Sort by returns (reds on one side, greens on the other)
    returns_df = profile_df.copy().sort_values("AvgReturn", ascending=False)
    
    # Create visualization based on selected metric
    if metric == "Average Return":
        returns_df["col"] = returns_df["AvgReturn"].gt(0).map({True:"green", False:"red"})
        fig = px.bar(returns_df, x=x, y="AvgReturn", color="col",
                   color_discrete_map="identity", height=400)
    elif metric == "ATR points":
        q = returns_df["AvgRange"].quantile([0, .33, .66, 1]).values
        returns_df["band"] = returns_df["AvgRange"].apply(
            lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
        fig = px.bar(returns_df, x=x, y="AvgRange", color="band",
                   color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
    # ATR level option has been removed
    else:
        fig = px.bar(returns_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                   color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
    
    fig.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True, key=f"{profile_key}_sorted_{metric}")
    
    # Add separator
    st.markdown("---")
    
    # Natural profile order view (Jan-Dec, Mon-Fri, etc.)
    st.subheader("Chart 2 - Natural Profile Order")
    
    # Sort by natural order for the profile type
    profile_df = create_ordered_profile_df(profile_df, profile_key, "daily")
    
    # Regular bar chart visualization (default for all profiles)
    if metric == "Average Return":
        profile_df["col"] = profile_df["AvgReturn"].gt(0).map({True:"green", False:"red"})
        fig2 = px.bar(profile_df, x=x, y="AvgReturn", color="col",
                    color_discrete_map="identity", height=400)
    elif metric == "ATR points":
        q = profile_df["AvgRange"].quantile([0, .33, .66, 1]).values
        profile_df["band"] = profile_df["AvgRange"].apply(
            lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
        fig2 = px.bar(profile_df, x=x, y="AvgRange", color="band",
                    color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
    # ATR level option has been removed
    else:
        fig2 = px.bar(profile_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                    color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
    
    fig2.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)
