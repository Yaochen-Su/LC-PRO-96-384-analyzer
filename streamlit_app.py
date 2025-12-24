import streamlit as st
import pandas as pd
import re
import io

# 1. 页面配置
st.set_page_config(page_title="LC PRO 96 智能故障专家", page_icon="🧪", layout="wide")

# --- 2. 增强型专家知识库 (包含多维度索引) ---
# 使用核心代码作为 Key，同时在内部定义关联的描述和 ID
FAULT_LIBRARY = {
    "0x0229": {
        "name": "加热盖压紧错误 (Pressing Error)",
        "alert_id": "9429.1.0.0.0.0.16",
        "symptoms": ["pressing error", "压盖错误", "盖子打不开"],
        "content": "加热盖电机下压力量未达标。通常发生在反应板密封阶段，电机步数已满但未触及压力平衡点。",
        "logic": "电机指令 -> 步进运动 -> 提前受阻或传感器未响应 -> 触发 0x0229。",
        "causes": {
            "🧪 耗材问题": "使用了非标高板、孔板未放平或封板膜过厚。",
            "⚙️ 机械阻力": "加样单元丝杆润滑脂干涸，导致电机力矩不足。",
            "📡 传感器偏置": "压力传感器(Load Cell)信号漂移，无法准确感应压力。"
        },
        "fix_steps": ["执行空载运行（不放板）测试", "清洁并润滑加热盖机械连杆", "在Service Tool中重新校准压力"]
    },
    "0x0189": {
        "name": "检测系统同步超时 (Detection Sync Timeout)",
        "alert_id": "9429.1.0.0.0.0.22",
        "symptoms": ["unhandled hardware failure", "未处理硬件故障", "荧光采集失败"],
        "content": "对应 Unhandled Failure。相机快门信号与LED灯闪烁不同步。",
        "logic": "相机曝光 -> Sync信号丢失 -> LED板等待超时 -> 触发 0x0189。",
        "causes": {
            "🔌 物理链路": "检测头内部相机同步线（黑色细线）松动或折断。",
            "⚡ 环境干扰": "Peltier大电流工作产生电磁脉冲干扰了同步电平。"
        },
        "fix_steps": ["重新插拔同步线", "排查拖链线束磨损", "执行光学专项自检"]
    }
}

# --- 3. 核心诊断引擎 ---
def perform_diagnosis(df, msg_col, user_input):
    st.markdown(f"### 🔍 诊断报告回溯: “{user_input}”")
    
    # 构建智能搜索列表
    search_keywords = [user_input]
    target_code = None
    
    # 预匹配：如果输入的是文字，先找出它可能对应的 0x 代码
    for code, info in FAULT_LIBRARY.items():
        if any(sym in user_input.lower() for sym in info['symptoms']) or info['alert_id'] in user_input:
            target_code = code
            search_keywords.extend([code, info['alert_id']])
            break
    
    # 在日志中进行模糊匹配搜索
    pattern = '|'.join(search_keywords)
    # 重点：忽略大小写，且将包含 JSON 结构的行也纳入搜索
    matches = df[df[msg_col].str.contains(pattern, case=False, na=False)]
    
    if matches.empty:
        st.warning("⚠️ 日志中未找到匹配项。请确保上传了正确的日志文件（如 system-logs.csv）。")
        return

    # 获取最后一次出现的匹配索引
    latest_event = matches.iloc[-1]
    raw_msg = str(latest_event[msg_col])
    idx = latest_event.name

    # 根因锁定逻辑
    final_info = None
    
    # 路径 A：如果直接匹配到了专家库中的代码
    for code in FAULT_LIBRARY.keys():
        if code in raw_msg or FAULT_LIBRARY[code]['alert_id'] in raw_msg:
            final_info = FAULT_LIBRARY[code]
            break
            
    # 路径 B：如果只匹配到描述，则向前回溯 100 行寻找最近的 0x 代码
    if final_info is None:
        context = df.iloc[max(0, idx-100):idx+10]
        for code in FAULT_LIBRARY.keys():
            if not context[context[msg_col].str.contains(code, na=False)].empty:
                final_info = FAULT_LIBRARY[code]
                st.caption(f"💡 自动关联底层硬件错误代码: `{code}`")
                break

    # 渲染界面
    if final_info:
        st.error(f"### 诊断结论：{final_info['name']}")
        
        tab1, tab2, tab3 = st.tabs(["📝 详细解析", "🕵️ 原因分析", "🛠️ 维修建议"])
        with tab1:
            st.write(f"**警报 ID:** `{final_info['alert_id']}`")
            st.write(f"**内容定义:** {final_info['content']}")
            st.info(f"**发生逻辑:** {final_info['logic']}")
        with tab2:
            for cat, detail in final_info['causes'].items():
                st.markdown(f"**{cat}**：{detail}")
        with tab3:
            st.success("请按以下步骤操作：")
            for i, step in enumerate(final_info['fix_steps']):
                st.write(f"{i+1}. {step}")
        
        st.text_area("原始日志条目预览", raw_msg, height=100)
    else:
        st.warning("检测到相关日志，但未能匹配到专家库中的具体解析。")
        st.code(raw_msg)

# --- 4. 主界面渲染 ---
def main():
    st.sidebar.title("🛠️ LC PRO 96 诊断面板")
    uploaded_file = st.sidebar.file_uploader("1. 上传日志文件", type=["csv", "log"])
    user_query = st.sidebar.text_input("2. 输入症状或代码 (如: pressing error)", "pressing error")

    if uploaded_file:
        content = uploaded_file.read()
        # 兼容性读取
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
