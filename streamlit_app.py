import streamlit as st
import pandas as pd
import re
import io

# 1. 页面配置 - 必须放在脚本第一行
st.set_page_config(page_title="LC PRO 96 故障根因分析专家", page_icon="🔬", layout="wide")

# 2. 深度百科库 - 针对 system-logs-1050022.csv 进行了专项细化
FAULT_DETAILS = {
    "Unhandled hardware failure": {
        "name": "未处理的硬件故障 (Unhandled Hardware Failure)",
        "content": "根据日志 system-logs-1050022.csv 分析，此报警是由于检测单元（Module 30）在执行荧光采集任务时，发生了致命的同步丢失（Sync Lost）。",
        "logic_gap": "相机曝光动作 (Module 30) -> 同步信号电缆 -> LED控制板接收。由于控制板在规定时间内未收到信号，导致整个检测链条断裂。",
        "causes": {
            "🔴 核心病因": "相机同步触发信号丢失（ErrorCode: 0x0189）。这是导致 Unhandled 报警的直接导火索。",
            "🔌 线束故障": "检测头在扫描移动中，内部的细微同步线可能由于往复弯折出现瞬时开路或接头松动。",
            "⚡ 环境干扰": "热循环模块升降温时产生的高频噪声干扰了触发信号的逻辑电平。",
            "📷 硬件损坏": "相机的触发输出口或LED控制板的接收光耦发生故障。"
        },
        "fix_steps": [
            "**优先检查**：打开检测头盖板，重新插拔并加固相机与LED控制板之间的同步连接线。",
            "**路径排查**：检查检测头运动拖链内的线束是否有挤压、磨损或由于扎带过紧导致的损坏。",
            "**对比测试**：尝试运行不带荧光检测的纯温度循环程序。如果正常，则问题锁定在光学同步链路。",
            "**软件校准**：进入 Service Tool，在诊断界面观察实时捕捉的相机触发脉冲计数。"
        ]
    },
    "0x0189": {
        "name": "光学系统同步超时 (Detection Sync Timeout)",
        "content": "这是 Unhandled 错误的底层代码。说明相机和灯没对上时间。",
        "logic_gap": "检测单元同步链条断开。",
        "causes": { "主因": "同步线缆损坏或接口氧化。", "次因": "电磁干扰导致误触发。" },
        "fix_steps": ["更换同步信号线", "清洁接口针脚", "检查屏蔽层接地"]
    },
    "0x0229": {
        "name": "加热盖压紧错误 (Pressing Error)",
        "content": "加热盖电机压紧力未达标，步数耗尽。",
        "logic_gap": "电机位置与压力反馈不匹配。",
        "causes": { "耗材": "非标耗材过高。", "机械": "丝杆干涩或传感器偏移。" },
        "fix_steps": ["使用标准耗材", "润滑丝杆", "校准压力"]
    }
}

# 3. 核心功能函数
def extract_params(msg):
    return re.findall(r'(\w+):\s*([\d\.-x]+)', msg)

def perform_diagnosis(df, msg_col, user_input):
    """根因分析引擎"""
    st.subheader(f"🛠️ 针对 “{user_input}” 的诊断报告")
    
    # 关键词模糊搜索逻辑
    keyword_map = {
        "unhandled": "unhandled hardware failure",
        "未处理": "unhandled hardware failure",
        "故障": "unhandled hardware failure",
        "压盖": "0x0229", "盖子": "0x0229",
        "荧光": "0x0189", "同步": "0x0189"
    }
    
    search_pattern = user_input
    for k, v in keyword_map.items():
        if k in user_input.lower(): search_pattern = v
    
    # 查找匹配行
    matches = df[df[msg_col].str.contains(search_pattern, case=False, na=False)]
    
    if matches.empty:
        st.warning("在日志中未找到匹配项。建议输入具体的错误代码，如 '0x0189'。")
        return

    # 锁定最后一次报错
    latest_event = matches.iloc[-1]
    raw_msg = str(latest_event[msg_col])
    idx = latest_event.name
    
    # 自动向前回溯，寻找隐藏在 Unhandled 后面的 16 进制代码
    real_code = "Unhandled hardware failure"
    hex_match = re.search(r'0x[0-9a-fA-F]+', raw_msg)
    if hex_match:
        real_code = hex_match.group(0)
    else:
        # 如果当前行没代码，向前找 50 行
        context = df.iloc[max(0, idx-50):idx]
        context_error = context[context[msg_col].str.contains('ErrorCode: 0x', na=False)]
        if not context_error.empty:
            real_code = re.search(r'0x[0-9a-fA-F]+', context_error.iloc[-1][msg_col]).group(0)
            st.warning(f"💡 自动追溯发现：此 'Unhandled' 报警根源为底层代码 `{real_code}`")

    # 渲染解析结果
    if real_code in FAULT_DETAILS:
        info = FAULT_DETAILS[real_code]
        st.error(f"### 诊断结论：{info['name']}")
        
        tab1, tab2, tab3 = st.tabs(["📑 故障解析", "🧐 因果推导", "🛠️ 解决方案"])
        with tab1:
            st.write(f"**内容定义：** {info['content']}")
            st.info(f"**底层逻辑闭环：** {info['logic_gap']}")
            st.text("原始日志快照：")
            st.code(raw_msg)
        with tab2:
            st.write("**可能的根因分析：**")
            for cat, detail in info['causes'].items():
                st.markdown(f"- **{cat}**：{detail}")
        with tab3:
            st.success("**建议排查步骤：**")
            for i, step in enumerate(info['fix_steps']):
                st.write(f"{i+1}. {step}")
    else:
        st.warning(f"检测到代码 `{real_code}`，但专家库暂未收录。")
        st.code(raw_msg)

# 4. 主界面逻辑 (确保 UI 元素总是被渲染)
def main():
    st.title("🔬 Roche LC PRO 96 智能维修助理")
    st.write("---")
    
    # 侧边栏保持一直显示，避免空白
    st.sidebar.header("⚙️ 操作面板")
    uploaded_file = st.sidebar.file_uploader("1. 上传 system-logs.csv", type=["csv", "log"])
    user_query = st.sidebar.text_input("2. 描述故障现象 (如: Unhandled, 压盖)", "")

    if uploaded_file:
        df = None
        content = uploaded_file.read()
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
                st.info("👈 文件已就绪。请在左侧输入故障描述（例如输入 'Unhandled'）开始深度根因分析。")
        else:
            st.error("❌ 文件读取失败，请确保格式正确。")
    else:
        # 初始引导界面
        st.markdown("""
        ### 使用说明：
        1. 从 LC PRO 96 导出 `system-logs.csv` 文件。
        2. 将其拖入左侧的上传框。
        3. 在左侧输入框描述遇到的问题，系统将执行**回溯分析**。
        
        **示例场景：**
        - 输入 **'Unhandled'**：系统将基于 `system-logs-1050022.csv` 的逻辑，为您挖掘被掩盖的 `0x0189` 同步错误。
        - 输入 **'压盖'**：系统将分析 `0x0229` 的压力传感器与电机同步问题。
        """)

if __name__ == "__main__":
    main()
