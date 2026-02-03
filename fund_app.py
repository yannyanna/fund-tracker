import streamlit as st
from datetime import datetime
import json
import os
import urllib.request
import ssl
import re
import pytz

# --- 基础配置 ---
TZ = pytz.timezone('Asia/Shanghai')
USER_CONFIG_FILE = "user_config.json"
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="资产追踪", layout="wide", initial_sidebar_state="expanded")

# --- 样式优化 ---
st.markdown("""
<style>
    .main { padding: 0.1rem !important; }
    .spacer-top { height: 45px; } 
    
    /* 黄金区域 - 三列一行 */
    .gold-row { display: flex; gap: 6px; margin-bottom: 12px; }
    .gold-box {
        flex: 1; background: linear-gradient(135deg, #fffdf2 0%, #fff9e6 100%);
        padding: 8px 4px; border-radius: 8px; text-align: center; border: 1px solid #f0e6cc;
    }
    .gold-title { font-size: 0.65rem; color: #856404; margin-bottom: 2px; }
    .gold-price { font-size: 1.1rem; font-weight: bold; color: #b8860b; line-height: 1.1; }
    .gold-sub { font-size: 0.6rem; color: #997; }

    /* 基金卡片：纯展示 */
    .fund-card {
        background: white; padding: 12px; margin-bottom: 10px;
        border-radius: 10px; border: 1px solid #eee;
    }
    .fund-header { display: flex; justify-content: space-between; align-items: center; }
    .fund-name { font-size: 0.95rem; font-weight: bold; color: #333; }
    .fund-code { font-size: 0.75rem; color: #999; background: #f1f3f5; padding: 1px 5px; border-radius: 5px; }
    .data-row { display: flex; justify-content: space-between; margin-top: 10px; }
    .data-item { text-align: center; flex: 1; }
    .data-label { font-size: 0.65rem; color: #888; margin-bottom: 2px; }
    .data-value { font-size: 0.9rem; font-weight: 600; }
    
    /* 底部管理区 */
    .admin-section {
        margin-top: 30px; padding: 15px; background: #f8f9fa;
        border-top: 2px solid #eee; border-radius: 15px 15px 0 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 核心逻辑 ---
def load_config():
    if os.path.exists(USER_CONFIG_FILE):
        with open(USER_CONFIG_FILE, 'r') as f: return json.load(f)
    return {"users": ["Default"], "current": "Default"}

def save_config(config):
    with open(USER_CONFIG_FILE, 'w') as f: json.dump(config, f)

def get_db(username):
    path = f"db_{username}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {"holdings": []}

def save_db(username, data):
    with open(f"db_{username}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_gold_data():
    res_data = {"au9999": 0.0, "xau_usd": 0.0, "usdcny": 0.0, "xau_cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            data = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([^"]+)"', data)
            m2 = re.search(r'hf_XAU="([^"]+)"', data)
            m3 = re.search(r'fx_susdcnh="([^"]+)"', data)
            if m1: res_data["au9999"] = float(m1.group(1).split(',')[0])
            if m2: res_data["xau_usd"] = float(m2.group(1).split(',')[0])
            if m3: res_data["usdcny"] = float(m3.group(1).split(',')[1])
            if res_data["xau_usd"] > 0:
                res_data["xau_cny"] = (res_data["xau_usd"] * res_data["usdcny"]) / 31.1034768
    except: pass
    return res_data

# --- 侧边栏 ---
config = load_config()
with st.sidebar:
    st.subheader("👤 账号管理")
    current_user = st.selectbox("当前用户", config["users"], index=config["users"].index(config["current"]))
    if current_user != config["current"]:
        config["current"] = current_user
        save_user_config(config)
        st.rerun()

    with st.expander("编辑用户名"):
        new_un = st.text_input("新增用户")
        if st.button("确认添加") and new_un:
            if new_un not in config["users"]:
                config["users"].append(new_un)
                save_config(config)
                st.rerun()
        
        del_un = st.selectbox("删除用户", [u for u in config["users"] if u != "Default"])
        if st.button("确认删除", type="secondary"):
            config["users"].remove(del_un)
            if config["current"] == del_un: config["current"] = "Default"
            save_config(config)
            st.rerun()
    st.divider()
    st.caption("🥛 睡前一小时记得喝杯热牛奶")

# --- 主页面 ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)
db = get_db(current_user)

# 1. 刷新与黄金看板
if st.button("🔄 刷新全部数据", type="primary", use_container_width=True):
    st.session_state.gold_cache = fetch_gold_data()
    st.rerun()

gold = st.session_state.get("gold_cache", fetch_gold_data())
st.markdown(f"""
<div class="gold-row">
    <div class="gold-box">
        <div class="gold-title">上海AU9999</div>
        <div class="gold-price">¥{gold['au9999']:.2f}</div>
        <div class="gold-sub">元/克</div>
    </div>
    <div class="gold-box">
        <div class="gold-title">国际现货</div>
        <div class="gold-price">${gold['xau_usd']:.2f}</div>
        <div class="gold-sub">美元/盎司</div>
    </div>
    <div class="gold-box">
        <div class="gold-title">国际(换算)</div>
        <div class="gold-price">¥{gold['xau_cny']:.2f}</div>
        <div class="gold-sub">汇率{gold['usdcny']:.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 2. 基金持仓展示区
st.write(f"当前用户：**{current_user}**")
if not db["holdings"]:
    st.info("暂无持仓，请在底部管理区添加。")
else:
    for h in db["holdings"]:
        st.markdown(f"""
        <div class="fund-card">
            <div class="fund-header">
                <div class="fund-name">{h.get('name', '持仓基金')}</div>
                <div class="fund-code">{h['code']}</div>
            </div>
            <div class="data-row">
                <div class="data-item">
                    <div class="data-label">持有份额</div>
                    <div class="data-value">{h['shares']:,}</div>
                </div>
                <div class="data-item">
                    <div class="data-label">持仓成本</div>
                    <div class="data-value">¥{h['cost']:.4f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 3. 底部管理区
st.markdown('<div class="admin-section">', unsafe_allow_html=True)
st.subheader("⚙️ 持仓管理")
m_col1, m_col2, m_col3 = st.columns([1, 1, 1])
m_code = m_col1.text_input("代码", max_chars=6, placeholder="6位代码")
m_shares = m_col2.number_input("份额", value=None, placeholder="0.00")
m_cost = m_col3.number_input("成本", value=None, placeholder="0.0000", format="%.4f")

btn_col1, btn_col2 = st.columns(2)
if btn_col1.button("✅ 保存/更新", type="primary", use_container_width=True):
    if m_code and m_shares is not None and m_cost is not None:
        idx = next((i for i, item in enumerate(db["holdings"]) if item["code"] == m_code), None)
        if idx is not None: db["holdings"][idx] = {"code": m_code, "shares": m_shares, "cost": m_cost}
        else: db["holdings"].append({"code": m_code, "shares": m_shares, "cost": m_cost})
        save_db(current_user, db)
        st.rerun()

if btn_col2.button("🗑️ 删除该代码", use_container_width=True):
    if m_code:
        db["holdings"] = [item for item in db["holdings"] if item["code"] != m_code]
        save_db(current_user, db)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
