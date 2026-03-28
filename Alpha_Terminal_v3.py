import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. Global UI & Typography Guard ---
st.set_page_config(layout="wide", page_title="ALPHA TERMINAL")

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


# --- 2. Professional Data Engine (EOD & Risk Ledger) ---
def load_terminal_data(uploaded_files):
    dfs = {}
    # Safety Score mapping per user requirements (Memory: 2026-02-20)
    # AAA = 100, AA+ = 95, etc.
    rating_map = {
        'AAA': 100, 'AA+': 95, 'AA': 90, 'AA-': 85, 'A+': 80, 'A': 75, 'A-': 70,
        'BBB+': 65, 'BBB': 60, 'BBB-': 55, 'BB+': 45, 'BB': 40, 'B+': 30, 'B': 20
    }

    for file in uploaded_files:
        df = None
        for enc in ['utf-8', 'latin1', 'cp1252']:
            try:
                file.seek(0)
                df = pd.read_csv(file, encoding=enc)
                break
            except:
                continue

        if df is not None:
            # Ticker & Metric Cleaning
            df['Ticker'] = df['Ticker'].astype(str).str.split(':').str[0].str.strip()

            num_cols = ['Closing Price', 'Dividend Yield', 'Est EPS Growth',
                        'Current Valuation', 'P/E', 'P/OCF(FFO)', 'P/FCFE(AFFO)']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[$,%x,]', '', regex=True),
                                            errors='coerce')

            # Risk Ledger: Rating and Safety Score
            df['Rating'] = df['Credit Rating']
            df['Safety Score'] = df['Credit Rating'].map(rating_map).fillna(50)
            dfs[file.name] = df
    return dfs


# --- 3. Sidebar Execution Desk ---
st.sidebar.header("📊 TRADING DESK")
files = st.sidebar.file_uploader("Upload EOD CSV Datasets", accept_multiple_files=True)

if files:
    data_map = load_terminal_data(files)
    selected_names = [f.name for f in files if st.sidebar.checkbox(f.name, value=True, key=f"chk_{f.name}")]

    if len(selected_names) > 0:
        start_df = data_map[selected_names[0]]
        df = data_map[selected_names[-1]].copy()

        # --- Sidebar Filters ---
        st.sidebar.divider()

        # 1. Sector Filter
        all_sects = df['GICS Sector'].dropna().unique().tolist()
        sel_sects = st.sidebar.multiselect("GICS Sector Filter", all_sects)

        # 2. Yield% Slider Filter
        max_y = float(df['Dividend Yield'].max()) if not df['Dividend Yield'].dropna().empty else 10.0
        yield_range = st.sidebar.slider(
            "Filter by Dividend Yield (%)",
            min_value=0.0,
            max_value=max_y if max_y > 0 else 10.0,
            value=(0.0, max_y if max_y > 0 else 10.0),
            step=0.1
        )

        # 3. Safety Score Slider Filter (Added per request)
        safety_range = st.sidebar.slider(
            "Filter by Safety Score (Credit Quality)",
            min_value=0,
            max_value=100,
            value=(0, 100),
            step=5
        )

        # Apply Global Filters
        if sel_sects:
            df = df[df['GICS Sector'].isin(sel_sects)]

        df = df[(df['Dividend Yield'] >= yield_range[0]) & (df['Dividend Yield'] <= yield_range[1])]
        df = df[(df['Safety Score'] >= safety_range[0]) & (df['Safety Score'] <= safety_range[1])]

        # --- Label Construction (Ticker Bold, Yield Unbold) ---
        df['DisplayLabel'] = df.apply(
            lambda x: f"<b>{x['Ticker']}</b> ({x['Dividend Yield']:.2f}%)" if pd.notnull(
                x['Dividend Yield']) else f"<b>{x['Ticker']}</b>",
            axis=1
        )

        tabs = st.tabs(["🎯 Alpha Radar", "📋 Execution Screener", "📈 Sector Alpha"])

        with tabs[0]:
            fig = go.Figure()

            # Quadrant Lock
            lim_x = max(df['Est EPS Growth'].abs().max() * 1.1, 15) if not df.empty else 15
            lim_y = max(df['Current Valuation'].abs().max() * 1.1, 15) if not df.empty else 15
            fig.add_hline(y=0, line_color="#dee2e6", line_width=1)
            fig.add_vline(x=0, line_color="#dee2e6", line_width=1)

            # Historical Trend Tails
            if len(selected_names) > 1 and not df.empty:
                trend_data = pd.merge(
                    start_df[['Ticker', 'Est EPS Growth', 'Current Valuation']],
                    df[['Ticker', 'Est EPS Growth', 'Current Valuation']],
                    on='Ticker', suffixes=('_start', '_end')
                ).dropna()

                for _, row in trend_data.iterrows():
                    l_color = "rgba(40, 167, 69, 0.3)" if row['Current Valuation_end'] < row[
                        'Current Valuation_start'] else "rgba(220, 53, 69, 0.2)"
                    fig.add_trace(go.Scatter(
                        x=[row['Est EPS Growth_start'], row['Est EPS Growth_end']],
                        y=[row['Current Valuation_start'], row['Current Valuation_end']],
                        mode='lines', line=dict(color=l_color, width=1.2, dash='dot'),
                        hoverinfo='skip', showlegend=False
                    ))

            # --- ENHANCEMENT #3: SAFETY SCORE SIZING ---
            if not df.empty:
                marker_sizes = 8 + (df['Safety Score'] / 100) * 16

                fig.add_trace(go.Scatter(
                    x=df['Est EPS Growth'],
                    y=df['Current Valuation'],
                    mode='markers+text',
                    text=df['DisplayLabel'],
                    textposition="top center",
                    textfont=dict(family="Arial, sans-serif", size=10, color="#495057"),
                    marker=dict(
                        size=marker_sizes,
                        color='#0969da',
                        line=dict(width=1, color='white'),
                        opacity=0.85
                    ),
                    hovertemplate="<b>%{text}</b><br>Rating: %{customdata[0]}<br>Safety Score: %{customdata[1]}<br>Valuation: %{y}%<extra></extra>",
                    customdata=df[['Rating', 'Safety Score']]
                ))

            fig.update_layout(
                template="plotly_white", height=780,
                xaxis=dict(title="Growth Trend (%)", range=[-lim_x, lim_x], gridcolor="#f8f9fa"),
                yaxis=dict(title="Valuation Stretch (%)", range=[-lim_y, lim_y], gridcolor="#f8f9fa"),
                margin=dict(l=20, r=20, t=20, b=20)
            )
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
                agg = df.groupby('GICS Sector').agg({'Dividend Yield': 'mean', 'Safety Score': 'mean'}).reset_index()
                fig_sec = go.Figure(data=[
                    go.Bar(name='Avg Yield', x=agg['GICS Sector'], y=agg['Dividend Yield'], marker_color='#2ea44f'),
                    go.Bar(name='Avg Safety Score', x=agg['GICS Sector'], y=agg['Safety Score'], marker_color='#0969da')
                ])
                fig_sec.update_layout(template="plotly_white", barmode='group')
                st.plotly_chart(fig_sec, use_container_width=True)
            else:
                st.warning("No data matches the current filters.")
else:
    st.info("Upload EOD CSV datasets to initialize the Terminal.")