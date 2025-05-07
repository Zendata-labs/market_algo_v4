"""
Seasonality tab implementation.
This module contains the UI and logic for the Seasonality analysis tab.
"""
import streamlit as st
import pandas as pd
import datetime as dt

from gold import config
from gold.seasonality import calculate_seasonality, generate_cumulative_returns, plot_seasonality

def render_seasonality_controls():
    """Render the sidebar controls for the seasonality tab"""
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
    
    return {
        'timeframe_key': timeframe_key,
        'selected_timeframe': selected_timeframe,
        'return_method': return_method,
        'selected_return_method': selected_return_method,
        'show_ytd': show_ytd,
        'show_5yr': show_5yr,
        'show_10yr': show_10yr, 
        'show_15yr': show_15yr,
        'calculate_button': calculate_button
    }

def load_seasonality_data(file_key, load_function):
    """Load data for seasonality analysis with caching"""
    df = load_function(file_key)
    return df

def render_seasonality_tab(tab, load_csv_function):
    """Render the Seasonality tab content"""
    with tab:
        st.markdown("## Gold Seasonality Analysis")
        
        # Get user controls from sidebar
        controls = render_seasonality_controls()
        
        # Main content area for the seasonality tab
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader(f"Gold Seasonality ({controls['selected_timeframe']} Data)")
        
        with col2:
            st.caption(f"Return Method: {controls['selected_return_method']}")
        
        # Calculate and display seasonality if button is clicked
        if controls['calculate_button'] or 'seasonality_figure' in st.session_state:
            # Show a spinner while calculating
            with st.spinner(f"Calculating seasonality patterns using {controls['selected_timeframe']} data..."):
                # Get the data file
                data_file = config.TIMEFRAME_FILES[controls['timeframe_key']]
                
                # Load data with caching decorator
                data = load_seasonality_data(data_file, load_csv_function)
                
                # Calculate years to include
                years_to_include = []
                if controls['show_5yr']:
                    years_to_include.append(5)
                if controls['show_10yr']:
                    years_to_include.append(10)
                if controls['show_15yr']:
                    years_to_include.append(15)
                
                # Calculate seasonality using the same cutoff date as other profiles
                seasonality_data = calculate_seasonality(
                    data, 
                    years_back=max(years_to_include), 
                    return_type=controls['return_method'],
                    cutoff_date=config.cutoff_date
                )
                
                # Generate return data
                return_data = generate_cumulative_returns(seasonality_data, years_list=years_to_include)
                
                # Filter based on selected options
                if not controls['show_ytd'] and "YTD" in return_data:
                    del return_data["YTD"]
                if not controls['show_5yr'] and "5YR" in return_data:
                    del return_data["5YR"]
                if not controls['show_10yr'] and "10YR" in return_data:
                    del return_data["10YR"]
                if not controls['show_15yr'] and "15YR" in return_data:
                    del return_data["15YR"]
                
                # Create figure
                title = f"Gold Seasonality - {controls['selected_timeframe']} ({controls['selected_return_method']})"
                seasonality_figure = plot_seasonality(return_data, title=title)
                
                # Save to session state
                st.session_state['seasonality_figure'] = seasonality_figure
        
            # Display the figure
            st.plotly_chart(st.session_state['seasonality_figure'], use_container_width=True)
            
            # Additional metrics table
            st.subheader("Monthly Performance Summary")
            
            # Create monthly summary if we have data
            if 'seasonality_figure' in st.session_state and return_data:
                render_monthly_summary(return_data)
        else:
            # Show placeholder before calculation
            st.info("Select your parameters and click 'Calculate Seasonality' to view seasonal patterns.")

def render_monthly_summary(return_data):
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
