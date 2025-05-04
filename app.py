import streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
import pathlib, sys, datetime as dt, pytz
sys.path.append(str(pathlib.Path(__file__).parent))

from gold import config
from gold.azure import load_csv
from gold.seasonality import calculate_seasonality, generate_cumulative_returns, plot_seasonality
from gold.time_matrix import prepare_data, create_timestamp_matrix, plot_time_matrix, plot_scatter_matrix, create_split_candle_chart
from gold.profiles import BUILDERS
from gold.date_ui import get_date_range_for_profile

st.set_page_config(page_title="Gold Profiles", layout="wide")
st.title("🥇 Gold Cyclical Profiles")

# Top-level tab organization
tab1, tab2, tab3, tab4 = st.tabs(["Current Market Position", "Cyclical Profiles", "Seasonality", "Time Matrix"])

# --- Sidebar controls ----------------------------------------------------
# Profile selection dropdown with display names
profile_options = list(config.PROFILE_DISPLAY_NAMES.keys())
profile_display_names = [config.PROFILE_DISPLAY_NAMES[k] for k in profile_options]
default_index = 3  # Default to 'month' profile

profile_display = st.sidebar.selectbox("Profile", profile_display_names, default_index)
profile_key = profile_options[profile_display_names.index(profile_display)]

# Metrics selection
metric = st.sidebar.radio("Metric", 
               ["Average Return", "ATR points", "ATR level", "Probability"], 0)

# Session profile specific options
session_view_mode = "daily"
session_filter = "All"

if profile_key == "session":
    # Add session-specific controls
    session_view_options = ["5-Bar (Weekdays)", "1-Bar (Combined)"]
    session_view_selection = st.sidebar.selectbox("View Mode", session_view_options, 0)
    session_view_mode = "daily" if session_view_selection == session_view_options[0] else "combined"
    
    # For the 1-bar view, add filter for red/green days
    if session_view_mode == "combined":
        session_filter = st.sidebar.radio("Filter by Day Type", ["All", "Green Days", "Red Days"], 0)

# Use the specialized date UI for this profile
start, end = get_date_range_for_profile(profile_key)

# Error handling for invalid dates
if start > end:
    st.error("Start date after End"); st.stop()
    
