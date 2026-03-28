import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

# --- 1. Global UI & Typography Guard ---
st.set_page_config(layout="wide", page_title="QTI's Stock Terminal", page_icon="🎯")

st.markdown("""
    <style>
    /* Professional Light Canvas */
    .stApp { background-color: #FFFFFF; color: #1c1e21; }
    section[data-testid="stSidebar"] { 
        background-color: #f8f9fa !important; 
        border-right: 1px solid #dee2e6; 
    }
    
    /* Typography Logic: 
       Ticker (Bold) vs Yield (Light)
    */
    .js-plotly-plot .plotly .pointtext text {
        font-weight: 300;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    .js-plotly-plot .plotly .pointtext text b {
        font-weight: 700 !important;
    }
    
    h1, h2, h3, p, label, .stMarkdown { font-weight: 400 !important; color: #1c1e21 !important; }
    .stTabs [data-baseweb="tab"] { font-weight: 600 !important; color: #495057; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Professional Data Engine (Bulletproof) ---
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
        
        # Clean numeric strings ($ , % x) for specific common columns
        numeric_targets = ['Closing Price', 'Dividend Yield', 'Est EPS Growth', 
                           'Current Valuation', 'P/E', 'P/OCF(FFO)', 'P/FCFE(AFFO)']
        
        for col in numeric_targets:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'[$,%x,]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Risk Ledger (Calculated from Credit Rating)
        if 'Credit Rating' in df.columns:
            df['Rating'] = df['Credit Rating']
            df['Safety Score'] = df['Credit Rating'].map(rating_map).fillna(50)
        else:
            df['Safety Score'] = 50 
            
        return df
    except Exception as e:
        st.error(f"Engine Error: {e}")
        return None

# --- 3. Sidebar & Auto-Load Logic ---
st.sidebar.header("📊 DATA CONTROLS")

DEFAULT_FILE = "sp500_dataset.csv" 
uploaded_files = st.sidebar.file_uploader("Upload EOD CSV Datasets", accept_multiple_files=True)

active_df = None
start_df = None
mode_label = ""

if uploaded_files:
    data_map = {f.name: load_terminal_data(f) for f in uploaded_files}
    selected_names = [f.name for f in uploaded_files if st.sidebar.checkbox(f.name, value=True, key=f"chk_{f.name}")]
    if selected_names:
        start_df = data_map[selected_names[0]]
        active_df = data_map[selected_names[-1]]
        mode_label = "Live Upload Mode"
elif os.path.exists(DEFAULT_FILE):
    active_df = load_terminal_data(DEFAULT_FILE, is_path=True)
    if active_df is not None:
        mode_label = f"Auto-Load: {DEFAULT_FILE}"
        st.sidebar.success(f"✅ Loaded: {DEFAULT_FILE}")
    else:
        st.sidebar.error(f"❌ Failed to parse {DEFAULT_FILE}")

# --- 4. Main Interface ---
# App Title at the top
st.title("QTI's Stock Terminal")

if active_df is not None:
    df = active_df.copy()
    
    # --- Sidebar Filters ---
    st.sidebar.divider()
    
    # 1. Sector Selector Filter (Added back)
    if 'GICS Sector' in df.columns:
        all_sects = df['GICS Sector'].dropna().unique().tolist()
        sel_sects = st.sidebar.multiselect("GICS Sector Filter", all_sects)
        if sel_sects:
            df = df[df['GICS Sector'].isin(sel_sects)]
    
    # 2. Yield% Slider Filter
    y_col = 'Dividend Yield'
    if y_col in df.columns:
        max_y = float(df[y_col].max()) if not df[y_col].dropna().empty else 10.0
        yield_range = st.sidebar.slider("Yield Filter (%)", 0.0, max_y, (0.0, max_y))
        df = df[(df[y_col] >= yield_range[0]) & (df[y_col] <= yield_range[1])]

    # 3. Safety Score Slider Filter
    safety_range = st.sidebar.slider("Safety Score Filter", 0, 100, (0, 100))
    df = df[(df['Safety Score'] >= safety_range[0]) & (df['Safety Score'] <= safety_range[1])]
    
    # Label Construction (Bold Ticker, Unbold Yield)
    df['DisplayLabel'] = df.apply(
        lambda x: f"<b>{x['Ticker']}</b> ({x['Dividend Yield']:.2f}%)" if pd.notnull(x['Dividend Yield']) else f"<b>{x['Ticker']}</b>", 
        axis=1
    )

    tabs = st.tabs(["🎯 Alpha Radar", "📋 Execution Ledger", "🏛️ Sector Alpha"])

    with tabs[0]:
        st.caption(f"Terminal Status: {mode_label}")
        fig = go.Figure()
        
        # Quadrant Lock
        lim_x = max(df['Est EPS Growth'].abs().max() * 1.1, 15) if not df.empty else 15
        lim_y = max(df['Current Valuation'].abs().max() * 1.1, 15) if not df.empty else 15
        
        fig.add_hline(y=0, line_color="#dee2e6", line_width=1)
        fig.add_vline(x=0, line_color="#dee2e6", line_width=1)

        # Historical Trend Tails (If 2+ files are uploaded)
        if uploaded_files and len(selected_names) > 1 and not df.empty:
            trend_data = pd.merge(
                start_df[['Ticker', 'Est EPS Growth', 'Current Valuation']], 
                df[['Ticker', 'Est EPS Growth', 'Current Valuation']], 
                on='Ticker', suffixes=('_start', '_end')
            ).dropna()

            for _, row in trend_data.iterrows():
                l_color = "rgba(40, 167, 69, 0.3)" if row['Current Valuation_end'] < row['Current Valuation_start'] else "rgba(220, 53, 69, 0.2)"
                fig.add_trace(go.Scatter(
                    x=[row['Est EPS Growth_start'], row['Est EPS Growth_end']],
                    y=[row['Current Valuation_start'], row['Current Valuation_end']],
                    mode='lines', line=dict(color=l_color, width=1.2, dash='dot'),
                    hoverinfo='skip', showlegend=False
                ))

        if not df.empty:
            # Enhancement #3: Safety Score Sizing
            marker_sizes = 8 + (df['Safety Score'] / 100) * 16

            fig.add_trace(go.Scatter(
                x=df['Est EPS Growth'], y=df['Current Valuation'],
                mode='markers+text', text=df['DisplayLabel'],
                textposition="top center",
                textfont=dict(family="Arial, sans-serif", size=10, color="#495057"),
                marker=dict(size=marker_sizes, color='#0969da', line=dict(width=1, color='white'), opacity=0.85),
                hovertemplate="<b>%{text}</b><br>Safety Score: %{customdata}<extra></extra>",
                customdata=df['Safety Score']
            ))

        fig.update_layout(template="plotly_white", height=780,
                          xaxis=dict(title="Est EPS Growth (%)", range=[-lim_x, lim_x], gridcolor="#f8f9fa"),
                          yaxis=dict(title="Current Valuation (%)", range=[-lim_y, lim_y], gridcolor="#f8f9fa"),
                          margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.subheader("Risk-Weighted Execution Ledger")
        cols = ['Ticker', 'Company Name', 'Rating', 'Safety Score', 'Current Valuation', 'P/E', 'Dividend Yield']
        st.dataframe(
            df[cols].sort_values('Safety Score', ascending=False)
            .style.background_gradient(subset=['Safety Score'], cmap='RdYlGn')
            .background_gradient(subset=['Current Valuation'], cmap='RdYlGn_r')
            .format({'Dividend Yield': '{:.2f}%', 'Current Valuation': '{:.2f}%'}),
            use_container_width=True, height=650
        )

    with tabs[2]:
        st.subheader("Sector Yield vs. Quality")
        if not df.empty:
            agg = df.groupby('GICS Sector').agg({'Dividend Yield':'mean', 'Safety Score':'mean'}).reset_index()
            fig_sec = go.Figure(data=[
                go.Bar(name='Avg Yield', x=agg['GICS Sector'], y=agg['Dividend Yield'], marker_color='#2ea44f'),
                go.Bar(name='Avg Safety Score', x=agg['GICS Sector'], y=agg['Safety Score'], marker_color='#0969da')
            ])
            fig_sec.update_layout(template="plotly_white", barmode='group')
            st.plotly_chart(fig_sec, use_container_width=True)

else:
    st.warning("⚠️ Waiting for data. Please upload a CSV or ensure 'sp500_dataset.csv' is in your GitHub folder.")
