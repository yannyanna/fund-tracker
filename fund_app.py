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

# --- 样式：严格左右布局与极简看板 ---
st.markdown("""
<style>
    .main { padding: 0.1rem !important; }
    .spacer-top { height: 45px; } 
    
    /* 黄金区域 */
    .gold-row { display: flex; gap: 6px; margin-bottom: 12px; }
    .gold-box {
        flex: 1; background: linear-gradient(135deg, #fffdf2 0%, #fff9e6 100%);
        padding: 8px 4px; border-radius: 8px; text-align: center; border: 1px solid #f0e6cc;
    }
    .gold-price { font-size: 1.1rem; font-weight: bold; color: #b8860b; }

    /* 基金卡片展示 */
    .fund-card {
        background: white; padding: 12px; margin-bottom: 10px;
        border-radius: 10px; border: 1px solid #eee;
    }
    .fund-name { font-size: 0.95rem; font-weight: bold; color: #333; }
    .fund-code { font-size: 0.75rem; color: #888; margin-left: 5px; }
    .data-row { display: flex; justify-content: space-between; margin-top: 8px; }
    .data-item { text-align: center; flex: 1; }
    .data-label { font-size: 0.65rem; color: #999; }
    .data-value { font-size: 0.9rem; font-weight: 600; }
    
    /* 底部管理区：严格左右对齐 */
    .admin-section {
        margin-top: 20px; padding: 15px; background: #f8f9fa;
        border-top: 2px solid #ddd; border-radius: 15px 15px 0 0;
    }
    .input-row { display: flex; align-items: center; margin-bottom: 8px; }
    .label-box { width: 60px; font-size: 0.9rem; color: #333; font-weight: bold; }
    .field-box { flex: 1; }
</style>
""", unsafe_allow_html=True)

# --- 数据持久化与采集 ---
def load_config():
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"users": ["Default"], "current": "Default"}

def save_config(cfg):
    with open(USER_CONFIG_FILE, 'w') as f: json.dump(cfg, f)

def get_db(username):
    path = f"db_{username}.json"
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"holdings": []}

def save_db(username, data):
    with open(f"db_{username}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_fund_name(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            return json.loads(content[content.find('{'):content.rfind('}')+1])['name']
    except: return "未知基金"

def fetch_gold():
    d = {"au": 0.0, "xau": 0.0, "fx": 0.0, "cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([^"]+)"', raw)
            m2 = re.search(r'hf_XAU="([^"]+)"', raw)
            m3 = re.search(r'fx_susdcnh="([^"]+)"', raw)
            if m1: d["au"] = float(m1.group(1).split(',')[0])
            if m2: d["xau"] = float(m2.group(1).split(',')[0])
            if m3: d["fx"] = float(m3.group(1).split(',')[1])
            if d["xau"] > 0: d["cny"] = (d["xau"] * d["fx"]) / 31.1035
    except: pass
    return d

# --- 侧边栏：仅用户名管理 ---
config = load_config()
with st.sidebar:
    st.subheader("👤 账号切换")
    cur_u = st.selectbox("当前用户", config["users"], index=config["users"].index(config["current"]) if config["current"] in config["users"] else 0)
    if cur_u != config["current"]:
        config["current"] = cur_u
        save_config(config)
        st.rerun()
    with st.expander("管理用户"):
        new_u = st.text_input("新增")
        if st.button("添加") and new_u:
            if new_u not in config["users"]:
                config["users"].append(new_u)
                save_config(config)
                st.rerun()
        del_u = st.selectbox("删除", [u for u in config["users"] if u != "Default"])
        if st.button("确认删除"):
            config["users"].remove(del_u)
            if config["current"] == del_u: config["current"] = "Default"
            save_config(config)
            st.rerun()
    st.divider()
    st.caption("🥛 睡前一小时记得喝杯热牛奶")

# --- 主页面 ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)
db = get_db(cur_u)

# 1. 刷新与黄金
if st.button("🔄 刷新全部数据", type="primary", use_container_width=True):
    st.session_state.g_cache = fetch_gold()
    st.rerun()

g = st.session_state.get("g_cache", fetch_gold())
st.markdown(f"""
<div class="gold-row">
    <div class="gold-box"><div style="font-size:0.6rem">上海金</div><div class="gold-price">¥{g['au']:.2f}</div></div>
    <div class="gold-box"><div style="font-size:0.6rem">国际现货</div><div class="gold-price">${g['xau']:.2f}</div></div>
    <div class="gold-box"><div style="font-size:0.6rem">折合人民币</div><div class="gold-price">¥{g['cny']:.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# 2. 持仓看板（纯展示结果）
st.write(f"当前用户：**{cur_u}**")
for h in db["holdings"]:
    st.markdown(f"""
    <div class="fund-card">
        <div class="fund-name">{h.get('name', '加载中...')} <span class="fund-code">{h['code']}</span></div>
        <div class="data-row">
            <div class="data-item"><div class="data-label">份额</div><div class="data-value">{h['shares']:,}</div></div>
            <div class="data-item"><div class="data-label">成本</div><div class="data-value">¥{h['cost']:.4f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 3. 底部管理区（左右布局）
st.markdown('<div class="admin-section">', unsafe_allow_html=True)
st.subheader("⚙️ 持仓增减/修改")

# 代码行
c1, c2 = st.columns([1, 4])
with c1: st.markdown('<div style="padding-top:10px; font-weight:bold;">代码</div>', unsafe_allow_html=True)
with c2: m_code = st.text_input("code", max_chars=6, placeholder="输入6位代码", label_visibility="collapsed")

# 份额行
c3, c4 = st.columns([1, 4])
with c3: st.markdown('<div style="padding-top:10px; font-weight:bold;">份额</div>', unsafe_allow_html=True)
with c4: m_shares = st.number_input("shares", value=None, placeholder="0.00", label_visibility="collapsed")

# 成本行
c5, c6 = st.columns([1, 4])
with c5: st.markdown('<div style="padding-top:10px; font-weight:bold;">成本</div>', unsafe_allow_html=True)
with c6: m_cost = st.number_input("cost", value=None, placeholder="0.0000", format="%.4f", label_visibility="collapsed")

b1, b2 = st.columns(2)
if b1.button("✅ 保存修改/新增", type="primary", use_container_width=True):
    if m_code and m_shares is not None:
        fname = fetch_fund_name(m_code)
        idx = next((i for i, x in enumerate(db["holdings"]) if x["code"] == m_code), None)
        new_data = {"code": m_code, "name": fname, "shares": m_shares, "cost": m_cost if m_cost else 0.0}
        if idx is not None: db["holdings"][idx] = new_data
        else: db["holdings"].append(new_data)
        save_db(cur_u, db)
        st.rerun()

if b2.button("🗑️ 删除持仓", use_container_width=True):
    db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
    save_db(cur_u, db)
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