# --- Time Matrix Tab ------------------------------------------------------
with tab4:
    st.markdown("## Gold Time Matrix Analysis")
    
    # Create sidebar for time matrix controls
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Time Matrix Options")
    
    # Analysis type selection
    analysis_types = [
        "Mapping Monthly High Low Timestamps (Use Weekly)",
        "Mapping Weekly High Low Timestamps (Use Daily)",
        "Mapping Daily High Low Timestamps (Use Hourly)",
        "Split Candles -> Green & Red",
        "Mapping Monthly -> 4 Week Scatter Plot",
        "Mapping Weekly -> 5 Day Scatter Plot",
        "Mapping Daily -> 24hr Scatter Plot"
    ]
    
    selected_analysis = st.sidebar.selectbox("Analysis Type", analysis_types)
    
    # Data source selection based on analysis type
    if "Monthly" in selected_analysis:
        data_timeframe = "m"
        source_tf = "monthly"
    elif "Weekly" in selected_analysis:
        data_timeframe = "W"
        source_tf = "weekly"
    elif "Daily" in selected_analysis or "Split Candles" in selected_analysis:
        data_timeframe = "d"
        source_tf = "daily"
    else:
        data_timeframe = "d"  # Default
        source_tf = "daily"
    
    # Target timeframe based on analysis type
    if "Use Weekly" in selected_analysis:
        target_tf = "weekly"
    elif "Use Daily" in selected_analysis:
        target_tf = "daily"
    elif "Use Hourly" in selected_analysis:
        target_tf = "hourly"
    else:
        target_tf = "daily"  # Default
    
    # Date range selection (similar to other tabs)
    date_range = st.sidebar.selectbox(
        "Date Range",
        list(config.STANDARD_PRESETS.keys()),
        index=1  # Default to 3Y
    )
    
    # Get date range from presets
    start_date, end_date = config.STANDARD_PRESETS[date_range]
    
    # Calculate and analyze button
    analyze_button = st.sidebar.button("Generate Time Matrix", type="primary")
    
    # Show different UI based on the analysis type
    if "Split Candles" in selected_analysis:
        st.markdown("### Split Candles Analysis - Green & Red")
        st.markdown("This analysis separates green and red candles to identify patterns specific to each type.")
    elif "Scatter Plot" in selected_analysis:
        if "Monthly" in selected_analysis:
            scatter_type = "month"
            period_unit = "4 weeks"
        elif "Weekly" in selected_analysis:
            scatter_type = "week"
            period_unit = "5 days"
        else:  # Daily
            scatter_type = "day"
            period_unit = "24 hours"
            
        st.markdown(f"### Timestamp Scatter Plot - {scatter_type.title()} ({period_unit})")
        st.markdown(f"This visualization shows when highs and lows typically occur within a {scatter_type}.")
    else:
        st.markdown(f"### High/Low Timestamp Analysis - {source_tf.title()} using {target_tf.title()} data")
        st.markdown(f"This analysis maps when price highs and lows occur within {source_tf} periods.")
    
    # Load and process data when the button is clicked
    if analyze_button or 'time_matrix_figure' in st.session_state:
        with st.spinner("Generating Time Matrix Analysis..."):
            # Get data file based on timeframe
            try:
                data_file = config.TIMEFRAME_FILES[data_timeframe]
            except KeyError:
                st.error(f"No data file available for timeframe {data_timeframe}")
                st.stop()
            
            # Load data with caching
            @st.cache_data(show_spinner=False)
            def load_time_matrix_data(file_key):
                df = load_csv(file_key)
                return df
            
            # Load and prepare data
            data = load_time_matrix_data(data_file)
            
            # Filter by date range
            data["Date"] = pd.to_datetime(data["Date"])
            data = data[(data["Date"] >= pd.Timestamp(start_date)) & 
                        (data["Date"] <= pd.Timestamp(end_date))]
            
            # Prepare data for analysis
            prepared_data = prepare_data(data, timeframe=source_tf)
            
            # Create visualization based on selected analysis
            if "Split Candles" in selected_analysis:
                time_matrix_figure = create_split_candle_chart(
                    prepared_data, 
                    title=f"Split Candle Analysis ({date_range})"
                )
            elif "Scatter Plot" in selected_analysis:
                # First create timestamp matrix
                timestamp_data = create_timestamp_matrix(
                    prepared_data,
                    source_timeframe=source_tf,
                    target_timeframe=target_tf
                )
                
                # Then create scatter plot
                time_matrix_figure = plot_scatter_matrix(
                    timestamp_data,
                    scatter_type=scatter_type,
                    title=f"{source_tf.title()} Highs/Lows Scatter ({date_range})"
                )
            else:
                # Create timestamp matrix
                timestamp_data = create_timestamp_matrix(
                    prepared_data,
                    source_timeframe=source_tf,
                    target_timeframe=target_tf
                )
                
                # Create time matrix plot
                time_matrix_figure = plot_time_matrix(
                    timestamp_data,
                    title=f"{source_tf.title()} Highs/Lows using {target_tf.title()} Data ({date_range})"
                )
            
            # Save to session state
            st.session_state['time_matrix_figure'] = time_matrix_figure
        
        # Display the figure
        st.plotly_chart(st.session_state['time_matrix_figure'], use_container_width=True)
        
        # Additional information based on analysis type
        if "Scatter Plot" not in selected_analysis and "Split Candles" not in selected_analysis:
            st.subheader("Interpretation Guide")
            st.markdown(f"""
            - **Top Panel**: Shows when **highs** typically occur within {source_tf} periods
            - **Bottom Panel**: Shows when **lows** typically occur within {source_tf} periods
            - Higher bars indicate more frequent occurrences at that specific time
            """)
    else:
        # Default instruction message
        st.info("Select your analysis type and click 'Generate Time Matrix' to view the results.")

