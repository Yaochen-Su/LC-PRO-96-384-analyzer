import streamlit as st
import pandas as pd
import re
import io

# 1. 页面基础配置
st.set_page_config(page_title="LC PRO 96 智能故障专家", page_icon="🧪", layout="wide")

# --- 2. 映射表：通用描述/警报ID -> 核心代码 ---
SYMPTOM_MAP = {
    "pressing error": "0x0229",
    "压盖错误": "0x0229",
    "9429.1.0.0.0.0.16": "0x0229",
    "unhandled hardware failure": "0x0189",
    "未处理硬件故障": "0x0189",
    "9429.1.0.0.0.0.22": "0x0189",
    "optical sync": "0x0189",
    "荧光同步失败": "0x0189"
}

# --- 3. 深度解析百科库 ---
FAULT_ENCYCLOPEDIA = {
    "0x0229": {
        "name": "加热盖压紧错误 (Pressing Error)",
        "alert_id": "9429.1.0.0.0.0.16",
        "content": "加热盖电机在压紧反应板时步数超限。系统认为盖子未能达到预定的密封位置或压力。",
        "logic": "电机指令 -> 下压动作 -> 物理受阻/传感器未触发 -> 步数溢出 -> 报 0x0229 并触发 Alert 16。",
        "causes": {
            "🧪 耗材问题": "使用了非标高板或封板膜过厚，导致电机提前受阻。",
            "⚙️ 机械问题": "压紧丝杆润滑不足，运行阻力过大。",
            "📡 反馈问题": "压力传感器(Load Cell)信号漂移或接线松动。"
        },
        "fix_steps": ["空载运行测试", "清洁并润滑丝杆", "重新校准压力传感器"]
    },
    "0x0189": {
        "name": "检测系统同步超时 (Detection Sync Timeout)",
        "alert_id": "9429.1.0.0.0.0.22",
        "content": "对应 'Unhandled hardware failure'。LED控制板没等到相机的拍摄快门信号，导致荧光采集链路断裂。",
        "logic": "相机曝光 -> 同步信号丢失 -> LED板等待超时 -> 报 0x0189 并触发 Alert 22。",
        "causes": {
            "🔌 物理链路": "相机与控制板间的同步线（细黑线）松动或断裂。",
            "⚡ 电磁干扰": "Peltier 工作产生的噪声干扰了触发电平。"
        },
        "fix_steps": ["重新插拔同步线", "检查线束拖链有无磨损", "执行光学专项自检"]
    }
}

# --- 4. 核心逻辑函数 ---
def perform_diagnosis(df, msg_col, user_input):
    st.markdown(f"### 🔍 针对 “{user_input}” 的根因回溯报告")
    
    # 自动转换通用描述/Alert ID 为 核心 Error Code
    normalized_input = user_input.lower().strip()
    target_code = SYMPTOM_MAP.get(normalized_input, user_input)
    
    # 在日志中查找相关条目
    search_pattern = f"{target_code}|{normalized_input}"
    matches = df[df[msg_col].str.contains(search_pattern, case=False, na=False)]
    
    if matches.empty:
        st.warning("⚠️ 日志中未找到匹配项。提示：请尝试输入 'pressing error' 或 '0x0229'。")
        return

    # 锁定最后一条错误，提取上下文
    latest_event = matches.iloc[-1]
    raw_msg = str(latest_event[msg_col])
    idx = latest_event.name
    
    # 确定最终用于百科查询的代码
    final_code = "Unknown"
    for code in FAULT_ENCYCLOPEDIA.keys():
        if code in raw_msg or FAULT_ENCYCLOPEDIA[code]["alert_id"] in raw_msg:
            final_code = code
            break
    
    # 如果当前行没找到，回溯 50 行找代码
    if final_code == "Unknown":
        context = df.iloc[max(0, idx-50):idx]
        for code in FAULT_ENCYCLOPEDIA.keys():
            if not context[context[msg_col].str.contains(code, na=False)].empty:
                final_code = code
                st.caption(f"💡 自动关联底层代码: `{final_code}`")
                break

    # 渲染结果
    if final_code in FAULT_ENCYCLOPEDIA:
        info = FAULT_ENCYCLOPEDIA[final_code]
        st.error(f"### 诊断结论：{info['name']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**关联警报 ID:** `{info['alert_id']}`")
            st.write(f"**内容定义:** {info['content']}")
            st.info(f"**因果逻辑:** {info['logic']}")
        with col2:
            st.write("**核心因果分析:**")
            for cat, detail in info['causes'].items():
                st.write(f"- **{cat}**: {detail}")
        
        st.success("**🛠️ 推荐维修步骤:**\n\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(info['fix_steps'])]))
        st.text("原始日志记录:")
        st.code(raw_msg)
    else:
        st.warning(f"未能匹配到专家解析。原始信息：{raw_msg}")

# --- 5. 主界面逻辑 ---
def main():
    st.title("🔬 LC PRO 96 故障智能翻译助手")
    st.sidebar.header("⚙️ 诊断面板")
    uploaded_file = st.sidebar.file_uploader("1. 上传日志", type=["csv", "log"])
    user_query = st.sidebar.text_input("2. 故障描述/警报ID/错误代码", placeholder="如: pressing error")

    if uploaded_file:
        content = uploaded_file.read()
        df = None
        for enc in ['utf-8', 'gbk', 'utf-16']:
            try:
                df = pd.read_csv(io.BytesIO(content), sep='\t', header=None, encoding=enc, encoding_errors='replace')
                break
            except: continue
        
        if df is not None:
            msg_col = df.shape[1] - 1
            df[msg_col] = df[msg_col].astype(str)
            if user_query:
                perform_diagnosis(df, msg_col, user_query)
            else:
                st.info("👈 请在左侧输入故障现象，例如 'pressing error' 或 '9429.1.0.0.0.0.16'")
    else:
        st.markdown("""
        ### 📖 使用提示：
        您可以输入以下任意内容进行分析：
        - **通用描述**：`pressing error`、`unhandled failure`
        - **警报 ID**：`9429.1.0.0.0.0.16`、`9429.1.0.0.0.0.22`
        - **硬件代码**：`0x0229`、`0x0189`
        """)

if __name__ == "__main__":
    main()
