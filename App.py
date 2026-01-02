import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# 設定網頁標題與寬度
st.set_page_config(page_title="股市資金流向儀表板", layout="wide")

st.title("💰 企業財報資金流向 (Sankey Diagram)")
st.markdown("輸入股票代號，查看資金如何從營收流向淨利。")

# 側邊欄輸入框
ticker = st.text_input("輸入股票代號 (例如: 2330.TW, AAPL, TSLA)", value="2330.TW").upper()

if st.button("開始分析"):
    with st.spinner('正在抓取財報數據...'):
        try:
            stock = yf.Ticker(ticker)
            financials = stock.financials
            
            if financials.empty:
                st.error("找不到財報數據，請確認代號是否正確 (台股請加 .TW)。")
            else:
                # 取得最新一年數據
                latest_data = financials.iloc[:, 0]
                date_label = financials.columns[0].strftime('%Y-%m-%d')
                
                # 提取數據 (邏輯同前)
                revenue = latest_data.get('Total Revenue', 0)
                gross_profit = latest_data.get('Gross Profit', 0)
                cost_of_revenue = latest_data.get('Cost Of Revenue', 0)
                if cost_of_revenue == 0 and revenue > 0:
                     cost_of_revenue = revenue - gross_profit

                operating_income = latest_data.get('Operating Income', 0)
                operating_expenses = gross_profit - operating_income
                net_income = latest_data.get('Net Income', 0)
                tax_and_interest = operating_income - net_income

                # 準備繪圖數據
                labels = ["總營收", "營業成本", "毛利", "營業費用", "營業利益", "稅/利息/其他", "淨利"]
                source = [0, 0, 2, 2, 4, 4]
                target = [1, 2, 3, 4, 5, 6]
                values = [cost_of_revenue, gross_profit, operating_expenses, operating_income, tax_and_interest, net_income]

                # 繪圖
                fig = go.Figure(data=[go.Sankey(
                    node=dict(
                        pad=15, thickness=20, line=dict(color="black", width=0.5),
                        label=labels, color="blue"
                    ),
                    link=dict(
                        source=source, target=target, value=values,
                        color=['#ffcccc', '#ccffcc', '#ffcccc', '#ccffcc', '#ffcccc', '#00cc00']
                    )
                )])
                
                fig.update_layout(title_text=f"{ticker} 資金流向 ({date_label})", font_size=14)
                
                # 顯示圖表 (這就是 Streamlit 強大的地方，一行搞定)
                st.plotly_chart(fig, use_container_width=True)
                
                # 顯示原始數據表格
                st.subheader("原始數據")
                st.dataframe(latest_data)

        except Exception as e:
            st.error(f"發生錯誤: {e}")