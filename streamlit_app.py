import streamlit as st
import pandas as pd
import re
import io

# --- 1. 高级故障百科全书 (更细致的解析) ---
FAULT_ENCYCLOPEDIA = {
    "0x0189": {
        "component": "光学检测模块 (Detection Unit)",
        "meaning": "同步信号缺失。相机拍摄动作与LED闪烁脉冲未能在毫秒级内匹配。",
        "parameters": ["CDI 0x100202 (LEDCntrl板)", "Check Cabling (线束检查)"],
        "root_causes": {
            "电气层面": "LVDS或触发信号线干扰；相机供电瞬间跌落。",
            "机械层面": "检测头扫描移动到特定位置时排线被拉扯导致瞬时断路。",
            "环境层面": "热循环模块(Peltier)产生的高频电磁噪声干扰。"
        },
        "fix_steps": ["检查并重新插拔同步线 (Sync Cable)", "检查检测头排线有无磨损点", "确认主控板接地良好"]
    },
    "0x0229": {
        "component": "热循环/加载模块 (Cover Pressing)",
        "meaning": "压力反馈异常。压盖电机尝试达到预设密封力时，传感器未在规定步数内反馈信号。",
        "parameters": ["m_InterruptPosition (中断位置)", "ErrorCode 553"],
        "root_causes": {
            "耗材层面": "使用了非标或过高的PCR板，导致电机提前受阻。",
            "机械层面": "丝杆干涸导致阻力过大；限位传感器脏污。",
            "电气层面": "驱动电机力矩不足或电流限制触发。"
        },
        "fix_steps": ["更换标准耗材测试", "清洁并润滑加热盖丝杆", "重新运行压力校准程序"]
    }
}

# --- 2. 核心分析函数 ---
def analyze_error_content(msg, code):
    """解析单条故障的具体内容"""
    st.markdown("### 🔍 深度故障解析报告")
    
    # 自动提取日志中的数值参数
    params = re.findall(r'(\w+):\s*([\d\.-x]+)', msg)
    if params:
        st.write("**📡 捕获到的实时运行参数：**")
        cols = st.columns(len(params) if len(params) < 4 else 4)
        for i, (k, v) in enumerate(params):
            cols[i % 4].metric(k, v)

    # 调取百科知识
    info = FAULT_ENCYCLOPEDIA.get(code)
    if info:
        st.divider()
        st.write(f"**🏗️ 故障部位：** `{info['component']}`")
        st.write(f"**📝 故障定义：** {info['meaning']}")
        
        # 展示可能的原因
        st.write("**🕵️ 可能的故障源分析：**")
        c1, c2, c3 = st.columns(3)
        for i, (cat, detail) in enumerate(info['root_causes'].items()):
            [c1, c2, c3][i].info(f"**{cat}**\n\n{detail}")
        
        # 提供维修指引
        st.warning(f"**🛠️ 建议排查步骤：**\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(info['fix_steps'])]))
    else:
        st.info("💡 该错误码暂未录入专家库。建议检查日志中出现的模块ID(CDI)以确定大致部位。")

# --- Streamlit 界面逻辑 (略，保持之前的上传和搜索功能) ---
# 在显示故障条目的地方调用 analyze_error_content(msg, code) 即可
