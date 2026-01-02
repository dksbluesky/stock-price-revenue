import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# --- 頁面設定 ---
st.set_page_config(page_title="財務瀑布圖分析", layout="wide")

# CSS 優化 (手機版字體調整)
st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 5rem;}
    h1 {text-align: center;}
</style>
""", unsafe_allow_html=True)

st.title("📉 企業獲利階梯 (瀑布圖)")
st.caption("清楚展示每一塊錢的營收，是如何經過層層剝削，最後變成淨利的。")

# --- 輸入區 ---
col1, col2 = st.columns([3, 1])
with col1:
    ticker = st.text_input("輸入股票代號", value="2330.TW").upper()
with col2:
    st.write("") ## 排版用
    st.write("") 
    run_btn = st.button("分析", type="primary", use_container_width=True)

if run_btn:
    try:
        with st.spinner('數據計算中...'):
            stock = yf.Ticker(ticker)
            financials = stock.financials
            
            if financials.empty:
                st.error("找不到資料，請確認代號。")
            else:
                # 取得最新數據
                latest = financials.iloc[:, 0]
                date_str = financials.columns[0].strftime('%Y-%m-%d')
                currency = stock.info.get('currency', 'TWD')

                # --- 數據擷取 ---
                rev = latest.get('Total Revenue', 0)
                gross = latest.get('Gross Profit', 0)
                cost = latest.get('Cost Of Revenue', 0)
                # 校正數據: 若無直接成本數據，用反推的
                if cost == 0 and rev > 0: cost = rev - gross
                
                op_inc = latest.get('Operating Income', 0)
                op_exp = gross - op_inc
                net = latest.get('Net Income', 0)
                tax_int = op_inc - net

                # 計算百分比
                gross_margin = (gross / rev) * 100 if rev else 0
                net_margin = (net / rev) * 100 if rev else 0

                # --- 數字格式化函式 ---
                def fmt(n):
                    return f"{n/1e8:.1f}億" if currency == 'TWD' else f"{n/1e9:.1f}B"

                # --- 準備瀑布圖數據 ---
                # 邏輯: 營收(正) -> 扣成本(負) -> 毛利(小計) -> 扣費用(負) -> 營益(小計) -> 扣稅(負) -> 淨利(總計)
                
                x_data = ["總營收", "營業成本", "毛利 (第一關)", "營業費用", "營業利益 (第二關)", "稅/利息/其他", "淨利 (最後所得)"]
                
                # y_data 裡的負數代表「往下掉」的階梯
                y_data = [
                    rev,            # 營收
                    -cost,          # 扣成本
                    0,              # 毛利 (由 Plotly 自動計算，設0即可)
                    -op_exp,        # 扣費用
                    0,              # 營益 (自動計算)
                    -tax_int,       # 扣稅
                    0               # 淨利 (自動計算)
                ]
                
                # measure 告訴 Plotly 哪一條是「總數」，哪一條是「變化量」
                measure = ["absolute", "relative", "total", "relative", "total", "relative", "total"]
                
                # 顯示在柱子上的文字
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
                    # 設定顏色: 增加(綠), 減少(紅), 總計(藍)
                    increasing = {"marker":{"color":"#2ECC71"}}, # 綠
                    decreasing = {"marker":{"color":"#E74C3C"}}, # 紅
                    totals     = {"marker":{"color":"#3498DB"}}   # 藍 (小計/總計)
                ))

                fig.update_layout(
                    title = f"{ticker} 獲利結構瀑布圖 ({date_str})",
                    showlegend = False,
                    font=dict(size=14),
                    height=600
                )

                st.plotly_chart(fig, use_container_width=True)

                # --- 下方重點摘要 ---
                st.markdown("### 📊 快速解讀")
                c1, c2, c3 = st.columns(3)
                c1.metric("營收規模", fmt(rev))
                c2.metric("毛利率 (扣完成本)", f"{gross_margin:.1f}%", help="越高代表產品越有競爭力")
                c3.metric("淨利率 (扣完全部)", f"{net_margin:.1f}%", help="真正放進口袋的錢")

    except Exception as e:
        st.error(f"發生錯誤: {e}")
