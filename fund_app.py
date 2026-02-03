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
USER_CONFIG_FILE = "user_config.json"  # 存储用户名列表
ssl_ctx = ssl._create_unverified_context()

st.set_page_config(page_title="资产追踪 Pro", layout="wide", initial_sidebar_state="expanded")

# --- 样式优化 ---
st.markdown("""
<style>
    .main { padding: 0.3rem !important; }
    .block-container { padding-top: 0.3rem !important; padding-bottom: 0.5rem !important; }
    .spacer-top { height: 45px; } /* 灵动岛避让 */
    
    /* 顶部刷新栏 */
    .refresh-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .update-time-inline { font-size: 0.75rem; color: #6c757d; }
    
    /* 黄金区域 */
    .gold-row { display: flex; gap: 6px; margin-bottom: 10px; }
    .gold-box { flex: 1; background: linear-gradient(135deg, #fffdf2 0%, #fff9e6 100%); padding: 8px 4px; border-radius: 8px; text-align: center; border: 1px solid #f0e6cc; }
    .gold-title { font-size: 0.65rem; color: #856404; margin-bottom: 2px; }
    .gold-price { font-size: 1.1rem; font-weight: bold; color: #b8860b; line-height: 1.1; }
    .gold-sub { font-size: 0.6rem; color: #997; }
    
    /* 汇总区域 */
    .summary-box { display: flex; justify-content: space-around; padding: 10px 5px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef; margin-bottom: 12px; }
    .summary-item { text-align: center; flex: 1; }
    .summary-label { font-size: 0.65rem; color: #6c757d; }
    .summary-value { font-size: 1rem; font-weight: bold; }
    
    /* 基金卡片 */
    .fund-card { background: white; padding: 10px 12px; margin-bottom: 8px; border-radius: 8px; border: 1px solid #e9ecef; }
    .fund-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
    .fund-name { font-size: 0.95rem; font-weight: 600; color: #212529; }
    .fund-code { font-size: 0.7rem; color: #6c757d; background: #f1f3f5; padding: 1px 6px; border-radius: 10px; }
    .fund-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center; }
    .fund-item { padding: 6px 2px; background: #f8f9fa; border-radius: 6px; }
    .fund-label { font-size: 0.65rem; color: #868e96; }
    .fund-value-num { font-size: 0.9rem; font-weight: 600; }
    
    /* 颜色控制 */
    .up { color: #e03131; }
    .down { color: #2f9e44; }
    
    /* 隐藏Streamlit默认元素 */
    .stDeployButton { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- 核心逻辑：用户与数据管理 ---
def get_user_list():
    if os.path.exists(USER_CONFIG_FILE):
        with open(USER_CONFIG_FILE, 'r') as f:
            return json.load(f).get("users", ["Default"])
    return ["Default"]

def save_user_list(users):
    with open(USER_CONFIG_FILE, 'w') as f:
        json.dump({"users": users}, f)

def get_data_path(username):
    return f"fund_db_{username}.json"

def load_db(username):
    path = get_data_path(username)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"holdings": []}

def save_db(username, data):
    path = get_data_path(username)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 数据抓取函数 ---
def fetch_gold():
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

def fetch_fund_data(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            data = json.loads(content[content.find('{'):content.rfind('}')+1])
            return {
                "name": data["name"], "code": data["fundcode"],
                "nav": float(data["dwjz"]), "estimate": float(data["gsz"]),
                "change_pct": float(data["gszzl"]), "time": data["gztime"]
            }
    except: return None

# --- 初始化 Session State ---
if 'users' not in st.session_state:
    st.session_state.users = get_user_list()
if 'gold_data' not in st.session_state:
    st.session_state.gold_data = None
if 'fund_cache' not in st.session_state:
    st.session_state.fund_cache = {}

# --- 侧边栏：用户管理 ---
with st.sidebar:
    st.title("👤 用户中心")
    
    # 用户选择
    current_user = st.selectbox("当前操作用户", st.session_state.users, key="active_user")
    
    # 录入用户信息 (持久化要求)
    st.divider()
    st.subheader("个人资料")
    st.info(f"性别: 男 | 年龄: 25 | 身高: 175cm") # 示例展示，可根据需要转为输入框
    
    # 用户增删
    with st.expander("管理用户账号"):
        new_un = st.text_input("新增用户名")
        if st.button("确认添加") and new_un:
            if new_un not in st.session_state.users:
                st.session_state.users.append(new_un)
                save_user_list(st.session_state.users)
                st.rerun()
        
        del_un = st.selectbox("删除用户名", [u for u in st.session_state.users if u != "Default"])
        if st.button("确认删除", type="secondary") and del_un:
            st.session_state.users.remove(del_un)
            save_user_list(st.session_state.users)
            if os.path.exists(get_data_path(del_un)): os.remove(get_data_path(del_un))
            st.rerun()

    st.divider()
    st.caption("💡 提示：睡前一小时记得喝杯热牛奶哦！🥛")

# 加载当前用户持仓
user_db = load_db(current_user)

# --- 主界面渲染 ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)

# 刷新行
col_ref, col_time = st.columns([1, 3])
with col_ref:
    if st.button("🔄 刷新数据", type="primary", use_container_width=True):
        st.session_state.gold_data = fetch_gold()
        st.session_state.fund_cache = {h["code"]: fetch_fund_data(h["code"]) for h in user_db["holdings"]}
        st.session_state.last_refresh = datetime.now(TZ).strftime("%H:%M:%S")
        st.rerun()
with col_time:
    last_ref = st.session_state.get('last_refresh', '未刷新')
    st.markdown(f'<div class="update-time-inline">用户: <b>{current_user}</b> | 更新于: {last_ref}</div>', unsafe_allow_html=True)

# 黄金板块
gold = st.session_state.gold_data or fetch_gold()
st.markdown(f"""
<div class="gold-row">
    <div class="gold-box"><div class="gold-title">上海AU9999</div><div class="gold-price">¥{gold['au9999']:.2f}</div></div>
    <div class="gold-box"><div class="gold-title">国际现货</div><div class="gold-price">${gold['xau_usd']:.2f}</div></div>
    <div class="gold-box"><div class="gold-title">国际换算</div><div class="gold-price">¥{gold['xau_cny']:.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# 统计与列表
total_mv, total_dp, total_tp = 0.0, 0.0, 0.0
valid_holdings = []

for h in user_db["holdings"]:
    f_data = st.session_state.fund_cache.get(h["code"]) or fetch_fund_data(h["code"])
    if f_data:
        st.session_state.fund_cache[h["code"]] = f_data
        mv = h["shares"] * f_data["estimate"]
        dp = h["shares"] * (f_data["estimate"] - f_data["nav"])
        tp = h["shares"] * (f_data["estimate"] - h["cost"])
        total_mv += mv; total_dp += dp; total_tp += tp
        valid_holdings.append((h, f_data, mv, dp, tp))

# 汇总展示
st.markdown(f"""
<div class="summary-box">
    <div class="summary-item"><div class="summary-label">总市值</div><div class="summary-value">¥{total_mv:,.0f}</div></div>
    <div class="summary-item"><div class="summary-label">当日盈亏</div><div class="summary-value {'up' if total_dp>=0 else 'down'}">{total_dp:+,.1f}</div></div>
    <div class="summary-item"><div class="summary-label">累计收益</div><div class="summary-value {'up' if total_tp>=0 else 'down'}">{total_tp:+,.1f}</div></div>
</div>
""", unsafe_allow_html=True)

# 持仓卡片
for idx, (h, f, mv, dp, tp) in enumerate(valid_holdings):
    st.markdown(f"""
    <div class="fund-card">
        <div class="fund-header">
            <div><span class="fund-name">{f['name']}</span> <span class="fund-code">{h['code']}</span></div>
            <div class="fund-label">{f['time'][-5:]}</div>
        </div>
        <div class="fund-grid">
            <div class="fund-item"><div class="fund-label">估值</div><div class="fund-value-num">{f['estimate']:.4f}</div></div>
            <div class="fund-item"><div class="fund-label">涨跌</div><div class="fund-value-num {'up' if f['change_pct']>=0 else 'down'}">{f['change_pct']}%</div></div>
            <div class="fund-item"><div class="fund-label">今日</div><div class="fund-value-num {'up' if dp>=0 else 'down'}">{dp:+.0f}</div></div>
            <div class="fund-item"><div class="fund-label">持有</div><div class="fund-value-num {'up' if tp>=0 else 'down'}">{tp:+.0f}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns([1, 5])
    if c1.button("删除", key=f"del_{idx}"):
        user_db["holdings"].pop(idx)
        save_db(current_user, user_db)
        st.rerun()
    c2.markdown(f"<div style='text-align:right; font-size:0.7rem; color:gray;'>份额: {h['shares']} | 成本: {h['cost']:.4f} | 市值: {mv:.1f}</div>", unsafe_allow_html=True)

# 添加区域
with st.expander("➕ 添加新持仓"):
    nc = st.text_input("代码", max_chars=6)
    ns = st.number_input("份额", min_value=0.0, step=100.0, value=0.0)
    nt = st.number_input("成本", min_value=0.0, step=0.001, value=0.0, format="%.4f")
    if st.button("确认添加", use_container_width=True):
        user_db["holdings"].append({"code": nc, "shares": ns, "cost": nt})
        save_db(current_user, user_db)
        st.rerun()
