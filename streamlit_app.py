import streamlit as st
import pandas as pd
import re
import io

# 页面基础配置
st.set_page_config(page_title="LC PRO 96 智能故障专家", page_icon="🧪", layout="wide")

# --- 1. 深度细化的故障因果百科库 ---
# 基于您提供的 system-logs.csv 和 system-logs-1050022.csv 录入
FAULT_ENCYCLOPEDIA = {
    "0x0229": {
        "name": "加热盖步数同步错误 (Cover Motor Sync Error)",
        "meaning": "加热盖电机在移动或压紧过程中，在被中断的情况下达到了最大允许步数。系统判定电机无法到达目标位置。",
        "logic": "电机指令发送 -> 运动受阻/传感器未反馈 -> 步数累计达上限 -> 报错中断。",
        "causes": {
            "🔩 机械阻力": "加样单元导轨或加热盖丝杆因异物或缺乏润滑导致运行不畅。",
            "🏷️ 耗材干扰": "使用了高度不兼容的PCR板，导致电机在未到达预设位置前就被强行阻挡。",
            "📡 传感器异常": "限位开关或压力传感器反馈迟钝，导致电机持续空转直到步数溢出。"
        },
        "fix_steps": ["检查并润滑加热盖机械连杆", "确认使用的PCR板类型符合Roche标准", "运行加样单元自检(Self-Test)"]
    },
    "0x0189": {
        "name": "光学系统同步超时 (Detection Sync Timeout)",
        "meaning": "LED控制板在等待来自相机的拍摄同步脉冲信号时发生超时。",
        "logic": "相机曝光开始 -> 发送同步电信号 -> LED板接收并闪烁。如果信号线断裂或相机输出失效，闭环就会断开。",
        "causes": {
            "🔌 链路故障": "相机与LED控制板之间的同步线束(Sync Cable)松动或内部断裂。",
            "⚡ 信号干扰": "Peltier大电流工作时产生的电磁脉冲干扰了敏感的TTL同步电平。",
            "📸 硬件损坏": "相机模组的触发输出引脚电路损坏。"
        },
        "fix_steps": ["重新插拔检测单元内部的所有同步信号排线", "检查线束是否在Y轴运动中受到挤压", "在诊断模式下执行光学连拍测试"]
    },
    "0x0301": {
        "name": "主电源电压跌落 (Power Bus Sag)",
        "meaning": "主控板感测到24V/48V直流总线电压在重载(如升温)瞬间低于安全阈值。",
        "logic": "升温指令 -> 电流激增 -> 电源老化无法稳压 -> 系统重启或报错。",
        "causes": {
            "🔋 电源老化": "电源模组输出能力下降。",
            "🌡️ 散热过热": "电源风扇故障导致过温保护。"
        },
        "fix_steps": ["测量加热瞬间的电压跌落情况", "更换电源模块"]
    }
}

# --- 2. 核心分析函数 ---
def extract_context_info(df, idx, msg_col):
    """提取故障前后的参数快照"""
    start = max(0, idx - 100)
    context = df.iloc[start:idx]
    # 提取最后提到的 Procedure
    proc_search = context[context[msg_col].str.contains('ProcTypeId_', na=False)]
    last_proc = "未知任务"
    if not proc_search.empty:
        match = re.search(r'ProcTypeId_(\w+)', proc_search.iloc[-1][msg_col])
        if match: last_proc = match.group(1)
    return last_proc

def run_diagnostic(df, msg_col, user_input):
    """核心诊断引擎"""
    st.markdown(f"### 🚩 针对 “{user_input}” 的根因分析报告")
    
    # 建立输入与错误码的模糊映射
    keyword_map = {
        "压盖": "0x0229", "盖子": "0x0229", "加热盖": "0x0229",
        "荧光": "0x0189", "采集": "0x0189", "光学": "0x0189", "检测": "0x0189",
        "电源": "0x0301", "电压": "0x0301", "停机": "ErrorCode"
    }
    
    # 在日志中匹配
    found_rows = df[df[msg_col].str.contains(user_input, case=False, na=False) | 
                    df[msg_col].str.contains('|'.join([v for k,v in keyword_map.items() if k in user_input]), na=False)]
    
    if found_rows.empty:
        st.warning("⚠️ 日志中未匹配到直接相关的故障记录，建议尝试输入具体的错误代码（如 0x0189）。")
        return

    # 分析最后一次发生的故障
    last_event = found_rows.iloc[-1]
    raw_msg = str(last_event[msg_col])
    idx = last_event.name
    
    # 提取错误码
    code_match = re.search(r'0x[0-9a-fA-F]+', raw_msg)
    code = code_match.group(0) if code_match else "Unknown"
    
    # UI 展示
    if code in FAULT_ENCYCLOPEDIA:
        info = FAULT_ENCYCLOPEDIA[code]
        st.error(f"**诊断结论：{info['name']}**")
        
        tab1, tab2, tab3 = st.tabs(["💡 故障解析", "🧐 因果推导", "🛠️ 维修方案"])
        with tab1:
            st.write(f"**主要内容：** {info['meaning']}")
            st.caption(f"**底层逻辑闭环：** {info['logic']}")
            st.write(f"**发生时仪器任务：** `{extract_context_info(df, idx, msg_col)}`")
        with tab2:
            c1, c2, c3 = st.columns(3)
            causes = list(info['causes'].items())
            c1.info(f"**原因 1**\n\n{causes[0][0]}: {causes[0][1]}")
            c2.info(f"**原因 2**\n\n{causes[1][0]}: {causes[1][1]}")
            c3.info(f"**原因 3**\n\n{causes[2][0]}: {causes[2][1]}")
        with tab3:
            st.success("**建议操作步骤：**")
            for i, step in enumerate(info['fix_steps']):
                st.write(f"{i+1}. {step}")
    else:
        st.warning(f"检测到错误代码 `{code}`，但专家库暂未包含该代码的因果逻辑。")
        st.text("原始日志片段：")
        st.code(raw_msg)

# --- 3. Streamlit 主界面 ---
def main():
    st.sidebar.title("🛠️ LC PRO 维修控制台")
    uploaded_file = st.sidebar.file_uploader("1. 上传故障日志", type=["csv", "log"])
    
    # 故障描述对话框
    user_query = st.sidebar.text_input("2. 描述您遇到的现象 (如: 荧光分析失败, 压盖报错)", "")
    
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
            if user_query:
                run_diagnostic(df, msg_col, user_query)
            else:
                st.info("👈 请在左侧输入框描述故障现象，我将为您分析根因。")
        else:
            st.error("无法读取文件，请确保它是罗氏导出的标准 .csv 格式。")

if __name__ == "__main__":
    main()