# --- Seasonality Tab ----------------------------------------------------
with tab3:
    st.markdown("## Gold Seasonality Analysis")
    
    # Create sidebar for seasonality controls
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Seasonality Options")
    
    # Data source selection (timeframe)
    timeframe_options = {
        "Daily": "d",
        "Weekly": "W",
        "Monthly": "m",
        "1-Hour": "h1"
    }
    selected_timeframe = st.sidebar.selectbox(
        "Data Timeframe",
        list(timeframe_options.keys()),
        index=0  # Default to daily
    )
    timeframe_key = timeframe_options[selected_timeframe]
    
    # Return calculation method
    return_methods = {
        "Open to Close (Intraday)": "open-close",
        "Close to Close (Daily)": "close-close"
    }
    selected_return_method = st.sidebar.radio(
        "Return Calculation",
        list(return_methods.keys())
    )
    return_method = return_methods[selected_return_method]
    
    # Year ranges to show
    show_ytd = st.sidebar.checkbox("Show Year-to-Date", value=True)
    show_5yr = st.sidebar.checkbox("Show 5-Year Average", value=True)
    show_10yr = st.sidebar.checkbox("Show 10-Year Average", value=True)
    show_15yr = st.sidebar.checkbox("Show 15-Year Average", value=True)
    
    # Calculate button
    calculate_button = st.sidebar.button("Calculate Seasonality", type="primary")
    clear_button = st.sidebar.button("Clear Filters")
    
    if clear_button:
        # Reset to defaults
        show_ytd = True
        show_5yr = True
        show_10yr = True
        show_15yr = True
        selected_timeframe = list(timeframe_options.keys())[0]
        selected_return_method = list(return_methods.keys())[0]
    
    # Main content area for the seasonality tab
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"Gold Seasonality ({selected_timeframe} Data)")
    
    with col2:
        st.caption(f"Return Method: {selected_return_method}")
    
    # Calculate and display seasonality if button is clicked
    if calculate_button or 'seasonality_figure' in st.session_state:
        # Show a spinner while calculating
        with st.spinner(f"Calculating seasonality patterns using {selected_timeframe} data..."):
            # Get the data file
            data_file = config.TIMEFRAME_FILES[timeframe_key]
            
            # Load data
            @st.cache_data(show_spinner=False)
            def load_seasonality_data(file_key):
                df = load_csv(file_key)
                return df
            
            data = load_seasonality_data(data_file)
            
            # Calculate years to include
            years_to_include = []
            if show_5yr:
                years_to_include.append(5)
            if show_10yr:
                years_to_include.append(10)
            if show_15yr:
                years_to_include.append(15)
            
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
            if not show_ytd and "YTD" in return_data:
                del return_data["YTD"]
            if not show_5yr and "5YR" in return_data:
                del return_data["5YR"]
            if not show_10yr and "10YR" in return_data:
                del return_data["10YR"]
            if not show_15yr and "15YR" in return_data:
                del return_data["15YR"]
            
            # Create figure
            title = f"Gold Seasonality - {selected_timeframe} ({selected_return_method})"
            seasonality_figure = plot_seasonality(return_data, title=title)
            
            # Save to session state
            st.session_state['seasonality_figure'] = seasonality_figure
    
        # Display the figure
        st.plotly_chart(st.session_state['seasonality_figure'], use_container_width=True)
        
        # Additional metrics table
        st.subheader("Monthly Performance Summary")
        
        # Create monthly summary if we have data
        if 'seasonality_figure' in st.session_state and return_data:
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
    else:
        # Show placeholder before calculation
        st.info("Select your parameters and click 'Calculate Seasonality' to view seasonal patterns.")



# ------------------------------------------------------------------------
blob_key = config.PROFILE_SOURCE[profile_key]
blob     = config.TIMEFRAME_FILES[blob_key]

@st.cache_data(show_spinner=f"Loading {blob} …")
def fetch(b):
    df = load_csv(b)[["Date","Open","High","Low","Close"]].copy()
    # strip thousands separator before numeric cast
    for col in ["Open","High","Low","Close"]:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)
    
    # First try to parse date with common formats to avoid warning
    try:
        # Try M/D/YYYY format (e.g., 3/19/2025)
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="raise")
    except ValueError:
        try:
            # Try YYYY-MM-DD format
            df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="raise")
        except ValueError:
            # As a fallback, let pandas infer the format
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    return df.dropna()

raw = fetch(blob)
build = BUILDERS[profile_key]

# Special handling for session profile
if profile_key == "session":
    # Call build with view mode parameter
    df = build(raw, pd.Timestamp(start), pd.Timestamp(end), view=session_view_mode)
    
    # Apply filter for combined view if needed
    if session_view_mode == "combined" and session_filter != "All":
        if session_filter == "Green Days":
            # Filter to only include data from days with positive returns
            green_days = raw[raw["Close"] > raw["Open"]].copy()
            if not green_days.empty:
                df = build(green_days, pd.Timestamp(start), pd.Timestamp(end), view=session_view_mode)
        elif session_filter == "Red Days":
            # Filter to only include data from days with negative returns
            red_days = raw[raw["Close"] < raw["Open"]].copy()
            if not red_days.empty:
                df = build(red_days, pd.Timestamp(start), pd.Timestamp(end), view=session_view_mode)
else:
    # Standard build for other profiles
    df = build(raw, pd.Timestamp(start), pd.Timestamp(end))

