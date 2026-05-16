import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# --- 頁面設定 ---
st.set_page_config(page_title="財務瀑布圖分析", layout="wide")

# CSS 優化
st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 5rem;}
    h1 {text-align: center;}
</style>
""", unsafe_allow_html=True)

st.title("📉 企業獲利階梯 (瀑布圖)")

# --- 備份數據 (已更新為 2025 推算數據) ---
# 既然是 2026 年初，我們用 2025 全年的推算數據做備份
BACKUP_DATA = {
    '2330.TW': {
        'rev': 3105000000000,
        'gross': 1750000000000,
        'cost': 1355000000000,
        'op_inc': 1420000000000,
        'net': 1250000000000,
        'currency': 'TWD',
        'date': '2025-12-31 (年度推算)',
        'eps': 48.2,
        'pe': 24.5,
        'fwd_pe': 21.8,
        'fwd_eps': 55.0,
    }
}

# --- 核心功能：抓資料 ---
@st.cache_data(ttl=3600) 
def get_stock_data(ticker_symbol):
    # 1. 優先嘗試從 Yahoo 抓取即時資料
    try:
        stock = yf.Ticker(ticker_symbol)
        financials = stock.income_stmt
        if financials.empty:
            financials = stock.financials
        
        if not financials.empty:
            latest = financials.iloc[:, 0]
            date_str = financials.columns[0].strftime('%Y-%m-%d')
            info = stock.info
            currency = info.get('currency', 'TWD')

            data = {
                'rev': latest.get('Total Revenue', 0),
                'gross': latest.get('Gross Profit', 0),
                'cost': latest.get('Cost Of Revenue', 0),
                'op_inc': latest.get('Operating Income', 0),
                'net': latest.get('Net Income', 0),
                'currency': currency,
                'date': date_str,
                'source': 'Yahoo Finance',
                'eps': info.get('trailingEps'),
                'pe': info.get('trailingPE'),
                'fwd_pe': info.get('forwardPE'),
                'fwd_eps': info.get('forwardEps'),
            }
            return data, None
            
    except Exception as e:
        print(f"Yahoo fetch failed: {e}")

    # 2. 如果 Yahoo 失敗，使用備份數據
    if ticker_symbol in BACKUP_DATA:
        return BACKUP_DATA[ticker_symbol], "Yahoo 連線忙線中，已切換至備份數據模式。"
        
    return None, "無法抓取數據，且無此代號的備份資料。"

# --- 輸入區 ---
col1, col2 = st.columns([3, 1])
with col1:
    raw_ticker = st.text_input("輸入股票代號", value="2330")
with col2:
    st.write("") 
    st.write("") 
    run_btn = st.button("分析", type="primary", use_container_width=True)

if run_btn:
    ticker = raw_ticker.upper().strip()
    if ticker.isdigit() and len(ticker) == 4:
        ticker += ".TW"
    
    data, warning_msg = get_stock_data(ticker)

    if warning_msg:
        st.warning(f"⚠️ {warning_msg}")
    elif data and data.get('source') == 'Yahoo Finance':
        st.success(f"✅ 成功從 Yahoo 取得 {ticker} 最新數據")

    if data:
        # --- 數據計算 ---
        rev = data['rev']
        gross = data['gross']
        cost = data['cost']
        if cost == 0 and rev > 0: cost = rev - gross
        
        op_inc = data['op_inc']
        op_exp = gross - op_inc
        net = data['net']
        tax_int = op_inc - net

        gross_margin = (gross / rev) * 100 if rev else 0
        net_margin = (net / rev) * 100 if rev else 0

        def fmt(n):
            if data['currency'] == 'TWD':
                return f"{n/1e8:.1f}億"
            else:
                return f"{n/1e9:.1f}B"

        # --- 瀑布圖數據 ---
        x_data = ["總營收", "營業成本", "毛利", "營業費用", "營業利益", "稅/利息", "淨利"]
        y_data = [rev, -cost, 0, -op_exp, 0, -tax_int, 0]
        measure = ["absolute", "relative", "total", "relative", "total", "relative", "total"]
        
        text_v = [
            f"{fmt(rev)}", 
            f"-{fmt(cost)}", 
            f"{fmt(gross)}<br>({gross_margin:.1f}%)", 
            f"-{fmt(op_exp)}", 
            f"{fmt(op_inc)}", 
            f"-{fmt(tax_int)}", 
            f"{fmt(net)}<br>({net_margin:.1f}%)"
        ]

        # --- 繪圖 ---
        fig = go.Figure(go.Waterfall(
            name = "20", orientation = "v",
            measure = measure,
            x = x_data,
            textposition = "outside",
            text = text_v,
            y = y_data,
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
            increasing = {"marker":{"color":"#2ECC71"}},
            decreasing = {"marker":{"color":"#E74C3C"}},
            totals     = {"marker":{"color":"#3498DB"}}
        ))

        fig.update_layout(
            title = f"{ticker} 獲利結構 ({data['date']})",
            showlegend = False,
            font=dict(size=14),
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📊 重點摘要")
        c1, c2, c3 = st.columns(3)
        c1.metric("營收", fmt(rev))
        c2.metric("毛利率", f"{gross_margin:.1f}%")
        c3.metric("淨利率", f"{net_margin:.1f}%")

        st.markdown("### 💹 估值指標")
        v1, v2, v3, v4 = st.columns(4)

        eps = data.get('eps')
        pe = data.get('pe')
        fwd_pe = data.get('fwd_pe')
        fwd_eps = data.get('fwd_eps')
        currency = data.get('currency', 'TWD')

        v1.metric("EPS (TTM)", f"{eps:.2f} {currency}" if eps else "N/A")
        v2.metric("本益比 P/E", f"{pe:.1f}x" if pe else "N/A")
        v3.metric("遠期本益比 Fwd P/E", f"{fwd_pe:.1f}x" if fwd_pe else "N/A")
        v4.metric("預估 EPS (Fwd)", f"{fwd_eps:.2f} {currency}" if fwd_eps else "N/A")
    
    else:
        st.error("❌ 找不到數據。Yahoo 暫時封鎖了連線，請稍後再試。")
