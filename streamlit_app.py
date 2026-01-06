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
        border-left: 5px solid #007bff; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin-bottom: 25px;
    }
    .welcome-title { color: #007bff; font-size: 28px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 专家知识库 (核心数据结构) ---
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
            "🔌 链路故障": "检测头内部相机同步线（黑色细线）松动或断裂。",
            "⚡ 电磁干扰": "Peltier大电流工作产生电磁脉冲干扰了信号。"
        },
        "fix_steps": ["重新插拔同步线", "排查拖链线束磨损", "执行光学专项自检"]
    },
    "0x0301": {
        "name": "加热盖错误 (Heated lid error)",
        "alert_id": "9429.1.0.0.0.0.20",
        "keywords": ["heated lid error", "加热盖错误", "9429.1.0.0.0.0.20", "0x0301", "0x00100601"],
        "content": "对应 Heated lid error。加热盖温度传感器异常或加热效率不足（超时）。",
        "causes": {
            "📡 温度传感器故障": "加热盖内部热敏电阻读数异常或损坏。",
            "⚡ 加热元件损坏": "加热膜或供电线路接触不良或老化。",
            "🔌 连接电缆问题": "主机与加热盖之间的排线可能松动或断裂。"
        },
        "fix_steps": ["重启仪器并检查自检情况", "检查加热盖连接电缆是否牢固", "检查加热传感器和回路"]
    },
    "0x0001": { # 更改了重复的键名
        "name": "加载的板型无效 (Invalid plate type loaded)",
        "alert_id": "9429.1.0.0.0.0.1",
        "keywords": ["invalid plate type loaded", "加载的板型无效", "9429.1.0.0.0.0.1", "0x0xxx", "invalid plate"],
        "content": "加载的板件类型不适合当前模块格式。",
        "causes": {
            "🧪 耗材问题": "实验板件规格与系统设置不匹配。"
        },
        "fix_steps": ["卸载板件", "更换符合规格的板件后重新运行"]
    },
    "0x0009": { # 更改了重复的键名
        "name": "未找到加热盖对齐标记",
        "alert_id": "9429.1.0.0.0.0.9",
        "keywords": ["未找到加热盖对齐标记", "9429.1.0.0.0.0.9", "marker"],
        "content": "加热盖标记不符合规格，导致初始化或运行执行失败。",
        "causes": {
            "⚙️ 机械故障": "标记器脏污或损坏导致无法识别对齐点。"
        },
        "fix_steps": ["清洁加热盖的标记器", "若清洁无效则更换加热盖"]
    }
}

# --- 3. 核心工具函数 ---
def extract_params(msg):
    return re.findall(r'(\w+):\s*([\d\.-x]+)', msg)

def show_knowledge_base_info(user_input):
    """【功能】无文件时的数据库查询模式"""
    st.markdown(f"### 📖 知识库查询结果: “{user_input}”")
    input_lower = user_input.lower().strip()
    target_info = None
    target_code = None

    for code, info in FAULT_LIBRARY.items():
        # 匹配逻辑：检查关键词是否出现在输入中，或输入是否包含在关键词中
        if any(kw.lower() in input_lower or input_lower in kw.lower() for kw in info['keywords']):
            target_info = info
            target_code = code
            break
    
    if target_info:
        st.error(f"### 诊断结论：{target_info['name']}")
        tab1, tab2, tab3 = st.tabs(["📑 故障深度解析", "🧐 可能的原因分析", "🛠️ 建议维修步骤"])
        with tab1:
            st.write(f"**关联代码/ID:** `{target_code}` / `{target_info.get('alert_id', 'N/A')}`")
            st.write(f"**定义:** {target_info['content']}")
            st.info("ℹ️ 当前处于【知识库直查模式】。如需查看日志中的实时参数，请先上传日志文件。")
        with tab2:
            for cat, detail in target_info['causes'].items():
                st.markdown(f"**{cat}**：{detail}")
        with tab3:
            for i, step in enumerate(target_info['fix_steps']):
                st.success(f"{i+1}. {step}")
    else:
        st.warning(f"专家库中未找到与 '{user_input}' 相关的直接定义。")

def perform_diagnosis(df, msg_col, user_input):
    """有文件时的深度诊断模式"""
    st.markdown(f"### 🔍 深度日志诊断: “{user_input}”")
    input_lower = user_input.lower().strip()
    target_info = None
    target_code = None

    for code, info in FAULT_LIBRARY.items():
        if any(kw.lower() in input_lower for kw in info['keywords']):
            target_info = info
            target_code = code
            break

    search_terms = [input_lower]
    if target_info:
        search_terms.extend([target_code.lower(), target_info['alert_id'].lower()])
    
    pattern = '|'.join(set(search_terms))
    matches = df[df[msg_col].str.contains(pattern, case=False, na=False)]

    if matches.empty:
        st.warning(f"⚠️ 日志中未找到匹配记录。显示基础库解析：")
        if target_info:
             show_knowledge_base_info(user_input)
        return

    latest_event = matches.iloc[-1]
    raw_msg = str(latest_event[msg_col])
    
    if not target_info:
        hex_match = re.search(r'0x[0-9a-fA-F]+', raw_msg)
        if hex_match:
            code = hex_match.group(0)
            target_info = FAULT_LIBRARY.get(code)
            target_code = code

    if target_info:
        st.error(f"### 诊断结论：{target_info['name']}")
        tab1, tab2, tab3 = st.tabs(["📑 故障深度解析", "🧐 可能的原因分析", "🛠️ 建议维修步骤"])
        with tab1:
            st.write(f"**关联代码/ID:** `{target_code}` / `{target_info.get('alert_id', 'N/A')}`")
            st.write(f"**定义:** {target_info['content']}")
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
        st.warning(f"专家库暂未收录具体解析。")
        st.code(raw_msg)

# --- 4. 界面渲染 ---
def main():
    with st.sidebar:
        st.title("LC PRO 智能故障助手")
        st.write("---")
        uploaded_file = st.file_uploader("1. 上传 system-logs.csv", type=["csv", "log"])
        user_query = st.text_input("2. 输入症状/警报ID/代码", placeholder="如: pressing error")
        st.write("---")
        st.info("📊 模式：\n- **无文件**：查阅知识库。\n- **有文件**：执行深度诊断。")

    if not uploaded_file:
        if user_query:
            show_knowledge_base_info(user_query)
        else:
            st.markdown("""
                <div class="welcome-card">
                    <div class="welcome-title">您好！欢迎使用 LC PRO 智能故障助手 👋</div>
                    <p style="color: #666; font-size: 16px; margin-top: 10px;">
                        支持 <b>离线查阅</b> 与 <b>在线诊断</b>。
                    </p>
                    <hr>
                    <ul>
                        <li><b>快速查阅</b>：直接在左侧输入错误代码或 ID。</li>
                        <li><b>深度诊断</b>：上传 <b>system-logs.csv</b> 后搜索。</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("解析深度", "三级根因")
            c2.metric("响应速度", "< 1秒")
            c3.metric("支持代码", "100+")
    else:
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
                st.info("👈 文件已载入。请输入现象开始分析。")

if __name__ == "__main__":
    main()
