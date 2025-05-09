"""
Cyclical Profiles tab implementation.
This module contains the UI and logic for the Cyclical Profiles tab.
It also includes integrated seasonality visualization for the monthly profile.
"""
import streamlit as st
import pandas as pd
import datetime as dt
import plotly.express as px
import plotly.graph_objects as go

from gold import config
from gold.date_ui import get_date_range_for_profile
from gold.data.loader import load_profile_data
from gold.seasonality import calculate_seasonality, generate_cumulative_returns, plot_seasonality
from gold.composite_avg import calculate_composite_average, get_composite_periods, get_composite_description
from gold.profile_utils import create_ordered_profile_df
# Import after creating the profile_utils to avoid circular imports
from gold.tabs.composite_view import render_composite_averages

def load_seasonality_data(file_key, load_function):
    """Load data for seasonality analysis with caching"""
    df = load_function(file_key)
    return df

def render_cyclical_profiles_tab(tab, df, profile_key, metric, session_view_mode, session_filter, x="Label", chart_type="bar", year_controls=None, view_type="standard", show_composite=False):
    """Render the Cyclical Profiles tab content"""
    with tab:
        st.markdown("""
        Explore **gold's seasonality** across multiple time‑based profiles (month, week of year, day of week, session, etc.).
        The coloured **barcode** underneath the main chart gives you a quick visual of the cycle:
        <span style='background:#2e7d32;color:white;padding:2px 6px;border-radius:4px'>green</span>
        bars = average up months, <span style='background:#c62828;color:white;padding:2px 6px;border-radius:4px'>red</span>
        bars = average down months.
        """, unsafe_allow_html=True)
        
        # If month profile with line chart, just show the seasonality chart
        if profile_key == "month" and chart_type == "line":
            # Render seasonality line chart for monthly profile
            render_monthly_seasonality(year_controls)
            return  # Exit early to avoid showing other charts
            
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
        
        # For composite view, we'll use predefined date ranges later
        # For standard view, get the date range from the UI
        if show_composite:
            # If showing composite averages, use today's date and a fixed 20-year history for loading initial data
            # The actual composite calculations will use appropriate periods defined in composite_avg module
            end = dt.datetime.now().date()
            start = end - dt.timedelta(days=365*20)  # 20 years of data should cover all composite periods
            
            # Create an info message about date ranges for composite averages
            st.info("📅 When viewing composite averages, the date range selector is not used. Each composite is calculated using its own predefined period.")
        else:
            # For regular view, set date range based on the selected profile
            # Use a key prefix to avoid duplicate widget IDs
            key_prefix = f"{profile_key}_{chart_type}"
            start, end = get_date_range_for_profile(profile_key, key_prefix=key_prefix)
            
            # Error handling for invalid dates
            if start > end:
                st.error("Start date after End date")
                return
        
        # Use the profile data if already fetched, otherwise load it with date filters
        if df is not None and len(df) > 0:
            profile_df = df  # Use the provided DataFrame
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
            
        # Set the x-axis label column based on profile type
        x = "Label" if "Label" in profile_df.columns else "Month"
        
        # Add date range information to the top of the page
        date_format = "%b %d, %Y"
        date_info = f"Data from {start.strftime(date_format)} to {end.strftime(date_format)}"
        
        # Check if we should show the composite averages view
        if show_composite:
            # Display date range at the top
            st.markdown(f"<p style='color: gray;'>{date_info}</p>", unsafe_allow_html=True)
            
            # Get all available composite periods for this profile type
            composite_periods = get_composite_periods(profile_key)
            composite_options = list(composite_periods.keys())
            
            # Create the tables for each composite period
            st.header(f"Composite Averages: {profile_key.replace('_', ' ').title()}")
            
            # Informational box explaining composite averages
            with st.expander("ℹ️ About Composite Averages", expanded=False):
                st.markdown("""
                A **composite average** is the average value of a metric at the same point within a repeating time cycle, 
                calculated across multiple instances of that cycle.
                
                For example, for a monthly profile, the "Short-term Avg" shows the average performance of each month
                over the past 3 years, while the "Long-term Avg" shows the average over 10 years.
                
                This helps identify which patterns are consistent across different timeframes and which might be
                more recent phenomena.
                """)
            
            # Show each timeframe one after another
            for period_type in composite_options:
                description = get_composite_description(profile_key, period_type)
                
                # Create a section for this period
                st.markdown(f"## {period_type}")
                st.markdown(f"<p style='color: gray; margin-bottom: 20px;'>{description}</p>", unsafe_allow_html=True)
                
                # Define metric columns to average
                metric_columns = ["AvgReturn", "AvgRange", "ProbGreen", "ProbRed"]
                
                # Make a copy of the data to avoid modifying the original
                period_df = profile_df.copy()
                
                # Calculate the composite average for this period
                if period_type != "Min Cycle":  # Min Cycle is the current data, no averaging needed
                    period_df = calculate_composite_average(period_df, profile_key, period_type, x, metric_columns)
                
                # Sort by natural order for the profile type
                period_df = create_ordered_profile_df(period_df, profile_key, session_view_mode)
                
                # Special handling for session profile to match regular session display
                if profile_key == "session":
                    # Create a visualization that matches the regular session profile
                    # Create a vibrant color palette for the three sessions (good for dark mode)
                    session_colors = {
                        "Asia": "#FF3333",    # Bright red
                        "London": "#FFCC00",  # Golden yellow
                        "NY": "#33CC33"       # Bright green
                    }
                    
                    # Select the y column based on the metric
                    y_column = "AvgReturn"
                    y_title = "Average Return"
                    if metric == "ATR points":
                        y_column = "AvgRange"
                        y_title = "ATR (points)"
                    elif metric == "Probability":
                        # For probability, we'll create a custom chart later - still use AvgReturn for now
                        y_column = "AvgReturn"
                        y_title = "Average Return"
                    
                    # Choose the chart based on the session view mode and metric
                    if metric == "Probability":
                        # For probability, we need to show both green and red probabilities
                        if session_view_mode == "daily":  # 5-Bar view
                            # Group the data by day, showing probability of green/red for each day
                            probability_df = period_df.groupby("DayLabel")[["ProbGreen", "ProbRed"]].mean().reset_index()
                            
                            # Create a grouped bar chart showing probability of green/red for each day
                            fig = px.bar(probability_df, 
                                        x="DayLabel", 
                                        y=["ProbGreen", "ProbRed"], 
                                        barmode="group",
                                        color_discrete_map={"ProbGreen":"#33CC33", "ProbRed":"#FF3333"},
                                        height=500)
                            
                            fig.update_layout(
                                title=f"Probability Analysis by Day - {period_type}",
                                xaxis_title="Day of Week",
                                yaxis_title="Probability (%)"
                            )
                        else:  # Combined view
                            # Group by session
                            probability_df = period_df.groupby("SessionLabel")[["ProbGreen", "ProbRed"]].mean().reset_index()
                            
                            # Create a grouped bar chart showing probability of green/red for each session
                            fig = px.bar(probability_df, 
                                        x="SessionLabel", 
                                        y=["ProbGreen", "ProbRed"], 
                                        barmode="group",
                                        color_discrete_map={"ProbGreen":"#33CC33", "ProbRed":"#FF3333"},
                                        height=500)
                            
                            fig.update_layout(
                                title=f"Probability Analysis by Session - {period_type}",
                                xaxis_title="Trading Session",
                                yaxis_title="Probability (%)"
                            )
                    else:  # For Average Return and ATR points metrics
                        if session_view_mode == "daily":  # 5-Bar view
                            # Create a stacked bar chart with one bar per day, colored by session
                            fig = px.bar(period_df,
                                        x="DayLabel",
                                        y=y_column,
                                        color="SessionLabel",
                                        color_discrete_map=session_colors,
                                        barmode="stack",
                                        height=500)
                            
                            # Customize layout
                            fig.update_layout(
                                title=f"Daily Performance by Trading Session - {period_type}",
                                xaxis_title="Day of Week",
                                yaxis_title=y_title,
                                legend_title="Trading Session"
                            )
                        else:  # Combined view (1 bar with 3 sessions)
                            # Use a constant value for x-axis to create a single bar
                            period_df["Segment"] = "Combined Sessions"
                            
                            # Create a stacked bar chart
                            fig = px.bar(period_df,
                                        x="Segment",
                                        y=y_column,
                                        color="SessionLabel",
                                        color_discrete_map=session_colors,
                                        barmode="stack",
                                        height=500)
                            
                            # Customize layout
                            fig.update_layout(
                                title=f"Trading Sessions Performance - {period_type}",
                                xaxis_title="",
                                yaxis_title=y_title,
                                legend_title="Trading Session"
                            )
                else:  # For non-session profiles, use standard display
                    # Create visualization based on selected metric
                    if metric == "Average Return":
                        period_df["col"] = period_df["AvgReturn"].gt(0).map({True:"green", False:"red"})
                        fig = px.bar(period_df, x=x, y="AvgReturn", color="col",
                                    color_discrete_map="identity", height=400)
                        fig.update_layout(yaxis_title="Average Return (%)")
                    elif metric == "ATR points":
                        q = period_df["AvgRange"].quantile([0, .33, .66, 1]).values
                        period_df["band"] = period_df["AvgRange"].apply(
                            lambda v: "Low" if v<=q[1] else "Avg" if v<=q[2] else "High")
                        fig = px.bar(period_df, x=x, y="AvgRange", color="band",
                                    color_discrete_map={"Low":"green","Avg":"orange","High":"red"}, height=400)
                        fig.update_layout(yaxis_title="ATR (points)")
                    else:  # Probability
                        fig = px.bar(period_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                                    color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
                        fig.update_layout(yaxis_title="Probability (%)")
                
                # Display the chart
                st.plotly_chart(fig, use_container_width=True)
                
                # Add separator between periods
                if period_type != composite_options[-1]:
                    st.markdown("---")
            
            return  # Exit early to avoid showing other UI elements

        # Display standard UI for non-composite view
        # Display the date range information at the top
        st.markdown(f"<p style='color: gray;'>{date_info}</p>", unsafe_allow_html=True)
        
        # Format date strings for display
        if start and end:
            # Format the date range string based on profile type
            if profile_key in ['hour', 'session']:
                # For intraday profiles, only show the date range in days
                date_range_str = f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}"
            elif profile_key in ['day_of_week', 'day_of_month']:
                # For daily profiles, show month and year only
                date_range_str = f"{start.strftime('%b %Y')} - {end.strftime('%b %Y')}"
            elif profile_key in ['month', 'week_of_month', 'quarter']:
                # For monthly/quarterly profiles, only show years
                date_range_str = f"{start.strftime('%Y')} - {end.strftime('%Y')}"
            elif profile_key in ['week_of_year']:
                # For yearly profiles, show year (and week number if available)
                date_range_str = f"{start.strftime('%Y')} - {end.strftime('%Y')}"
            elif profile_key in ['presidential', 'decennial']:
                # For multi-year cycles, just show years
                date_range_str = f"{start.year} - {end.year}"
            else:
                # Default format for other profile types
                date_range_str = f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}"
                
            # Display the date range in the title                
            st.markdown(f"### Profile Data: {date_range_str}")
        
        # Session profiles get their own visualization logic
        if profile_key == "session":
            render_session_profile(profile_df, session_view_mode, session_filter, metric=metric)
        # Monthly profile with 'line' chart type gets the seasonality view
        elif profile_key == "month" and chart_type == "line":
            render_monthly_seasonality(year_controls)
        # For all other profiles, use the standard visualization
        else:
            render_standard_profile(profile_df, metric, x, profile_key)

