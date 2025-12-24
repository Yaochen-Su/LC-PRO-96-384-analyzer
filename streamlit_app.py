import streamlit as st
import pandas as pd
import re
import io

# 1. 页面配置
st.set_page_config(page_title="LC PRO 96 智能故障专家", page_icon="🧪", layout="wide")

# --- 2. 增强型映射表 (确保关键词到代码的桥梁坚固) ---
SYMPTOM_TO_CODE = {
    "pressing error": "0x0229",
    "9429.1.0.0.0.0.16": "0x0229",
    "压盖错误": "0x0229",
    "unhandled hardware failure": "0x0189",
    "9429.1.0.0.0.0.22": "0x0189",
    "未处理硬件故障": "0x0189"
}

# --- 3. 核心专家知识库 ---
FAULT_LIBRARY = {
    "0x0229": {
        "name": "加热盖压紧错误 (Pressing Error)",
        "alert_id": "9429.1.0.0.0.0.16",
        "content": "加热盖电机下压力量未达标。通常发生在反应板密封阶段，电机步数已满但未触及压力平衡点。",
        "logic": "电机指令 -> 步进运动 -> 提前受阻或传感器未响应 -> 触发 0x0229 -> 软件报告 Alert 16。",
        "causes": {
            "🧪 耗材问题": "使用了非标高板、孔板未放平或封板膜过厚。",
            "⚙️ 机械阻力": "加热盖压紧丝杆润滑脂干涸，导致电机力矩不足或运行受阻。",
            "📡 传感器偏置": "压力传感器(Load Cell)信号漂移或接线松动，无法感应下压力。"
        },
        "fix_steps": ["执行空载运行（不放板）测试，确认是否报错", "清洁并润滑加热盖机械连杆丝杆", "在 Service Tool 中重新校准压力传感器"]
    },
    "0x0189": {
        "name": "检测系统同步超时 (Detection Sync Timeout)",
        "alert_id": "9429.1.0.0.0.0.22",
        "content": "对应 Unhandled Failure。相机快门信号与LED灯闪烁不同步，导致荧光采集链路中断。",
        "logic": "相机曝光 -> Sync信号丢失 -> LED板等待超时 -> 触发 0x0189 -> 软件报告 Alert 22。",
        "causes": {
            "🔌 物理链路": "检测头内部相机同步线（黑色细线）松动、接触不良或折断。",
            "⚡ 电磁干扰": "Peltier 大电流工作产生电磁脉冲干扰了同步逻辑电平。"
        },
        "fix_steps": ["重新插拔同步线接口", "排查检测头拖链线束是否有磨损", "执行光学专项自检程序"]
    }
}

# --- 4. 深度诊断引擎 ---
def perform_diagnosis(df, msg_col, user_input):
    st.markdown(f"### 🔍 诊断报告回溯: “{user_input}”")
    
    # A. 规范化输入并查找目标代码
    normalized_input = user_input.lower().strip()
    target_code = SYMPTOM_TO_CODE.get(normalized_input)
    
    # B. 在日志中搜索关键词相关行
    # 同时搜索原始输入和映射后的代码
    search_keywords = [normalized_input]
    if target_code:
        search_keywords.append(target_code)
    
    pattern = '|'.join(search_keywords)
    matches = df[df[msg_col].str.contains(pattern, case=False, na=False)]
    
    if matches.empty:
        st.warning("⚠️ 日志中未找到与该现象相关的记录。请确认上传了正确的 system-logs.csv 文件。")
        return

    # 获取最后一次发生的记录索引
    latest_event = matches.iloc[-1]
    raw_msg = str(latest_event[msg_col])
    idx = latest_event.name

    # C. 锁定专家库条目
    final_info = None
    
    # 路径 1: 如果输入本身就对应一个代码，直接锁定该代码
    if target_code in FAULT_LIBRARY:
        final_info = FAULT_LIBRARY[target_code]
    
    # 路径 2: 如果输入没对应代码，但在当前行或上下文找到了代码
    if final_info is None:
        for code in FAULT_LIBRARY.keys():
            if code in raw_msg:
                final_info = FAULT_LIBRARY[code]
                break
        
        if final_info is None: # 继续向回搜 100 行
            context = df.iloc[max(0, idx-100):idx+5]
            for code in FAULT_LIBRARY.keys():
                if not context[context[msg_col].str.contains(code, na=False)].empty:
                    final_info = FAULT_LIBRARY[code]
                    st.caption(f"💡 自动关联底层硬件错误代码: `{code}`")
                    break

    # D. 渲染解析界面
    if final_info:
        st.error(f"### 诊断结论：{final_info['name']}")
        
        tab1, tab2, tab3 = st.tabs(["📑 故障解析", "🧐 因果推导", "🛠️ 维修建议"])
        with tab1:
            st.write(f"**警报 ID:** `{final_info.get('alert_id', 'N/A')}`")
            st.write(f"**内容定义:** {final_info['content']}")
            st.info(f"**发生逻辑:** {final_info['logic']}")
        with tab2:
            st.write("**核心因果分析:**")
            for cat, detail in final_info['causes'].items():
                st.markdown(f"**{cat}**：{detail}")
        with tab3:
            st.success("**建议排查与维修步骤:**")
            for i, step in enumerate(final_info['fix_steps']):
                st.write(f"{i+1}. {step}")
        
        st.text_area("捕获的原始日志片段", raw_msg, height=100)
    else:
        st.warning("检测到相关日志，但未能匹配到专家库中的具体解析。")
        st.code(raw_msg)

# --- 5. 主界面渲染 ---
def main():
    st.title("🔬 LC PRO 96 智能维修助理 (V3.0)")
    st.sidebar.header("⚙️ 诊断控制台")
    uploaded_file = st.sidebar.file_uploader("1. 上传 system-logs.csv", type=["csv", "log"])
    user_query = st.sidebar.text_input("2. 输入症状或警报 ID (如: pressing error)", "pressing error")

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
            perform_diagnosis(df, msg_col, user_query)
        else:
            st.error("文件读取失败。")
    else:
        st.info("👈 请先在左侧上传日志文件。")

if __name__ == "__main__":
    main()
