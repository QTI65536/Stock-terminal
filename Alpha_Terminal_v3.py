import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

# --- 1. Global UI & Typography Guard ---
st.set_page_config(layout="wide", page_title="Alpha Terminal v1.0", page_icon="🎯")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1c1e21; }
    section[data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #dee2e6; }
    
    /* Selective Bolding CSS Override */
    .js-plotly-plot .plotly .pointtext text { font-weight: 300; font-family: 'Segoe UI', sans-serif !important; }
    .js-plotly-plot .plotly .pointtext text b { font-weight: 700 !important; }
    
    h1, h2, h3, p, label, .stMarkdown { font-weight: 400 !important; }
    .stTabs [data-baseweb="tab"] { font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Professional Data Engine ---
def load_terminal_data(file_source, is_path=False):
    """Handles both uploaded files and local system paths."""
    rating_map = {
        'AAA': 100, 'AA+': 95, 'AA': 90, 'AA-': 85, 'A+': 80, 'A': 75, 'A-': 70,
        'BBB+': 65, 'BBB': 60, 'BBB-': 55, 'BB+': 45, 'BB': 40, 'B+': 30, 'B': 20
    }
    
    try:
        if is_path:
            df = pd.read_csv(file_source, encoding='latin1')
        else:
            file_source.seek(0)
            df = pd.read_csv(file_source, encoding='latin1')
            
        # Ticker & Metric Cleaning
        df['Ticker'] = df['Ticker'].astype(str).str.split(':').str[0].str.strip()
        num_cols = ['Closing Price', 'Dividend Yield', 'Est EPS Growth', 'Current Valuation', 'P/E']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[$,%x,]', '', regex=True), errors='coerce')
        
        # Risk Ledger
        df['Rating'] = df['Credit Rating']
        df['Safety Score'] = df['Credit Rating'].map(rating_map).fillna(50)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# --- 3. Sidebar & Auto-Load Logic ---
st.sidebar.header("📊 DATA CONTROLS")

# Check for a default file in the repository (e.g., 'latest_v1.csv')
DEFAULT_FILE = "sp500_dataset.csv" 
files = st.sidebar.file_uploader("Upload New EOD CSV", accept_multiple_files=True)

active_df = None
mode_label = ""

if files:
    # Use uploaded data
    data_map = {f.name: load_terminal_data(f) for f in files}
    selected = [f.name for f in files if st.sidebar.checkbox(f.name, value=True)]
    if selected:
        active_df = data_map[selected[-1]]
        mode_label = "Live Upload Mode"
elif os.path.exists(DEFAULT_FILE):
    # Use repository default if no upload exists
    active_df = load_terminal_data(DEFAULT_FILE, is_path=True)
    mode_label = f"Auto-Load Mode: {DEFAULT_FILE}"
    st.sidebar.info(f"Using default dataset: {DEFAULT_FILE}")

# --- 4. Main Interface ---
if active_df is not None:
    df = active_df.copy()
    
    # Filters
    st.sidebar.divider()
    max_y = float(df['Dividend Yield'].max()) if not df['Dividend Yield'].dropna().empty else 10.0
    yield_range = st.sidebar.slider("Yield Filter (%)", 0.0, max_y, (0.0, max_y))
    safety_range = st.sidebar.slider("Safety Score Filter", 0, 100, (0, 100))
    
    df = df[(df['Dividend Yield'] >= yield_range[0]) & (df['Dividend Yield'] <= yield_range[1])]
    df = df[(df['Safety Score'] >= safety_range[0]) & (df['Safety Score'] <= safety_range[1])]
    
    # Label Logic (Bold Ticker)
    df['DisplayLabel'] = df.apply(lambda x: f"<b>{x['Ticker']}</b> ({x['Dividend Yield']:.2f}%)", axis=1)

    tabs = st.tabs(["🎯 Alpha Radar", "📋 Execution Ledger"])

    with tabs[0]:
        st.caption(f"Status: {mode_label}")
        fig = go.Figure()
        lim_x = max(df['Est EPS Growth'].abs().max() * 1.1, 15) if not df.empty else 15
        lim_y = max(df['Current Valuation'].abs().max() * 1.1, 15) if not df.empty else 15
        
        fig.add_hline(y=0, line_color="#dee2e6", line_width=1)
        fig.add_vline(x=0, line_color="#dee2e6", line_width=1)

        if not df.empty:
            # Enhancement #3: Safety Score Sizing
            marker_sizes = 8 + (df['Safety Score'] / 100) * 16

            fig.add_trace(go.Scatter(
                x=df['Est EPS Growth'], y=df['Current Valuation'],
                mode='markers+text', text=df['DisplayLabel'],
                textposition="top center",
                textfont=dict(family="Arial", size=10, color="#495057"),
                marker=dict(size=marker_sizes, color='#0969da', line=dict(width=1, color='white'), opacity=0.8)
            ))

        fig.update_layout(template="plotly_white", height=780,
                          xaxis=dict(title="Growth (%)", range=[-lim_x, lim_x]),
                          yaxis=dict(title="Valuation (%)", range=[-lim_y, lim_y]))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.dataframe(df[['Ticker', 'Rating', 'Safety Score', 'Current Valuation', 'Dividend Yield']]
                     .sort_values('Safety Score', ascending=False), use_container_width=True)
else:
    st.warning("No data found. Please upload a CSV or ensure 'sp500_dataset.csv' is in your GitHub folder.")
