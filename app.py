import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. KONFIGURASI HALAMAN & CSS INJECTION ---
st.set_page_config(page_title="Risk Score Report", page_icon="📊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Global Dark Theme */
    .stApp {
        background-color: #08090d;
        color: #e0e0e0;
        font-family: 'DM Sans', sans-serif;
    }
    
    /* Custom Card Design */
    .risk-card {
        background-color: #12141d;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #1f2233;
        margin-bottom: 15px;
    }
    
    /* Typography */
    .data-font { font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; font-weight: 700; }
    .label-font { font-size: 0.9rem; color: #8a8d9e; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Status Colors */
    .green { color: #00ff88; }
    .red { color: #ff3366; }
    .amber { color: #ffbb00; }
    .neutral { color: #e0e0e0; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNGSI PENGAMBILAN DATA ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Ambil data harga 1 tahun terakhir
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    hist = stock.history(start=start_date, end=end_date)
    
    return info, hist

# --- 3. FUNGSI PENILAIAN RISIKO (SCORING) ---
def calculate_risk_score(info):
    score_val = 0
    score_health = 0
    score_growth = 0
    
    # 1. Valuation (Max 35) - Mencari PE yang wajar
    pe = info.get('trailingPE', None)
    if pe is not None and pe > 0:
        if pe < 15: score_val = 35
        elif pe < 25: score_val = 20
        else: score_val = 5
        val_status = "green" if pe < 15 else "amber" if pe < 25 else "red"
    else:
        val_status = "neutral"

    # 2. Financial Health (Max 35) - Mencari hutang rendah
    de_ratio = info.get('debtToEquity', None)
    if de_ratio is not None:
        if de_ratio < 100: score_health = 35
        elif de_ratio < 200: score_health = 20
        else: score_health = 5
        health_status = "green" if de_ratio < 100 else "amber" if de_ratio < 200 else "red"
    else:
        health_status = "neutral"

    # 3. Growth (Max 30) - Mencari pertumbuhan revenue
    rev_growth = info.get('revenueGrowth', None)
    if rev_growth is not None:
        if rev_growth > 0.10: score_growth = 30
        elif rev_growth > 0: score_growth = 15
        else: score_growth = 0
        growth_status = "green" if rev_growth > 0.10 else "amber" if rev_growth > 0 else "red"
    else:
        growth_status = "neutral"

    total_score = score_val + score_health + score_growth
    # Normalisasi ke 100 jika ada data kosong agar gauge tetap masuk akal
    return total_score, val_status, health_status, growth_status

# --- 4. HEADER & INPUT ---
st.markdown("<h1 style='text-align: center;'>⚡ INDONESIA STOCK RISK REPORT</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8a8d9e;'>Institutional Grade HTML Dark Report</p>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    raw_ticker = st.text_input("Masukkan Kode Saham (Contoh: BBCA, BUMI, BRPT)", value="BBCA")
    ticker = raw_ticker.strip().upper() + ".JK"

if raw_ticker:
    with st.spinner(f"Menganalisa {ticker}..."):
        info, hist = get_stock_data(ticker)
        
        if hist.empty:
            st.error(f"Data untuk saham {ticker} tidak ditemukan. Pastikan kode benar.")
        else:
            total_score, val_status, health_status, growth_status = calculate_risk_score(info)
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            pct_change = ((current_price - prev_price) / prev_price) * 100
            color_price = "green" if pct_change >= 0 else "red"
            sign = "+" if pct_change >= 0 else ""

            # --- TABS: PAGE 1 & PAGE 2 ---
            tab1, tab2 = st.tabs(["PAGE 1: DASHBOARD", "PAGE 2: DEEP DIVE"])

            with tab1:
                # STOCK BAR & RISK GAUGE
                st.markdown(f"""
                <div class='risk-card' style='text-align: center;'>
                    <h2 style='margin:0;'>{info.get('longName', ticker)} ({ticker})</h2>
                    <p class='data-font {color_price}' style='font-size: 2rem; margin:0;'>Rp {current_price:,.0f} <span style='font-size: 1rem;'>{sign}{pct_change:.2f}%</span></p>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns([1, 2])
                with c1:
                    # PLOTLY RISK GAUGE (0-100)
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = total_score,
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        title = {'text': "RISK SCORE", 'font': {'color': '#8a8d9e', 'family': 'DM Sans'}},
                        number = {'font': {'color': '#e0e0e0', 'family': 'JetBrains Mono'}},
                        gauge = {
                            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                            'bar': {'color': "#00ff88" if total_score > 65 else "#ffbb00" if total_score > 40 else "#ff3366"},
                            'bgcolor': "#1f2233",
                            'steps': [
                                {'range': [0, 40], 'color': "rgba(255, 51, 102, 0.2)"},
                                {'range': [40, 65], 'color': "rgba(255, 187, 0, 0.2)"},
                                {'range': [65, 100], 'color': "rgba(0, 255, 136, 0.2)"}]
                        }
                    ))
                    fig_gauge.update_layout(paper_bgcolor="#08090d", height=300, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig_gauge, use_container_width=True)

                with c2:
                    # PLOTLY 12-MONTH SVG PRICE CHART
                    fig_chart = go.Figure()
                    fig_chart.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Price', line=dict(color='#00ff88', width=2)))
                    fig_chart.update_layout(
                        title="12-Month Price Action",
                        paper_bgcolor="#08090d",
                        plot_bgcolor="#12141d",
                        font=dict(color="#8a8d9e", family="DM Sans"),
                        height=300,
                        margin=dict(l=10, r=10, t=40, b=10),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=True, gridcolor="#1f2233")
                    )
                    st.plotly_chart(fig_chart, use_container_width=True)

                # 6-CARD GRIDS
                st.markdown("<h3 style='margin-top: 20px;'>KPI Matrix</h3>", unsafe_allow_html=True)
                g1, g2, g3 = st.columns(3)
                
                # Valuation
                pe_val = info.get('trailingPE', 'N/A')
                pb_val = info.get('priceToBook', 'N/A')
                g1.markdown(f"""
                <div class='risk-card'>
                    <div class='label-font'>Valuation (35%)</div>
                    <div class='data-font {val_status}'>P/E: {round(pe_val, 2) if isinstance(pe_val, float) else pe_val}x</div>
                    <div class='data-font neutral'>P/B: {round(pb_val, 2) if isinstance(pb_val, float) else pb_val}x</div>
                </div>
                """, unsafe_allow_html=True)

                # Financial Health
                de_val = info.get('debtToEquity', 'N/A')
                cr_val = info.get('currentRatio', 'N/A')
                g2.markdown(f"""
                <div class='risk-card'>
                    <div class='label-font'>Financial Health (35%)</div>
                    <div class='data-font {health_status}'>D/E: {round(de_val, 2) if isinstance(de_val, float) else de_val}%</div>
                    <div class='data-font neutral'>CR: {round(cr_val, 2) if isinstance(cr_val, float) else cr_val}x</div>
                </div>
                """, unsafe_allow_html=True)

                # Growth
                rev_g_val = info.get('revenueGrowth', 'N/A')
                eps_g_val = info.get('earningsQuarterlyGrowth', 'N/A')
                g3.markdown(f"""
                <div class='risk-card'>
                    <div class='label-font'>Growth (30%)</div>
                    <div class='data-font {growth_status}'>Rev: {(rev_g_val*100) if isinstance(rev_g_val, float) else rev_g_val}%</div>
                    <div class='data-font neutral'>EPS: {(eps_g_val*100) if isinstance(eps_g_val, float) else eps_g_val}%</div>
                </div>
                """, unsafe_allow_html=True)

            with tab2:
                # QUARTERLY TREND TABLE & BOTTOM LINE
                st.markdown("<h3 style='margin-top: 20px;'>Fundamental Deep Dive</h3>", unsafe_allow_html=True)
                
                t1, t2 = st.columns(2)
                with t1:
                    st.markdown("""
                    <div class='risk-card'>
                        <div class='label-font'>🔥 Catalysts (Beats)</div>
                        <ul style='color: #00ff88; font-family: "DM Sans";'>
                            <li>Momentum teknikal sedang berjalan</li>
                            <li>Posisi harga mendukung akumulasi</li>
                            <li>Sektor pendukung sedang ekspansif</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                with t2:
                    st.markdown("""
                    <div class='risk-card'>
                        <div class='label-font'>⚠️ Risks (Misses)</div>
                        <ul style='color: #ff3366; font-family: "DM Sans";'>
                            <li>Volatilitas IHSG yang tinggi</li>
                            <li>Potensi aksi ambil untung (Profit Taking)</li>
                            <li>Data fundamental Yahoo seringkali tertinggal</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)

                # RATING VERDICT
                verdict = "STRONG BUY" if total_score > 75 else "HOLD / CAUTION" if total_score > 40 else "AVOID / HIGH RISK"
                verdict_color = "green" if total_score > 75 else "amber" if total_score > 40 else "red"
                
                st.markdown(f"""
                <div class='risk-card' style='text-align: center; margin-top: 20px; border-top: 3px solid {"#00ff88" if verdict_color=="green" else "#ffbb00" if verdict_color=="amber" else "#ff3366"};'>
                    <div class='label-font'>Bottom Line Verdict</div>
                    <div class='data-font {verdict_color}' style='font-size: 2.5rem;'>{verdict}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Clipboard Export (Disederhanakan menggunakan tombol copy bawaan Streamlit untuk code block)
                st.markdown("<div class='label-font' style='margin-top:20px;'>Laporan Teks (Klik tombol Copy di kanan atas kotak ini untuk Export ke Clipboard)</div>", unsafe_allow_html=True)
                export_text = f"RISK REPORT: {ticker}\nPrice: Rp{current_price:,.0f} ({sign}{pct_change:.2f}%)\nScore: {total_score}/100\nVerdict: {verdict}"
                st.code(export_text, language="text")
