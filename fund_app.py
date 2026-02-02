import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime
import time
import json
import os

# 页面配置
st.set_page_config(
    page_title="基金收益追踪",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS样式
st.markdown("""
<style>
    .main { padding: 0.5rem 1rem; }
    .fund-card {
        background: white;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 10px;
        border-left: 4px solid #3498db;
    }
    .positive { color: #e74c3c; font-weight: bold; }
    .negative { color: #27ae60; font-weight: bold; }
    .update-time {
        color: #95a5a6;
        font-size: 11px;
        text-align: center;
        margin-top: 15px;
    }
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 数据文件
DATA_FILE = "fund_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "holdings": [
            {"code": "000001", "name": "华夏成长混合", "shares": 5000, "cost": 1.2345},
        ]
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 初始化
if 'data' not in st.session_state:
    st.session_state.data = load_data()

@st.cache_data(ttl=60)
def get_fund_data(codes):
    data_list = []
    try:
        valuation_df = ak.fund_em_valuation()
        for code in codes:
            fund_data = valuation_df[valuation_df['基金代码'] == code]
            if not fund_data.empty:
                growth_str = str(fund_data['估算增长率'].values[0]).replace('%', '')
                data_list.append({
                    'code': code,
                    'name': fund_data['基金名称'].values[0],
                    'estimated_nav': float(fund_data['估算净值'].values[0]),
                    'estimated_growth': float(growth_str) if growth_str not in ['nan', '--'] else 0,
                    'last_nav': float(fund_data['单位净值'].values[0]),
                })
    except Exception as e:
        st.error(f"数据获取失败: {e}")
    return pd.DataFrame(data_list)

# 界面
st.title("📱 基金收益追踪")

# 添加基金
with st.expander("➕ 添加基金"):
    col1, col2, col3 = st.columns(3)
    with col1:
        new_code = st.text_input("基金代码", placeholder="如: 000001")
    with col2:
        new_shares = st.number_input("持有份额", min_value=0.0, value=1000.0, step=100.0)
    with col3:
        new_cost = st.number_input("成本价", min_value=0.0001, value=1.0, step=0.0001, format="%.4f")
    
    if st.button("添加", type="primary"):
        if new_code:
            try:
                info = ak.fund_individual_basic_info_xq(symbol=new_code)
                name = info['name'].values[0] if not info.empty else f"基金{new_code}"
                st.session_state.data['holdings'].append({
                    'code': new_code, 'name': name, 
                    'shares': new_shares, 'cost': new_cost
                })
                save_data(st.session_state.data)
                st.success(f"已添加 {name}")
                time.sleep(1)
                st.rerun()
            except:
                st.error("基金代码错误")

# 获取数据
holdings = st.session_state.data['holdings']
if not holdings:
    st.info("请添加基金")
    st.stop()

codes = [h['code'] for h in holdings]
fund_data = get_fund_data(tuple(codes))

if fund_data.empty:
    st.warning("获取数据中...")
    st.stop()

# 计算收益
total_cost = total_value = 0
results = []

for holding in holdings:
    row = fund_data[fund_data['code'] == holding['code']]
    if not row.empty:
