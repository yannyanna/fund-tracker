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

# --- 样式：极简看板风 ---
st.markdown("""
<style>
    .main { padding: 0.1rem !important; }
    .spacer-top { height: 45px; } 
    /* 基金卡片：纯展示 */
    .fund-card {
        background: white; padding: 12px; margin-bottom: 10px;
        border-radius: 10px; border: 1px solid #eee;
    }
    .fund-header { display: flex; justify-content: space-between; align-items: center; }
    .fund-name { font-size: 1rem; font-weight: bold; color: #333; }
    .fund-code { font-size: 0.75rem; color: #999; }
    .data-row { display: flex; justify-content: space-between; margin-top: 10px; }
    .data-item { text-align: center; flex: 1; }
    .data-label { font-size: 0.65rem; color: #888; margin-bottom: 2px; }
    .data-value { font-size: 0.9rem; font-weight: 600; }
    
    .up { color: #e03131; } .down { color: #2f9e44; }
    
    /* 底部管理区样式 */
    .admin-section {
        margin-top: 30px;
        padding: 15px;
        background: #f8f9fa;
        border-top: 2px solid #eee;
        border-radius: 15px 15px 0 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 用户与文件系统 ---
def load_user_config():
    if os.path.exists(USER_CONFIG_FILE):
        with open(USER_CONFIG_FILE, 'r') as f: return json.load(f)
    return {"users": ["Default"], "current": "Default"}

def save_user_config(config):
    with open(USER_CONFIG_FILE, 'w') as f: json.dump(config, f)

def get_db(username):
    path = f"db_{username}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return {"holdings": []}

def save_db(username, data):
    with open(f"db_{username}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 侧边栏：仅限用户名管理 ---
config = load_user_config()
with st.sidebar:
    st.subheader("👤 账号切换")
    current_user = st.selectbox("当前用户", config["users"], index=config["users"].index(config["current"]))
    
    if current_user != config["current"]:
        config["current"] = current_user
        save_user_config(config)
        st.rerun()

    with st.expander("管理用户名"):
        new_un = st.text_input("新增用户")
        if st.button("确认添加", use_container_width=True) and new_un:
            if new_un not in config["users"]:
                config["users"].append(new_un)
                save_user_config(config)
                st.rerun()
        
        del_un = st.selectbox("删除用户", [u for u in config["users"] if u != "Default"])
        if st.button("确认删除", type="secondary", use_container_width=True):
            config["users"].remove(del_un)
            if config["current"] == del_un: config["current"] = "Default"
            save_user_config(config)
            st.rerun()

# --- 主页面展示 ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)
db = get_db(current_user)

# 顶部标题与刷新
col_t1, col_t2 = st.columns([3, 1])
col_t1.title(f"{current_user} 的资产看板")
if col_t2.button("🔄 刷新", use_container_width=True):
    st.rerun()

# 基金卡片展示区
if not db["holdings"]:
    st.info("暂无持仓数据，请在底部添加。")
else:
    for h in db["holdings"]:
        # 这里的展示逻辑可以根据实际API获取的数据增强
        st.markdown(f"""
        <div class="fund-card">
            <div class="fund-header">
                <div class="fund-name">{h.get('name', '基金')}</div>
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
                <div class="data-item">
                    <div class="data-label">当前状态</div>
                    <div class="data-value">已同步</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- 底部管理区域：添加、修改、删除 ---
st.markdown('<div class="admin-section">', unsafe_allow_html=True)
st.subheader("⚙️ 持仓管理")

with st.container():
    # 采用横向布局
    m_col1, m_col2, m_col3 = st.columns([1, 1, 1])
    m_code = m_col1.text_input("基金代码", max_chars=6, placeholder="6位数字")
    m_shares = m_col2.number_input("份额", value=None, placeholder="输入份额", step=0.01)
    m_cost = m_col3.number_input("成本", value=None, placeholder="输入成本", step=0.0001, format="%.4f")
    
    btn_col1, btn_col2 = st.columns(2)
    
    if btn_col1.button("✅ 保存 (新增或更新)", type="primary", use_container_width=True):
        if m_code and m_shares is not None and m_cost is not None:
            # 检查是否存在，存在则更新，不存在则添加
            idx = next((i for i, item in enumerate(db["holdings"]) if item["code"] == m_code), None)
            if idx is not None:
                db["holdings"][idx] = {"code": m_code, "shares": m_shares, "cost": m_cost}
                st.toast(f"已更新 {m_code}")
            else:
                db["holdings"].append({"code": m_code, "shares": m_shares, "cost": m_cost})
                st.toast(f"已添加 {m_code}")
            save_db(current_user, db)
            st.rerun()
        else:
            st.error("请完整填写代码、份额和成本")

    if btn_col2.button("🗑️ 删除该代码持仓", use_container_width=True):
        if m_code:
            new_holdings = [item for item in db["holdings"] if item["code"] != m_code]
            if len(new_holdings) < len(db["holdings"]):
                db["holdings"] = new_holdings
                save_db(current_user, db)
                st.toast(f"已删除 {m_code}")
                st.rerun()
            else:
                st.warning("未找到该代码")
        else:
            st.error("请输入要删除的代码")

st.markdown('</div>', unsafe_allow_html=True)