if df.empty:
    st.info("No data in range"); st.stop()

# --- Current Market Position Tab -------------------------------------------------------
with tab1:
    # Get current Eastern Time
    eastern = pytz.timezone('US/Eastern')
    current_time = dt.datetime.now(eastern)
    st.markdown(f"### Current Eastern Time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Create the Current Market Position table
    st.markdown("## Current Market Position 🔄")
    
    # Calculate current positions for all profiles
    positions_data = []
    
    for i, prof_key in enumerate(BUILDERS.keys()):
        # Get data for this profile using default presets
        blob_key = config.PROFILE_SOURCE[prof_key]
        blob_data = config.TIMEFRAME_FILES[blob_key]
        raw_data = fetch(blob_data)
        build_func = BUILDERS[prof_key]
        
        # Get default dates from profile presets
        default_preset = config.PROFILE_DEFAULT_PRESET[prof_key]
        preset_dict = config.PROFILE_PRESETS.get(prof_key, config.STANDARD_PRESETS)
        default_start, default_end = preset_dict.get(default_preset, (None, None))
        
        # Fall back to 1-year range if needed
        if default_start is None or default_end is None:
            default_start = dt.date.today() - dt.timedelta(days=365)
            default_end = dt.date.today()
        
        profile_df = build_func(raw_data, pd.Timestamp(default_start), pd.Timestamp(default_end))
        
        # Determine current position based on today's date
        if prof_key == 'decennial':
            current_position = current_time.year % 10
            max_position = 10
        elif prof_key == 'presidential':
            current_position = (current_time.year % 4) + 1
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
            current_position = current_time.weekday() + 1
            max_position = 5
        elif prof_key == 'session':
            current_position = current_time.weekday() + 1
            max_position = 5
        
        # Format the profile name for better display
        formatted_profile = prof_key.replace('_', ' ').title()
        
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

# --- Cyclical Profiles Tab -------------------------------------------------------
with tab2:
    st.markdown("""
    Explore **gold's seasonality** across multiple time‑based profiles (month, week of year, day of week, session, etc.).
    The coloured **barcode** underneath the main chart gives you a quick visual of the cycle:
    <span style='background:#2e7d32;color:white;padding:2px 6px;border-radius:4px'>green</span>
    bars = average up months, <span style='background:#c62828;color:white;padding:2px 6px;border-radius:4px'>red</span>
    bars = average down months.
    """, unsafe_allow_html=True)
    
    # Original view - sorted by returns (reds/greens grouped together)
    st.subheader("Chart 1 - Grouped by Returns (Red/Green)")
    
    # Sort by returns (reds on one side, greens on the other)
    returns_df = df.copy().sort_values("AvgReturn", ascending=False)
    
    # Use Label for x-axis
    x = "Label"
    
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
    elif metric == "ATR level":
        q = returns_df["AvgRange"].quantile([0, .33, .66, 1]).values
        returns_df["lvl"] = returns_df["AvgRange"].apply(lambda v: 1 if v<=q[1] else 2 if v<=q[2] else 3)
        fig = px.bar(returns_df, x=x, y="lvl", color="lvl",
                    color_discrete_map={1:"green",2:"orange",3:"red"}, height=400)
    else:
        fig = px.bar(returns_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                    color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
    
    fig.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    
    # Removed barcode visualization as requested
    
    # Add separator
    st.markdown("---")
    
    # Natural profile order view (Jan-Dec, Mon-Fri, etc.)
    st.subheader("Chart 2 - Natural Profile Order")
    
    # Sort by Bucket (natural profile order)
    # Create hardcoded calendar ordering for each profile type
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
    
    # Create visualization based on selected metric and profile type
    if profile_key == "session":
        # Special visualization for sessions profile
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
    else:
        # Standard visualization for other profiles
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
        elif metric == "ATR level":
            q = profile_df["AvgRange"].quantile([0, .33, .66, 1]).values
            profile_df["lvl"] = profile_df["AvgRange"].apply(lambda v: 1 if v<=q[1] else 2 if v<=q[2] else 3)
            fig2 = px.bar(profile_df, x=x, y="lvl", color="lvl",
                         color_discrete_map={1:"green",2:"orange",3:"red"}, height=400)
        else:
            fig2 = px.bar(profile_df, x=x, y=["ProbGreen","ProbRed"], barmode="group",
                         color_discrete_map={"ProbGreen":"green","ProbRed":"red"}, height=400)
    
    fig2.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)
