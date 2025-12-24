import streamlit as st
import pandas as pd
import re
import io

# --- 专家知识库：针对 system-logs-1050022.csv 深度优化 ---
FAULT_ENCYCLOPEDIA = {
    "Unhandled hardware failure": {
        "name": "未处理的硬件故障 (Unhandled Hardware Failure)",
        "content": "系统遭遇了无法自动恢复的底层硬件异常。根据 system-logs-1050022.csv 日志显示，该错误通常是由检测模块（Detection Unit）的同步超时引发的致命中断。",
        "logic": "相机快门动作与LED闪烁脉冲失步 -> 检测板触发紧急报告(0x0189) -> 流程控制层(Workflow)无法处理此同步中断 -> 抛出全局未处理故障。",
        "causes": {
            "🔍 核心原因 (根据日志)": "相机同步链路故障。LED控制板（LEDCntrl）未收到来自相机的同步触发信号（Sync Signal）。",
            "🔌 物理链路": "相机与控制板之间的同步线束接触不良、针脚松动或在扫描运动中受挤压损坏。",
            "⚡ 电气干扰": "Peltier 升降温时产生的高频干扰（EMI）屏蔽失效，干扰了弱电同步脉冲。",
            "📷 硬件老化": "相机模组的触发输出引脚性能下降，输出电平不足以驱动控制板。"
        },
        "fix_steps": [
            "**查找前置代码**：确认报错前是否出现了 0x0189。如果是，请直接按【检测单元同步故障】方案维修。",
            "**线束检查**：检查检测头内部连接相机与LED控制板的黑色细线（触发线），重新插拔并固定。",
            "**静态测试**：在维修软件中手动触发 LED 闪烁和相机拍摄，观察是否能稳定捕捉 Sync 信号。",
            "**检查屏蔽**：确保检测单元的金属壳体和电缆屏蔽层接地良好，减少运行干扰。"
        ]
    },
    "0x0189": {
        "name": "检测系统同步超时 (Detection Sync Timeout)",
        "content": "这是 system-logs-1050022.csv 中 Unhandled 故障的直接来源。由于相机脉冲信号丢失，LED控制板无法在曝光瞬间点亮荧光诱导光。",
        "logic": "采集流程中断，实验数据无法保证，系统强制停机。",
        "causes": {
            "主因": "同步信号线束故障或相机输出故障。",
            "辅助原因": "主控板供电波动或固件通讯超时。"
        },
        "fix_steps": ["更换同步信号电缆", "检查相机模组状态", "升级相关板卡固件"]
    }
}

# --- 界面展示优化 ---
def run_diagnostic(df, msg_col, user_input):
    st.markdown(f"### 🚩 针对 “{user_input}” 的深度解析 (基于最新日志样本)")
    
    # 查找 Unhandled 报错行
    unhandled_rows = df[df[msg_col].str.contains('unhandled hardware failure', case=False, na=False)]
    
    if not unhandled_rows.empty:
        idx = unhandled_rows.iloc[-1].name
        # 自动回溯寻找真正的 0x 代码
        context_df = df.iloc[max(0, idx-50):idx]
        real_error = context_df[context_df[msg_col].str.contains('ErrorCode: 0x', na=False)]
        
        if not real_error.empty:
            found_code = re.search(r'0x[0-9a-fA-F]+', real_error.iloc[-1][msg_col]).group(0)
            st.warning(f"💡 自动分析发现：本次 'Unhandled' 故障的根源是底层错误代码 `{found_code}`")
            # 优先调用具体的代码解析
            code_to_show = found_code if found_code in FAULT_ENCYCLOPEDIA else "Unhandled hardware failure"
        else:
            code_to_show = "Unhandled hardware failure"
            
        # 渲染解析结果
        info = FAULT_ENCYCLOPEDIA[code_to_show]
        st.error(f"**诊断结论：{info['name']}**")
        
        with st.expander("🧐 因果分析 (Why it happened?)", expanded=True):
            st.write(f"**内容定义：** {info['content']}")
            st.write(f"**底层因果链：** {info['logic']}")
            
        with st.expander("🕵️ 可能的原因分析 (Potential Causes)", expanded=True):
            for cat, detail in info['causes'].items():
                st.write(f"- **{cat}**：{detail}")
                
        with st.expander("🛠️ 推荐解决方案 (Solution)", expanded=True):
            for s in info['fix_steps']:
                st.success(s)
    else:
        st.info("未检测到 'Unhandled' 相关日志条目。")
