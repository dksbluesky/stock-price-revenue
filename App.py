import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# --- 設定網頁標題與寬度 ---
st.set_page_config(page_title="專業財報儀表板", layout="wide")

# --- 自定義 CSS 讓介面更乾淨 ---
st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    h1 {text-align: center; color: #ffffff;}
</style>
""", unsafe_allow_html=True)

st.title("💰 企業資金流向分析")
st.markdown("<div style='text-align: center; color: #888;'>輸入股票代號，一秒看穿公司是用技術賺錢，還是做苦工</div>", unsafe_allow_html=True)
st.write("") # 空行

# --- 上方輸入區 ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    ticker = st.text_input("請輸入股票代號 (台股加 .TW, 美股直接打)", value="2330.TW").upper()
    run_btn = st.button("🚀 開始分析", use_container_width=True, type="primary")

if run_btn:
    try:
        with st.spinner('正在分析財報數據...'):
            stock = yf.Ticker(ticker)
            financials = stock.financials
            
            if financials.empty:
                st.error(f"找不到 {ticker} 的資料，請確認代號正確。")
            else:
                # 取得最新數據
                latest = financials.iloc[:, 0]
                date_str = financials.columns[0].strftime('%Y-%m-%d')
                currency = stock.info.get('currency', 'TWD')

                # --- 數據處理 ---
                rev = latest.get('Total Revenue', 0)
                gross = latest.get('Gross Profit', 0)
                cost = latest.get('Cost Of Revenue', 0)
                if cost == 0 and rev > 0: cost = rev - gross
                
                op_inc = latest.get('Operating Income', 0)
                op_exp = gross - op_inc
                net = latest.get('Net Income', 0)
                tax_int = op_inc - net

                # 計算百分比 (讓使用者更容易懂)
                gross_margin = (gross / rev) * 100 if rev else 0
                net_margin = (net / rev) * 100 if rev else 0

                # --- 設定顏色邏輯 (Sankey 核心) ---
                # 節點顏色: 營收(藍), 成本/費用(紅), 利潤(綠)
                node_colors = [
                    "#2E86C1", # 0 總營收 (藍)
                    "#E74C3C", # 1 成本 (紅)
                    "#27AE60", # 2 毛利 (綠)
                    "#E74C3C", # 3 費用 (紅)
                    "#27AE60", # 4 營益 (綠)
                    "#95A5A6", # 5 稅/雜項 (灰)
                    "#2ECC71"  # 6 淨利 (亮綠)
                ]

                # 流動顏色: 帶透明度，讓視覺不擁擠
                # 0->1(成本), 0->2(毛利), 2->3(費用), 2->4(營益), 4->5(稅), 4->6(淨利)
                link_colors = [
                    "rgba(231, 76, 60, 0.4)",  # 紅流: 營收->成本 (花掉)
                    "rgba(39, 174, 96, 0.4)",  # 綠流: 營收->毛利 (賺到)
                    "rgba(231, 76, 60, 0.4)",  # 紅流: 毛利->費用 (花掉)
                    "rgba(39, 174, 96, 0.6)",  # 綠流: 毛利->營益 (賺到)
                    "rgba(149, 165, 166, 0.4)",# 灰流: 營益->稅
                    "rgba(46, 204, 113, 0.8)"  # 亮綠: 營益->淨利 (最終口袋)
                ]

                # --- 準備標籤 (加上 % 數與金額簡寫) ---
                def fmt(num):
                    if num > 1e9: return f"{num/1e9:.1f}B" # 十億
                    if num > 1e6: return f"{num/1e6:.1f}M" # 百萬
                    return f"{num:,.0f}"

                labels = [
                    f"總營收<br>{fmt(rev)}", 
                    f"成本 (花掉)<br>{fmt(cost)}", 
                    f"毛利 (剩{gross_margin:.1f}%)<br>{fmt(gross)}", 
                    f"營業費用<br>{fmt(op_exp)}", 
                    f"本業獲利<br>{fmt(op_inc)}", 
                    f"稅/利息<br>{fmt(tax_int)}", 
                    f"淨利 (最後實拿 {net_margin:.1f}%)<br>{fmt(net)}"
                ]

                # --- 繪圖 ---
                fig = go.Figure(data=[go.Sankey(
                    node=dict(
                        pad=20, thickness=20,
                        line=dict(color="white", width=0.5),
                        label=labels,
                        color=node_colors,
                        hovertemplate='%{label}<extra></extra>' # 滑鼠移過去顯示清楚
                    ),
                    link=dict(
                        source=[0, 0, 2, 2, 4, 4],
                        target=[1, 2, 3, 4, 5, 6],
                        value=[cost, gross, op_exp, op_inc, tax_int, net],
                        color=link_colors
                    )
                )])
                
                # 更新版面設定 (背景透明，字體放大)
                fig.update_layout(
                    title_text=f"{ticker} ({date_str}) 單位: {currency}",
                    font=dict(size=14, color="white"),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=600
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # --- 下方重點指標 ---
                m1, m2, m3 = st.columns(3)
                m1.metric("💰 總營收", fmt(rev))
                m2.metric("📈 毛利率 (技術力)", f"{gross_margin:.1f}%")
                m3.metric("💵 淨利率 (真實獲利)", f"{net_margin:.1f}%")

    except Exception as e:
        st.error(f"發生錯誤: {e}")
