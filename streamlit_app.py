import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="LC PRO 96 智能诊断专家", page_icon="🔬", layout="wide")

# --- 专家知识图谱 ---
SYMPTOM_MAP = {
    "运行中途停止/崩溃": ["ErrorCode", "Emergency", "Abort", "Failure"],
    "荧光信号异常/过低": ["LEDIntensity", "Gain", "ExposureTime", "CaptureImage"],
    "温度波动/报错": ["UTEC", "TempSensor", "Heatsink", "Peltier"],
    "加热盖打不开/报错": ["PressCover", "Motor", "Sync_Err", "Lid"]
}

KNOWLEDGE_BASE = {
    "0x0189": {"title": "检测单元同步失效", "cause": "相机未给LED控制板发送触发信号", "suggest": "检查内部连接线或更换相机模块"},
    "0x0229": {"title": "加热盖压紧错误", "cause": "压紧电机步数溢出", "suggest": "检查耗材高度或润滑丝杆"},
    "0x0201": {"title": "板卡通讯中断", "cause": "主控板与模块连接丢失", "suggest": "检查直流供电电压是否稳定"},
}

st.title("🔬 LC PRO 96 智能故障根因分析系统")

# --- 侧边栏：故障描述输入 ---
st.sidebar.header("🛠️ 故障现象描述")
user_symptom = st.sidebar.selectbox(
    "请选择或输入具体问题：",
    ["请选择...", "运行中途停止/崩溃", "荧光信号异常/过低", "温度波动/报错", "加热盖打不开/报错", "其他 (搜索关键词)"]
)
custom_keyword = st.sidebar.text_input("或输入自定义搜索关键词（如：Motor）")

uploaded_file = st.file_uploader("📤 上传 system-logs.csv 文件", type=["csv", "log"])

if uploaded_file:
    df = None
    content = uploaded_file.read()
    # 自动识别编码
    for enc in ['utf-8', 'gbk', 'gb18030']:
        try:
            df = pd.read_csv(io.BytesIO(content), sep='\t', header=None, encoding=enc, encoding_errors='replace')
            break
        except: continue

    if df is not None:
        # 数据列标准化
        msg_col = df.shape[1] - 1
        df[msg_col] = df[msg_col].astype(str)
        
        # --- 智能分析逻辑 ---
        st.subheader("📋 诊断报告")
        
        target_keywords = []
        if user_symptom != "请选择...":
            target_keywords = SYMPTOM_MAP.get(user_symptom, [])
        if custom_keyword:
            target_keywords.append(custom_keyword)

        if target_keywords:
            # 在日志中根据现象关键词进行筛选
            pattern = '|'.join(target_keywords)
            matched_df = df[df[msg_col].str.contains(pattern, case=False, na=False)]
            
            if not matched_df.empty:
                st.write(f"🔍 根据您的描述，在日志中找到 **{len(matched_df)}** 条相关线索：")
                
                # 提取最高频出现的错误码
                all_text = " ".join(matched_df[msg_col].tolist())
                found_codes = re.findall(r'0x[0-9a-fA-F]+', all_text)
                
                if found_codes:
                    most_common_code = max(set(found_codes), key=found_codes.count)
                    st.success(f"### 🚩 疑似核心根因：{most_common_code}")
                    
                    if most_common_code in KNOWLEDGE_BASE:
                        kb = KNOWLEDGE_BASE[most_common_code]
                        c1, c2 = st.columns(2)
                        c1.metric("故障模块", kb['title'])
                        c2.info(f"**可能原因：** {kb['cause']}\n\n**处理建议：** {kb['suggest']}")
                
                # 时间轴展示
                st.write("---")
                st.write("🕒 **故障前后的关键事件链：**")
                display_df = matched_df.tail(10)[[1, 4, msg_col]] # 取最后10条关键记录
                display_df.columns = ['时间', '模块', '详细日志']
                st.table(display_df)
            else:
                st.warning("未在日志中找到与该现象直接相关的关键词。")
        else:
            st.info("请在左侧选择或输入故障现象，系统将开始根因回溯。")

        # 原始错误统计（保留之前的功能）
        with st.sidebar.expander("📊 原始统计"):
            hw_errors = df[df[msg_col].str.contains('ErrorCode|Hardware failure', case=False)].shape[0]
            st.write(f"硬件错误总数: {hw_errors}")
