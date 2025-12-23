import streamlit as st
import pandas as pd
import re
import io

# 页面配置
st.set_page_config(page_title="罗氏 LC PRO 96 智能诊断", page_icon="🧬", layout="wide")

# 自定义样式
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧬 Roche LightCycler PRO 96 智能日志分析系统")
st.info("本工具用于快速定位 LC PRO 96 运行样本时的 'Unhandled hardware failure' 等硬件故障。")

# 核心专家库（基于您提供的日志样本）
KNOWLEDGE_BASE = {
    "0x0189": {
        "title": "检测单元同步故障 (Optical Sync)",
        "desc": "LED控制板未收到相机的同步信号。通常是内部触发线松动、电磁干扰或相机/LED板卡损坏。",
        "action": "1. 检查相机与LEDCntrl板连接线；2. 检查屏蔽接地；3. 运行光学专项自检。"
    },
    "0x0229": {
        "title": "加热盖压紧错误 (Pressing Error)",
        "desc": "加热盖电机在下压时步数超限，无法到达预设压力或位置。",
        "action": "1. 检查PCR耗材高度是否标准；2. 检查压紧丝杆润滑；3. 校准盖压力。"
    },
    "553": {
        "title": "硬件紧急报告 (Emergency)",
        "desc": "底层模块触发了紧急停止信号。",
        "action": "请结合具体的 ErrorCode 进行排查。"
    }
}

uploaded_file = st.file_uploader("📤 请上传导出的 system-logs.csv 文件", type=["csv", "log"])

if uploaded_file:
    # 自动识别编码并读取
    df = None
    content = uploaded_file.read()
    for enc in ['utf-8', 'gbk', 'utf-16', 'gb18030']:
        try:
            df = pd.read_csv(io.BytesIO(content), sep='\t', header=None, encoding=enc, encoding_errors='replace')
            st.caption(f"✅ 文件解析成功 (编码: {enc})")
            break
        except:
            continue

    if df is not None:
        # 处理列名
        msg_col_idx = df.shape[1] - 1
        df[msg_col_idx] = df[msg_col_idx].astype(str)
        
        # 提取关键错误
        error_df = df[df[msg_col_idx].str.contains('ErrorCode|Hardware emergency|unhandled hardware failure|Alert', case=False)]

        if not error_df.empty:
            st.error(f"🚨 在日志中检测到 {len(error_df)} 处异常记录")
            
            for idx, row in error_df.iterrows():
                msg = row[msg_col_idx]
                # 匹配代码
                code_match = re.search(r'ErrorCode:\s*(0x[0-9a-fA-F]+)|ErrorNo\s*(\d+)|Scenario\":\"(.*?)\"', msg)
                
                # 尝试获取识别码
                code = "Unknown"
                if code_match:
                    code = code_match.group(1) or code_match.group(2) or code_match.group(3)

                with st.expander(f"时间点: {row[1] if len(row)>1 else '未知'} | 错误信息摘要", expanded=True):
                    c1, c2 = st.columns([1, 2])
                    
                    with c1:
                        st.warning(f"标识码: {code}")
                        # 查找 PCR 阶段
                        context = df.iloc[max(0, idx-150):idx]
                        proc = context[context[msg_col_idx].str.contains('ProcTypeId_', na=False)].tail(1)
                        if not proc.empty:
                            stage = re.search(r'ProcTypeId_(\w+)', proc[msg_col_idx].values[0])
                            st.write(f"📍 **发生阶段:** {stage.group(1) if stage else '未知'}")
                    
                    with c2:
                        know = KNOWLEDGE_BASE.get(code, {"title": "未定义的硬件错误", "desc": "请查看下方原始日志，建议联系罗氏后台。", "action": "查阅维修手册。"})
                        st.markdown(f"### {know['title']}")
                        st.write(f"**分析:** {know['desc']}")
                        st.success(f"**建议:** {know['action']}")
                    
                    st.text("原始日志:")
                    st.code(msg)
        else:
            st.balloons()
            st.success("🎉 该日志中未发现明显硬件故障，请检查软件设置或人为操作。")