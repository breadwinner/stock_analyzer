import streamlit as st
import google.generativeai as genai
import yfinance as yf
import os
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="AI 深度股票研报生成器",
    page_icon="📈",
    layout="wide"
)

# --- 2. 安全与配置 (环境变量读取) ---
# 尝试从系统环境变量获取 Key
API_KEY = os.getenv("GOOGLE_API_KEY")

# 如果环境变量不存在，尝试从 Streamlit Secrets 获取 (用于云端部署)
if not API_KEY:
    try:
        API_KEY = st.secrets["GOOGLE_API_KEY"]
    except:
        pass

# 如果都找不到，报错并停止运行
if not API_KEY:
    st.error("❌ 未找到 API Key配置！")
    st.markdown("""
    **请通过以下两种方式之一提供 API Key:**
    1. **环境变量**: 在终端运行 `export GOOGLE_API_KEY='你的key'` (Mac/Linux) 或 `set GOOGLE_API_KEY='你的key'` (Windows)
    2. **Streamlit Secrets**: 创建 `.streamlit/secrets.toml` 文件并写入 `GOOGLE_API_KEY = "你的key"`
    """)
    st.stop()

# 配置 Gemini
genai.configure(api_key=API_KEY)

# --- 3. 核心功能函数 ---

def get_financial_data(ticker_symbol):
    """
    使用 yfinance 获取基础财务数据作为 Context，
    防止 LLM 在关键数字上产生幻觉。
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # 尝试获取 info，如果失败通常是因为网络或 ticker 错误
        info = stock.info
        
        # 获取最新的收盘价（以防 info 中的价格有延迟）
        history = stock.history(period="1d")
        if not history.empty:
            current_price = round(history['Close'].iloc[-1], 2)
        else:
            current_price = info.get('currentPrice', 'N/A')

        # 构建给 AI 参考的数据摘要
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
        return f"Warning: Could not fetch real-time data via yfinance ({str(e)}). Please rely on your internal knowledge."

def generate_report(ticker, financial_data, model_name):
    """调用 Gemini 生成研报"""
    model = genai.GenerativeModel(model_name)
    
    # 你的 Prompt 模板
    prompt = f"""
    Role: You are a world-class equity research analyst.
    Task: Conduct a comprehensive, in-depth analysis of the company: {ticker}.
    
    **CRITICAL INSTRUCTION**: The final output MUST be a professional research report in **CHINESE (简体中文)**.
    
    Context Data (Real-time):
    {financial_data}
    
    Analysis Framework:
    1. **Fundamental Business**: Deconstruct business model, moat, and financial health (Revenue, Margins, Cash Flow).
    2. **Valuation & Ratios**: Analyze P/E, PEG, ROE relative to historicals and peers using the provided data.
    3. **Technical Analysis**: Describe current trend structure (Support/Resistance) based on price action logic.
    4. **Industry & Competition**: Macro trends, TAM, and competitive landscape.
    5. **Qualitative**: Management, Risks, and Catalysts.
    6. **Conclusion**: Buy/Hold/Sell rating, Target Price logic, and Risk Mitigation.
    
    Format the response with Markdown headers, bullet points for readability, and clear sections.
    Current Date: {datetime.now().strftime("%Y-%m-%d")}
    """
    
    with st.spinner(f'🤖 AI 正在分析 {ticker} 的基本面与技术面...'):
        response = model.generate_content(prompt)
        return response.text

# --- 4. 界面布局 ---

st.title("📈 AI 智能股票研报生成器 (Pro)")
st.caption("Powered by Gemini 2.5 & Yahoo Finance")

with st.sidebar:
    st.header("⚙️ 参数设置")
    # API Key 状态指示灯
    st.success("✅ API Key 已加载")
    
    model_version = st.selectbox(
        "选择模型", 
        ["gemini-2.5-flash"],
        index=1, # 默认选 Pro
        help="Flash 速度更快，Pro 分析更深入"
    )
    
    st.markdown("---")
    st.info("提示：输入美股代码效果最佳 (如 NVDA, TSLA, BABA)")

# 主输入区
col1, col2 = st.columns([3, 1])
with col1:
    ticker_input = st.text_input("请输入股票代码", value="", placeholder="例如: AAPL").upper()
with col2:
    st.write("") # 占位用于对齐
    st.write("")
    generate_btn = st.button("🚀 生成研报", type="primary", use_container_width=True)

# 执行逻辑
if generate_btn:
    if not ticker_input:
        st.warning("请输入有效的股票代码")
    else:
        # 1. 获取数据
        status_placeholder = st.empty()
        status_placeholder.info(f"正在拉取 {ticker_input} 实时财务数据...")
        
        hard_data = get_financial_data(ticker_input)
        
        # 2. 生成报告
        try:
            status_placeholder.info("正在进行 AI 深度推理 (这可能需要 30-60 秒)...")
            report_content = generate_report(ticker_input, hard_data, model_version)
            status_placeholder.empty() # 清除状态提示
            
            # 3. 显示结果
            st.markdown(report_content)
            
            # 4. 下载按钮
            st.markdown("---")
            file_name = f"{ticker_input}_研报_{datetime.now().strftime('%Y%m%d')}.md"
            st.download_button(
                label="📥 下载 Markdown 报告",
                data=report_content,
                file_name=file_name,
                mime="text/markdown"
            )
            
        except Exception as e:
            status_placeholder.error(f"生成失败: {e}")