def render_session_profile(profile_df, session_view_mode, session_filter, metric="Average Return"):
    """Render session-specific visualization"""
    # Get the metric from the sidebar if not provided
    if metric is None:
        metric = st.session_state.get('metric', "Average Return")
    
    # Select the y column and title based on the metric
    y_column = "AvgReturn"
    y_title = "Average Return"
    if metric == "ATR points":
        y_column = "AvgRange"
        y_title = "ATR (points)"
    
    # Handle different metrics and view modes
    if metric == "Probability":
        if session_view_mode == "daily":
            # Group the data by day, showing probability of green/red for each day
            probability_df = profile_df.groupby("DayLabel")[["ProbGreen", "ProbRed"]].mean().reset_index()
            
            # Create a grouped bar chart showing probability of green/red for each day
            fig2 = px.bar(probability_df, 
                        x="DayLabel", 
                        y=["ProbGreen", "ProbRed"], 
                        barmode="group",
                        color_discrete_map={"ProbGreen":"#33CC33", "ProbRed":"#FF3333"},
                        height=500)
            
            fig2.update_layout(
                title="Probability Analysis by Day",
                xaxis_title="Day of Week",
                yaxis_title="Probability (%)"
            )
        else:  # Combined view
            # Group by session
            probability_df = profile_df.groupby("SessionLabel")[["ProbGreen", "ProbRed"]].mean().reset_index()
            
            # Create a grouped bar chart showing probability of green/red for each session
            fig2 = px.bar(probability_df, 
                        x="SessionLabel", 
                        y=["ProbGreen", "ProbRed"], 
                        barmode="group",
                        color_discrete_map={"ProbGreen":"#33CC33", "ProbRed":"#FF3333"},
                        height=500)
            
            # Add title based on filter
            filter_title = ""
            if session_filter != "All":
                filter_title = f" ({session_filter})"
                
            fig2.update_layout(
                title=f"Probability Analysis by Session{filter_title}",
                xaxis_title="Trading Session",
                yaxis_title="Probability (%)"
            )
    elif session_view_mode == "daily":
        # For daily view with 5 bars, each split into 3 sessions as stacked segments
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
                        y=y_column,
                        color="SessionLabel",
                        color_discrete_map=session_colors,
                        barmode="stack",
                        height=500)
            
            # Customize layout
            fig2.update_layout(
                title=f"Daily Performance by Trading Session - {y_title}",
                xaxis_title="Day of Week",
                yaxis_title=y_title,
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
            fig2 = px.bar(profile_df, x="Label", y=y_column, color="col",
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
                    y=y_column,
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

def render_monthly_seasonality(year_controls=None):
    """Render monthly seasonality line chart (integrated from seasonality tab)"""
    from gold.azure import load_csv  # Import here to avoid circular imports
    
    # Set default year controls if not provided
    if year_controls is None:
        year_controls = {
            'show_ytd': True,
            'show_5yr': True,
            'show_10yr': True,
            'show_15yr': False,
            'return_method_key': 'open-close'
        }
    
    # Create a title for the chart
    st.subheader("Monthly Performance ")
    
    # Get calculation settings
    timeframe_key = "d"  # Always use daily data for consistency
    return_method = year_controls.get('return_method_key', 'open-close')  # Get return method from controls
    
    # Show a spinner while calculating
    with st.spinner("Calculating monthly patterns..."):
        # Get the data file
        data_file = config.TIMEFRAME_FILES[timeframe_key]
        
        # Load data with caching
        data = load_seasonality_data(data_file, load_csv)
        
        # Calculate years to include
        years_to_include = []
        if year_controls['show_5yr']:
            years_to_include.append(5)
        if year_controls['show_10yr']:
            years_to_include.append(10)
        if year_controls['show_15yr']:
            years_to_include.append(15)
        
        if not years_to_include:
            years_to_include = [10]  # Default to 10 years if none selected
        
        # Calculate seasonality using the same cutoff date as other profiles
        seasonality_data = calculate_seasonality(
            data, 
            years_back=max(years_to_include), 
            return_type=return_method,
            cutoff_date=config.cutoff_date
        )
        
        # Generate return data
        return_data = generate_cumulative_returns(seasonality_data, years_list=years_to_include)
        
        # Filter based on selected options
        if not year_controls['show_ytd'] and "YTD" in return_data:
            del return_data["YTD"]
        if not year_controls['show_5yr'] and "5YR" in return_data:
            del return_data["5YR"]
        if not year_controls['show_10yr'] and "10YR" in return_data:
            del return_data["10YR"]
        if not year_controls['show_15yr'] and "15YR" in return_data:
            del return_data["15YR"]
        
        # Create figure with monthly profile-specific title
        title = "Monthly Performance (Daily Data)"
        seasonality_figure = plot_seasonality(return_data, title=title)
        
        # Save to session state with a specific key for the monthly profile
        st.session_state['monthly_seasonality_figure'] = seasonality_figure

    # Display the figure
    st.plotly_chart(st.session_state['monthly_seasonality_figure'], use_container_width=True)
    
    # Additional metrics table
    with st.expander("Monthly Performance Summary", expanded=False):
        # Create monthly summary if we have data
        if 'monthly_seasonality_figure' in st.session_state and return_data:
            render_monthly_performance_summary(return_data)

def render_monthly_performance_summary(return_data):
    """Render the monthly performance summary table"""
    # Create summary table
    summary_data = []
    
    for key, data in return_data.items():
        if key == "YTD":
            name = "Year to Date"
        else:
            name = f"{key[:-2]} Year Average"
        
        # Calculate monthly performance - handle different day of year calculations
        try:
            # More accurate month calculation - convert day of year to date
            if "DayOfYear" in data.columns:
                # Make sure DayOfYear is integer
                data["DayOfYear"] = data["DayOfYear"].astype(int)
                
                # Generate month from day of year (more accurate than division)
                def day_to_month(day, year=2020):  # Using leap year for safety
                    date = dt.datetime(year, 1, 1) + dt.timedelta(days=int(day)-1)
                    return date.month
                
                data["Month"] = data["DayOfYear"].apply(day_to_month)
            else:  # Handle case where DayOfYear is missing
                data["Month"] = (data.index % 365 // 30) + 1
            
            # Group by month
            monthly_returns = data.groupby("Month")["Return"].sum().reset_index()
        except Exception as e:
            st.warning(f"Could not calculate monthly returns accurately: {e}")
            # Fallback to approximate months
            month_data = {"Timeframe": name}
            for m in range(1, 13):
                month_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m-1]
                month_data[month_name] = "N/A"
            summary_data.append(month_data)
            continue
        
        # Format data for the table
        month_data = {"Timeframe": name}
        
        for _, row in monthly_returns.iterrows():
            month = int(row["Month"])  # Convert to integer explicitly
            if 1 <= month <= 12:
                month_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1]
                month_data[month_name] = f"{row['Return']:.2f}%"
        
        summary_data.append(month_data)
    
    # Convert to DataFrame and display
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)

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
    st.plotly_chart(fig, use_container_width=True)
    
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
