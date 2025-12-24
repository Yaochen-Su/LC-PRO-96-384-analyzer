import streamlit as st
import pandas as pd
import re
import io

# 页面基础设置
st.set_page_config(page_title="LC PRO 96 故障诊断专家", page_icon="👨‍🔧", layout="wide")

# --- 1. 专家级故障百科全书 (解析库) ---
# 这里是工具的“大脑”，您可以根据维修经验不断丰富它
FAULT_DETAILS = {
    "0x0189": {
        "name": "检测单元同步信号超时 (Optical Sync Timeout)",
        "content": "在该报错期间，相机已完成图像采集，但负责控制LED亮度的LEDCntrl板未能在预定窗口期内接收到相机的触发脉冲信号（Sync Signal）。",
        "logic_gap": "相机触发输出 -> 同步电缆 -> LED控制板输入。此闭环中任意环节中断均会触发0x0189。",
        "causes": {
            "🔌 电气/信号": "同步排线接头氧化或松动；主控板5V逻辑供电波动；电磁干扰导致脉冲信号出现毛刺。",
            "⚙️ 机械/磨损": "检测头在Y轴往复运动中，拖链内的柔性排线发生疲劳断裂（瞬时开路）。",
            "📷 组件故障": "相机模组的触发引脚电路损坏，或LED控制板的光耦接收端失效。"
        },
        "fix_steps": ["重新插拔并清洁相机与控制板间的同步线", "检查检测头拖链排线是否有挤压或破损点", "在诊断模式下连续采集50张图像查看报错频率"]
    },
    "0x0229": {
        "name": "加热盖压紧动作失败 (Cover Pressing Failure)",
        "content": "加热盖电机尝试将盖子下压至密封位置，但压力传感器反馈的数值在规定电机步数内未达标，或触发了异常阻力报警。",
        "logic_gap": "电机步数计数 <-> 压力传感器反馈。两者不匹配说明机械受阻或反馈丢失。",
        "causes": {
            "🧪 耗材/操作": "使用了高度超标的非原厂孔板；封板膜过厚；孔板未在底座中放平。",
            "⚙️ 机械结构": "加热盖压紧丝杆缺少润滑导致阻力过大；压力传感器（Load Cell）零点漂移。",
            "⚡ 电动控制": "压盖电机驱动板电流限制设置过低；电机排线接触不良。"
        },
        "fix_steps": ["检查并更换标准PCR耗材测试", "手动旋转丝杆检查是否有卡涩感并润滑", "在Service Tool中执行压力校准(Pressure Calibration)"]
    }
}

# --- 2. 核心逻辑函数 ---
def extract_params(msg):
    """自动提取日志中的原始参数，如 UTEC, Temp, Pos 等"""
    # 匹配 Key: Value 格式
    pattern = r'(\w+):\s*([\d\.-x]+)'
    return re.findall(pattern, msg)

def render_diagnosis(code, raw_msg):
    """渲染详细的故障解析界面"""
    st.divider()
    if code in FAULT_DETAILS:
        detail = FAULT_DETAILS[code]
        st.subheader(f"🔍 故障解析: {detail['name']}")
        
        # 第一部分：故障包括的内容
        with st.expander("📝 故障内容定义", expanded=True):
            st.write(f"**核心描述：** {detail['content']}")
            st.info(f"**底层逻辑：** {detail['logic_gap']}")
        
        # 第二部分：提取出的运行参数
        params = extract_params(raw_msg)
        if params:
            st.write("**📊 报错时底层参数快照：**")
            cols = st.columns(len(params) if len(params) < 5 else 5)
            for i, (p_name, p_val) in enumerate(params):
                cols[i % 5].metric(p_name, p_val)

        # 第三部分：可能导致的原因
        st.write("**🕵️ 可能的原因分析：**")
        c1, c2, c3 = st.columns(3)
        cause_list = list(detail['causes'].items())
        c1.warning(f"**{cause_list[0][0]}**\n\n{cause_list[0][1]}")
        c2.warning(f"**{cause_list[1][0]}**\n\n{cause_list[1][1]}")
        c3.warning(f"**{cause_list[2][0]}**\n\n{cause_list[2][1]}")
        
        # 第四部分：维修建议
        st.success("**🛠️ 维修指引步骤：**\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(detail['fix_steps'])]))
    else:
        st.warning(f"⚠️ 专家库暂未覆盖代码 `{code}`。建议查看下方原始日志，并重点关注其中的 CDI 代码。")
        st.code(raw_msg)

# --- 3. Streamlit 主界面 ---
st.title("👨‍🔧 Roche LC PRO 96 智能维修助理")
uploaded_file = st.file_uploader("请上传 system-logs.csv", type=["csv", "log"])

if uploaded_file:
    # (此处省略读取和预处理逻辑，参考之前版本)
    # ... (代码逻辑：读取df, 查找error_df) ...
    
    # 假设我们已经找到了对应的 error_df
    # 模拟用户点击了某条错误进行分析：
    # code = "0x0189" 
    # raw_msg = "..." 
    # render_diagnosis(code, raw_msg)
    pass
