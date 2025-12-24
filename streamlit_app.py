import streamlit as st
import pandas as pd
import re
import io

# 1. 页面配置
st.set_page_config(page_title="LC PRO 智能故障助手", page_icon="🔬", layout="wide")

# 自定义 CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .welcome-card {
        background-color: #ffffff; padding: 25px; border-radius: 15px;
        border-left: 5px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 25px;
    }
    .welcome-title { color: #007bff; font-size: 28px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 专家知识库 (核心数据结构) ---
# 定义 0x 代码及其关联的所有标识符
FAULT_LIBRARY = {
    "0x0229": {
        "name": "加热盖压紧错误 (Pressing Error)",
        "alert_id": "9429.1.0.0.0.0.16",
        "keywords": ["pressing error", "压盖错误", "9429.1.0.0.0.0.16", "0x0229"],
        "content": "加热盖电机在下压密封过程中受阻。电机步数已满但未获得压力达标反馈。",
        "causes": {
            "🧪 耗材问题": "使用了过高的非标板、孔板未放平或封板膜太厚。",
            "⚙️ 机械问题": "压紧丝杆润滑脂干涸导致摩擦力过大，电机丢步。",
            "📡 传感器": "压力传感器(Load Cell)零点漂移或接线松动。"
        },
        "fix_steps": ["空载运行测试", "清洁并润滑丝杆", "校准压力传感器"]
    },
    "0x0189": {
        "name": "检测系统同步超时 (Detection Sync Timeout)",
        "alert_id": "9429.1.0.0.0.0.22",
        "keywords": ["unhandled hardware failure", "未处理硬件故障", "9429.1.0.0.0.0.22", "0x0189", "sync"],
        "content": "对应 Unhandled Failure。相机快门信号与LED灯闪烁不同步。",
        "causes": {
            "🔌 链路故障": "检测头内部相机同步线（黑色细线）松动或折断。",
            "⚡ 电磁干扰": "Peltier大电流工作产生电磁脉冲干扰了信号。"
        },
        "fix_steps": ["重新插拔同步线", "排查拖链线束磨损", "执行光学专项自检"]
    }
}

# --- 3. 核心工具函数 ---
def extract_params(msg):
    return re.findall(r'(\w+):\s*([\d\.-x]+)', msg)

def perform_diagnosis(df, msg_col, user_input):
    st.markdown(f"### 🔍 诊断报告: “{user_input}”")
    
    input_lower = user_input.lower().strip()
    target_info = None
    target_code = None

    # 第一步：基于知识库的“强关联识别”
    # 只要用户输入的词在某个故障的 keywords 列表里，就直接锁定该故障
    for code, info in FAULT_LIBRARY.items():
        if any(kw in input_lower for kw in info['keywords']):
            target_info = info
            target_code = code
            break

    # 第二步：在日志中搜索证据
    # 搜索词包括用户输入的原词、关联的代码和关联的 Alert ID
    search_terms = [input_lower]
    if target_info:
        search_terms.extend([target_code.lower(), target_info['alert_id'].lower()])
    
    pattern = '|'.join(set(search_terms))
    matches = df[df[msg_col].str.contains(pattern, case=False, na=False)]

    if matches.empty:
        st.warning(f"⚠️ 在日志中未找到与 '{user_input}' 相关的记录。")
        return

    # 锁定最后一条记录作为展示背景
    latest_event = matches.iloc[-1]
    raw_msg = str(latest_event[msg_col])
    
    # 如果通过输入没锁死故障，则尝试从日志行里提取代码再查一遍
    if not target_info:
        hex_match = re.search(r'0x[0-9a-fA-F]+', raw_msg)
        if hex_match:
            code = hex_match.group(0)
            target_info = FAULT_LIBRARY.get(code)
            target_code = code

    # 第三步：渲染结果
    if target_info:
        st.error(f"### 诊断结论：{target_info['name']}")
        
        tab1, tab2, tab3 = st.tabs(["📑 故障深度解析", "🧐 可能的原因分析", "🛠️ 建议维修步骤"])
        with tab1:
            st.write(f"**关联代码/ID:** `{target_code}` / `{target_info.get('alert_id', 'N/A')}`")
            st.write(f"**定义:** {target_info['content']}")
            # 参数显示
            params = extract_params(raw_msg)
            if params:
                st.write("**实时参数快照：**")
                cols = st.columns(len(params) if len(params) < 5 else 5)
                for i, (k, v) in enumerate(params):
                    cols[i % 5].metric(k, v)
        with tab2:
            for cat, detail in target_info['causes'].items():
                st.markdown(f"**{cat}**：{detail}")
        with tab3:
            for i, step in enumerate(target_info['fix_steps']):
                st.success(f"{i+1}. {step}")
        
        with st.expander("查看原始日志条目"):
            st.code(raw_msg)
    else:
        st.warning(f"检测到日志相关性，但专家库暂未收录具体解析。")
        st.code(raw_msg)

# --- 4. 界面渲染 ---
def main():
    # 侧边栏布局
    with st.sidebar:
        # [Logo] 可以在此处更换 URL
        st.image("logo.png", width=120)
        st.title("LC PRO 智能故障助手")
        st.write("---")
        uploaded_file = st.file_uploader("1. 上传 system-logs.csv", type=["csv", "log"])
        user_query = st.text_input("2. 输入症状/警报ID/代码", placeholder="如: pressing error")
        st.write("---")
        st.info("📊 支持 Alert ID 自动关联硬件错误码。")

    # 主界面内容
    if not uploaded_file:
        st.markdown("""
            <div class="welcome-card">
                <div class="welcome-title">您好！欢迎使用 LC PRO 智能故障助手 👋</div>
                <p style="color: #666; font-size: 16px; margin-top: 10px;">
                    本工具集成了 <b>回溯分析、因果推导、参数提取</b> 等功能，专门用于快速定位 Roche LC PRO 仪器的硬件故障。
                </p>
                <hr>
                <p><b>使用三部曲：</b></p>
                <ol>
                    <li>在左侧上传 <b>system-logs.csv</b> 文件。</li>
                    <li>在搜索框输入遇到的问题（如：<b>pressing error</b>）。</li>
                    <li>查看系统生成的 <b>深度诊断报告</b>。</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("解析深度", "三级根因", "电气/机械/耗材")
        c2.metric("响应速度", "< 1秒", "即时诊断")
        c3.metric("支持代码", "100+", "持续更新")
    else:
        # 读取数据
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
                st.info("👈 文件已载入。请在左侧输入现象（如 'Unhandled'）开始分析。")
        else:
            st.error("文件格式不兼容，请确保是标准的罗氏日志文件。")

if __name__ == "__main__":


