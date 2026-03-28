import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

# --- 1. Global UI & Typography Guard ---
st.set_page_config(layout="wide", page_title="Alpha Terminal v1.1", page_icon="🎯")

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

# --- 2. Professional Data Engine (Bulletproof Version) ---
def load_terminal_data(file_source, is_path=False):
    rating_map = {
        'AAA': 100, 'AA+': 95, 'AA': 90, 'AA-': 85, 'A+': 80, 'A': 75, 'A-': 70,
        'BBB+': 65, 'BBB': 60, 'BBB-': 55, 'BB+': 45, 'BB': 40, 'B+': 30, 'B': 20
    }
    
    try:
        # Use utf-8-sig to automatically handle Excel BOM markers
        if is_path:
            df = pd.read_csv(file_source, encoding='utf-8-sig')
        else:
            file_source.seek(0)
            df = pd.read_csv(file_source, encoding='utf-8-sig')
            
        # CLEAN HEADERS: Remove any invisible spaces or newlines
        df.columns = df.columns.str.strip()

        # FALLBACK: If 'Ticker' isn't found exactly, look for it case-insensitively
        if 'Ticker' not in df.columns:
            match = [c for c in df.columns if c.lower() == 'ticker']
            if match:
                df.rename(columns={match[0]: 'Ticker'}, inplace=True)
            else:
                st.error(f"Critical Error: 'Ticker' column missing. Found: {list(df.columns)}")
                return None

        # Ticker & Metric Cleaning
        df['Ticker'] = df['Ticker'].astype(str).str.split(':').str[0].str.strip()
        
        # Define necessary columns for the Alpha Radar
        num_cols = {
            'Closing Price': 'price',
            'Dividend Yield': 'yield',
            'Est EPS Growth': 'growth',
            'Current Valuation': 'valuation',
            'Safety Score': 'safety'
        }

        for col in df.columns:
            # Clean numeric strings ($ , % x)
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(r'[$,%x,]', '', regex=True)
                # Convert to numeric, but keep as object if it's a name/sector
                converted = pd.to_numeric(df[col], errors='coerce')
                if not converted.isna().all():
                    df[col] = converted

        # Risk Ledger (Calculated from your Credit Rating requirement)
        if 'Credit Rating' in df.columns:
            df['Rating'] = df['Credit Rating']
            df['Safety Score'] = df['Credit Rating'].map(rating_map).fillna(50)
        else:
            df['Safety Score'] = 50 # Fallback
            
        return df
    except Exception as e:
        st.error(f"Engine Error: {e}")
        return None

# --- 3. Sidebar & Auto-Load Logic ---
st.sidebar.header("📊 DATA CONTROLS")

# Ensure the filename matches exactly what is on GitHub (Case Sensitive)
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
    # Use repository default
    active_df = load_terminal_data(DEFAULT_FILE, is_path=True)
    if active_df is not None:
        mode_label = f"Auto-Load: {DEFAULT_FILE}"
        st.sidebar.success(f"✅ Loaded: {DEFAULT_FILE}")
    else:
        st.sidebar.error(f"❌ Failed to parse {DEFAULT_FILE}")

# --- 4. Main Interface ---
if active_df is not None:
    df = active_df.copy()
    
    # Sidebar Filters
    st.sidebar.divider()
    y_col = 'Dividend Yield' if 'Dividend Yield' in df.columns else None
    
    if y_col:
        max_y = float(df[y_col].max()) if not df[y_col].dropna().empty else 10.0
        yield_range = st.sidebar.slider("Yield Filter (%)", 0.0, max_y, (0.0, max_y))
        df = df[(df[y_col] >= yield_range[0]) & (df[y_col] <= yield_range[1])]

    safety_range = st.sidebar.slider("Safety Score Filter", 0, 100, (0, 100))
    df = df[(df['Safety Score'] >= safety_range[0]) & (df['Safety Score'] <= safety_range[1])]
    
    # Label Logic (Bold Ticker)
    df['DisplayLabel'] = df.apply(lambda x: f"<b>{x['Ticker']}</b> ({x['Dividend Yield']:.2f}%)", axis=1)

    tabs = st.tabs(["🎯 Alpha Radar", "📋 Execution Ledger"])

    with tabs[0]:
        st.caption(f"Terminal Status: {mode_label}")
        fig = go.Figure()
        
        # Calculate dynamic limits based on dataset
        lim_x = max(df['Est EPS Growth'].abs().max() * 1.1, 15) if not df.empty else 15
        lim_y = max(df['Current Valuation'].abs().max() * 1.1, 15) if not df.empty else 15
        
        fig.add_hline(y=0, line_color="#dee2e6", line_width=1)
        fig.add_vline(x=0, line_color="#dee2e6", line_width=1)

        if not df.empty:
            # Safety Score Sizing (Enhancement #3)
            marker_sizes = 8 + (df['Safety Score'] / 100) * 16

            fig.add_trace(go.Scatter(
                x=df['Est EPS Growth'], y=df['Current Valuation'],
                mode='markers+text', text=df['DisplayLabel'],
                textposition="top center",
                textfont=dict(family="Arial", size=10, color="#495057"),
                marker=dict(size=marker_sizes, color='#0969da', line=dict(width=1, color='white'), opacity=0.8)
            ))

        fig.update_layout(template="plotly_white", height=780,
                          xaxis=dict(title="Est EPS Growth (%)", range=[-lim_x, lim_x]),
                          yaxis=dict(title="Current Valuation (%)", range=[-lim_y, lim_y]))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.dataframe(df.sort_values('Safety Score', ascending=False), use_container_width=True)
else:
    st.warning("⚠️ Waiting for data. Please upload a CSV or ensure 'sp500_dataset.csv' is in your GitHub folder.")
