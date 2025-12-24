import streamlit as st
import pandas as pd
import re
import io

# 页面配置
st.set_page_config(page_title="LC PRO 96 智能专家系统", page_icon="🧪", layout="wide")

# --- 1. 细化后的因果解析专家库 ---
FAULT_DETAILS = {
    "0x0189": {
        "name": "检测单元同步超时 (Optical Sync Timeout)",
        "content": "检测模块接收相机的Sync脉冲失败。这意味着图像虽然拍了，但控制板不知道灯该什么时候闪。",
        "logic_gap": "相机触发 -> 同步电缆 -> LED控制板输入。",
        "causes": {
            "🔌 电气/信号": "同步排线接头氧化；主控板5V供电波动干扰了逻辑电平。",
            "⚙️ 机械/磨损": "Y轴移动时，拖链内的排线受拉扯产生瞬时开路。",
            "📷 组件故障": "相机模组触发引脚损坏。"
        },
        "fix_steps": ["检查同步线", "排查拖链排线", "连续采集测试"]
    },
    "0x0229": {
        "name": "加热盖压紧动作失败 (Cover Pressing Failure)",
        "content": "盖子下压压力未达标，或电机步数已满但未触碰到压力平衡点。",
        "logic_gap": "电机步数 vs 压力反馈。两者不同步。",
        "causes": {
            "🧪 耗材/操作": "PCR板高度超标；封板膜过厚；板子没放平。",
            "⚙️ 机械结构": "压紧丝杆干涸导致阻力过大；压力传感器(Load Cell)损坏。",
            "⚡ 电动控制": "驱动板电流限制触发。"
        },
        "fix_steps": ["更换耗材测试", "润滑丝杆", "重新压力校准"]
    },
    "0x0301": { # 新增：电源模块解析
        "name": "电源供应不稳/电压跌落 (PSU Voltage Sag)",
        "content": "主控板监测到DC总线电压瞬间低于设定阈值。这通常发生在Peltier全功率升温瞬间。",
        "logic_gap": "瞬时电流需求 > 电源带载能力。",
        "causes": {
            "🔋 电源老化": "电源模块内部电容失效，导致大电流输出时纹波过大或电压骤降。",
            "🔥 热负载异常": "Peltier元件老化阻值改变，产生了异常的浪涌电流。",
            "🌬️ 散热失效": "电源板风扇停转导致过热保护，功率输出被限制。"
        },
        "fix_steps": ["测量升温瞬间DC 24V/48V电压平稳度", "检查电源风扇是否运转", "排查Peltier模块阻值"]
    },
    "0x0405": { # 新增：条码模块解析
        "name": "条码扫描器识别失败 (Barcode Read Failure)",
        "content": "条码扫描头已启动但未能在超时时间内解析出有效的条码信息。",
        "logic_gap": "扫描器激活 -> 图像采集 -> 算法识别。其中任一环节光路不通或对比度不足。",
        "causes": {
            "🧼 物理遮挡": "扫描头镜头玻璃有指纹、油污或实验室粉尘。",
            "💡 环境光干扰": "实验室上方强光源直射入扫描口，冲淡了扫描器的辅助红光。",
            "🏷️ 耗材质量": "条码打印对比度太低，或条码粘贴位置偏移出了扫描窗。"
        },
        "fix_steps": ["使用无水酒精擦拭扫描头镜头", "检查条码贴纸位置是否垂直", "尝试调暗实验室环境光测试"]
    }
}

# --- 2. 核心分析逻辑函数 ---
def extract_params(msg):
    pattern = r'(\w+):\s*([\d\.-x]+)'
    return re.findall(pattern, msg)

def perform_diagnosis(df, msg_col, user_input):
    """基于用户输入的症状进行回溯分析"""
    st.markdown("### 🛠️ 深度根因分析报告")
    
    # 将用户输入的症状转化为搜索关键词
    keyword_map = {
        "停机": "ErrorCode|Failure|Emergency",
        "压盖": "PressCover|Lid|0x0229",
        "条码": "Barcode|Scanner|0x0405",
        "电源": "Power|Voltage|0x0301",
        "荧光": "Detection|Optical|0x0189"
    }
    
    # 模糊搜索用户关键词
    search_pattern = "|".join([v for k, v in keyword_map.items() if k in user_input])
    if not search_pattern: search_pattern = user_input # 如果没匹配到，直接按用户输入的查
    
    # 在日志中查找
    matches = df[df[msg_col].str.contains(search_pattern, case=False, na=False)].tail(5)
    
    if matches.empty:
        st.warning("在日志中未找到直接相关的错误记录。建议尝试更换关键词，如“0x0189”或“Motor”。")
        return

    # 获取最新的一条错误
    latest_error = matches.iloc[-1]
    raw_msg = latest_error[msg_col]
    
    # 提取错误码
    code_match = re.search(r'0x[0-9a-fA-F]+', raw_msg)
    code = code_match.group(0) if code_match else "Unknown"

    # 展示诊断结论
    if code in FAULT_DETAILS:
        detail = FAULT_DETAILS[code]
        st.error(f"📍 定位故障：{detail['name']}")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write(f"**现象解析：** {detail['content']}")
            st.write(f"**可能原因：**")
            for cat, val in detail['causes'].items():
                st.write(f"- **{cat}**: {val}")
        with c2:
            st.info(f"**参数监测：**")
            params = extract_params(raw_msg)
            for p_name, p_val in params:
                st.write(f"`{p_name}`: {p_val}")
        
        st.success(f"**建议排查步骤：**\n\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(detail['fix_steps'])]))
    else:
        st.warning(f"检测到代码 `{code}`，但专家库尚未收录详细因果逻辑。")
        st.code(raw_msg)

# --- 3. Streamlit UI 布局 ---
def main():
    st.sidebar.title("🛠️ 维修控制面板")
    uploaded_file = st.sidebar.file_uploader("1. 上传日志文件", type=["csv", "log"])
    
    # 故障输入对话框 (这正是您提到的缺少的部分)
    user_input = st.sidebar.text_input("2. 描述故障现象 (如：压盖报错、停机、条码失败)", "")
    
    if uploaded_file:
        df = None
        for enc in ['utf-8', 'gbk', 'utf-16']:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep='\t', header=None, encoding=enc, encoding_errors='replace')
                break
            except: continue
        
        if df is not None:
            msg_col = df.shape[1] - 1
            df[msg_col] = df[msg_col].astype(str)
            
            if user_input:
                perform_diagnosis(df, msg_col, user_input)
            else:
                st.info("💡 请在左侧侧边栏输入具体的故障现象，系统将为您分析日志根因。")
        else:
            st.error("文件读取失败，请检查文件格式。")

if __name__ == "__main__":
    main()
