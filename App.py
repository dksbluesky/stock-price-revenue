import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

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

# --- 核心功能：抓資料 ---
@st.cache_data(ttl=3600) 
def get_stock_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        financials = stock.financials
        
        if financials.empty:
            return None, "找不到數據，請確認代號。"
            
        latest = financials.iloc[:, 0]
        date_str = financials.columns[0].strftime('%Y-%m-%d')
        currency = stock.info.get('currency', 'TWD')
        
        data = {
            'rev': latest.get('Total Revenue', 0),
            'gross': latest.get('Gross Profit', 0),
            'cost': latest.get('Cost Of Revenue', 0),
            'op_inc': latest.get('Operating Income', 0),
            'net': latest.get('Net Income', 0),
            'date': date_str,
            'currency': currency
        }
        return data, None

    except Exception as e:
        return None, str(e)

# --- 輸入區 ---
col1, col2 = st.columns([3, 1])
with col1:
    raw_ticker = st.text_input("輸入股票代號 (例如 2330)", value="2330")
with col2:
    st.write("") 
    st.write("") 
    run_btn = st.button("分析", type="primary", use_container_width=True)

if run_btn:
    ticker = raw_ticker.upper().strip()
    if ticker.isdigit() and len(ticker) == 4:
        ticker += ".TW"
    
    st.info(f"正在搜尋代號: {ticker}")

    data, error_msg = get_stock_data(ticker)

    if error_msg:
        st.error(f"❌ {error_msg}")
        if "Too Many Requests" in str(error_msg):
             st.warning("⚠️ Yahoo 目前忙線中，請稍後再試。")
    elif data:
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
            return f"{n/1e8:.1f}億" if data['currency'] == 'TWD' else f"{n/1e9:.1f}B"

        # --- 瀑布圖數據 ---
        x_data = ["總營收", "營業成本", "毛利", "營業費用", "營業利益", "稅/利息", "淨利"]
        y_data = [rev, -cost, 0, -op_exp, 0, -tax_int, 0]
        measure = ["absolute", "relative", "total", "relative", "total", "relative", "total"]
        
        # 這裡把 text_v 寫在一起，避免複製遺漏
        text_v = [f"{fmt(rev)}", f"-{fmt(cost)}", f"{fmt(gross)}<br>({gross_margin:.1f}%)", f"-{fmt(op_exp)}", f"{fmt(op_inc)}", f"-{fmt(tax_int)}", f"{fmt(net)}<br>({net_margin:.1f}%)"]

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
