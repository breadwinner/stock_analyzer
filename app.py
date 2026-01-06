import streamlit as st
import google.generativeai as genai
import yfinance as yf
import os
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="AI Equity Research Analyst",
    page_icon="📈",
    layout="wide"
)

# --- 2. 安全与配置 ---
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GOOGLE_API_KEY"]
    except:
        pass

if not API_KEY:
    st.error("❌ 未找到 API Key / API Key not found!")
    st.stop()

genai.configure(api_key=API_KEY)

# --- 3. 核心功能函数 ---

def get_financial_data(ticker_symbol):
    """
    使用 yfinance 获取基础财务数据作为 Context
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        # 获取最新的收盘价
        history = stock.history(period="1d")
        if not history.empty:
            current_price = round(history['Close'].iloc[-1], 2)
        else:
            current_price = info.get('currentPrice', 'N/A')

        # 构建数据摘要
        data_context = f"""
        [Financial Data Context for {ticker_symbol}]
        - Current Price: {current_price} {info.get('currency', 'USD')}
        - Market Cap: {info.get('marketCap', 'N/A')}
        - Trailing P/E: {info.get('trailingPE', 'N/A')}
        - Forward P/E: {info.get('forwardPE', 'N/A')}
        - PEG Ratio: {info.get('pegRatio', 'N/A')}
        - Price/Book: {info.get('priceToBook', 'N/A')}
        - Revenue Growth (yoy): {info.get('revenueGrowth', 'N/A')}
        - 52 Week High: {info.get('fiftyTwoWeekHigh', 'N/A')}
        - 52 Week Low: {info.get('fiftyTwoWeekLow', 'N/A')}
        - Sector: {info.get('sector', 'N/A')}
        - Industry: {info.get('industry', 'N/A')}
        """
        return data_context
    except Exception as e:
        return f"Warning: Could not fetch real-time data via yfinance ({str(e)})."

def generate_report(ticker, financial_data, model_name, language):
    """
    调用 Gemini 生成研报，支持多语言
    """
    model = genai.GenerativeModel(model_name)
    
    # 动态设定语言指令
    if language == "English":
        lang_instruction = "The final output MUST be in **ENGLISH**."
    else:
        lang_instruction = "The final output MUST be in **CHINESE (简体中文)**."

    # Prompt 模板
    prompt = f"""
    Role: You are a world-class equity research analyst.
    Task: Conduct a comprehensive, in-depth analysis of the company: {ticker}.
    
    **CRITICAL INSTRUCTION**: {lang_instruction}
    
    Context Data (Real-time):
    {financial_data}
    
    Analysis Framework:
    1. **Fundamental Business**: Deconstruct business model, moat, and financial health.
    2. **Valuation & Ratios**: Analyze P/E, PEG, ROE relative to historicals and peers using the provided data.
    3. **Technical Analysis**: Describe current trend structure (Support/Resistance).
    4. **Industry & Competition**: Macro trends, TAM, and competitive landscape.
    5. **Qualitative**: Management, Risks, and Catalysts.
    6. **Conclusion**: Buy/Hold/Sell rating, Target Price logic, and Risk Mitigation.
    
    Format the response with Markdown headers, bullet points for readability.
    Current Date: {datetime.now().strftime("%Y-%m-%d")}
    """
    
    loading_text = "AI is analyzing..." if language == "English" else "AI 正在深度分析..."
    
    with st.spinner(loading_text):
        response = model.generate_content(prompt)
        return response.text

# --- 4. 界面布局 ---

st.title("📈 AI 智能股票研报生成器 / AI Equity Research")
st.caption("Powered by Gemini 2.5 & Yahoo Finance")

with st.sidebar:
    st.header("⚙️ Settings / 设置")
    
    # === 新增：语言选择 ===
    report_language = st.radio(
        "选择报告语言 / Report Language",
        ["简体中文", "English"],
        index=0
    )
    
    st.divider()
    
    model_version = st.selectbox(
        "Model / 模型", 
        ["gemini-2.5-flash", "gemini-2.5-flash-lite"],
        index=1
    )
    
    st.info("Pro 模型分析更深入 / Pro model provides deeper insights")

# 主输入区
col1, col2 = st.columns([3, 1])
with col1:
    ticker_input = st.text_input("Stock Ticker / 股票代码", value="", placeholder="e.g. NVDA, AAPL").upper()
with col2:
    st.write("") 
    st.write("")
    # 根据语言改变按钮文字
    btn_label = "Generate Report" if report_language == "English" else "生成研报"
    generate_btn = st.button(f"🚀 {btn_label}", type="primary", use_container_width=True)

# 执行逻辑
if generate_btn:
    if not ticker_input:
        st.warning("Please enter a ticker / 请输入代码")
    else:
        # 1. 获取数据
        status_msg = st.empty()
        fetch_msg = f"Fetching data for {ticker_input}..." if report_language == "English" else f"正在拉取 {ticker_input} 数据..."
        status_msg.info(fetch_msg)
        
        hard_data = get_financial_data(ticker_input)
        
        # 2. 生成报告
        try:
            # 传入用户选择的 report_language
            report_content = generate_report(ticker_input, hard_data, model_version, report_language)
            status_msg.empty() 
            
            # 3. 显示结果
            st.markdown(report_content)
            
            # 4. 下载按钮 (动态文件名)
            st.markdown("---")
            lang_suffix = "EN" if report_language == "English" else "CN"
            file_name = f"{ticker_input}_Report_{lang_suffix}_{datetime.now().strftime('%Y%m%d')}.md"
            
            dl_label = "📥 Download Report" if report_language == "English" else "📥 下载 Markdown 报告"
            
            st.download_button(
                label=dl_label,
                data=report_content,
                file_name=file_name,
                mime="text/markdown"
            )
            
        except Exception as e:
            status_msg.error(f"Error: {e}")
