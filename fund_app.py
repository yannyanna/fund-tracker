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

st.set_page_config(page_title="资产管理系统 - 终极修复版", layout="wide", initial_sidebar_state="expanded")

# --- 样式定制 ---
st.markdown("""
<style>
    .summary-card { background: #1c1e22; color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 15px; }
    .gold-box { flex: 1; background: #fffcf0; padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #f0e6cc; }
    .gold-price { font-size: 1.2rem; font-weight: bold; color: #b8860b; }
    .fund-card { background: white; padding: 15px; margin-bottom: 12px; border-radius: 12px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .up { color: #e03131 !important; font-weight: bold; }
    .down { color: #2f9e44 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 1. 用户配置管理 ---
def load_config():
    if not os.path.exists(USER_CONFIG_FILE):
        init_cfg = {"users": ["Default"], "current": "Default"}
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(init_cfg, f)
        return init_cfg
    with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(cfg):
    with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False)

def load_user_db(username):
    path = f"db_{username}.json"
    if not os.path.exists(path):
        return {"holdings": []}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_user_db(username, data):
    with open(f"db_{username}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

# --- 2. 核心数据抓取 ---
def fetch_fund_data_final(code):
    try:
        # 强制访问详情页，获取最权威的 3.4470
        url = f"http://fund.eastmoney.com/{code}.html"
        headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/002611'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            
            # 提取名称
            name = re.search(r'<div class="fundDetail-tit">([^<]+)<span>', content).group(1)
            
            # 提取最新价格 (锁定权威 ID)
            price_match = re.search(r'id="gz_gsz">([\d\.]+)<', content)
            # 提取涨跌幅 (锁定权威 ID)
            rate_match = re.search(r'id="gz_gszzl">([\+\-\d\.]+)\%<', content)
            
            if not price_match or not rate_match:
                # 备用匹配逻辑（针对非交易时间标签切换）
                price_match = re.search(r'class="ui-font-large.*?ui-num">([\d\.]+)<', content)
                rate_match = re.search(r'class="ui-num">([\+\-\d\.]+)\%<', content)

            price = float(price_match.group(1))
            rate = float(rate_match.group(1))
            
            return {
                "name": name, "price": price, "rate": rate,
                "last_p": price / (1 + rate/100),
                "time": datetime.now(TZ).strftime("%H:%M:%S")
            }
    except Exception as e:
        return None

def fetch_gold():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
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
            fx = float(m3.group(1).split(',')[1]) if m3 else 7.24
            if d["xau"] > 0: d["cny"] = (d["xau"] * fx) / 31.1035
    except: pass
    return d

# --- 3. UI 交互 ---
cfg = load_config()

with st.sidebar:
    st.header("👤 用户系统")
    # 用户切换
    all_users = cfg["users"]
    current_index = all_users.index(cfg["current"]) if cfg["current"] in all_users else 0
    selected_u = st.selectbox("当前登录账号", all_users, index=current_index)
    
    if selected_u != cfg["current"]:
        cfg["current"] = selected_u
        save_config(cfg)
        st.rerun()

    # 新增用户
    with st.expander("➕ 新增/管理用户"):
        new_user_name = st.text_input("新用户名", key="new_u_input")
        if st.button("确认添加") and new_user_name:
            if new_user_name not in cfg["users"]:
                cfg["users"].append(new_user_name)
                cfg["current"] = new_user_name
                save_config(cfg)
                st.rerun()
    
    st.divider()
    st.caption("🥛 晚上睡前一小时记得喝杯热牛奶")

# --- 4. 主界面逻辑 ---
cur_u = cfg["current"]
db = load_user_db(cur_u)

col1, col2 = st.columns([4, 1])
with col1: st.subheader(f"📈 {cur_u} 的个人资产看板")
with col2: 
    if st.button("🔄 刷新行情", use_container_width=True): st.rerun()

# 黄金价格
g = fetch_gold()
st.markdown(f"""
<div style="display:flex; gap:10px; margin-bottom:15px">
    <div class="gold-box">上海金<br><span class="gold-price">¥{g['au']:.2f}</span></div>
    <div class="gold-box">国际金<br><span class="gold-price">${g['xau']:.2f}</span></div>
    <div class="gold-box">折合价<br><span class="gold-price">¥{g['cny']:.2f}</span></div>
</div>
""", unsafe_allow_html=True)

# 计算持仓
results = []
total_market, total_day = 0.0, 0.0

if db["holdings"]:
    for h in db["holdings"]:
        f = fetch_fund_data_final(h['code'])
        if f:
            shares, cost = float(h['shares']), float(h['cost'])
            day_p = shares * (f['price'] - f['last_p'])
            total_p = shares * (f['price'] - cost)
            total_market += (shares * f['price'])
            total_day += day_p
            results.append({**f, "day_p": day_p, "total_p": total_p, "code": h['code']})

    # 统计看板
    if results:
        p_color = "up" if total_day >= 0 else "down"
        st.markdown(f"""
        <div class="summary-card">
            <div style="font-size:0.9rem; opacity:0.8">预估总市值 (CNY)</div>
            <div style="font-size:2rem; font-weight:bold; margin:10px 0">¥{total_market:,.2f}</div>
            <div style="font-size:1.1rem">今日盈亏：<span class="{p_color}">{total_day:+.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)

        for f in results:
            r_cls = "up" if f['rate'] >= 0 else "down"
            t_cls = "up" if f['total_p'] >= 0 else "down"
            st.markdown(f"""
            <div class="fund-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px">
                    <span style="font-weight:bold; font-size:1.1rem">{f['name']}</span>
                    <span style="color:#888; font-size:0.8rem">{f['time']} 更新</span>
                </div>
                <div style="display:flex; justify-content:space-between; text-align:center">
                    <div style="flex:1">当前价<br><span class="{r_cls}">{f['price']:.4f}</span><br><small class="{r_cls}">{f['rate']:+.2f}%</small></div>
                    <div style="flex:1">今日盈亏<br><span class="{r_cls}">{f['day_p']:+.2f}</span></div>
                    <div style="flex:1">累计盈亏<br><span class="{t_cls}">{f['total_p']:+.2f}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("💡 尚未添加持仓数据。")

# --- 5. 管理持仓 ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("⚙️ 管理持仓数据 (提交后自动刷新)", expanded=not db["holdings"]):
    with st.form("fund_manage_form", clear_on_submit=True):
        f_code = st.text_input("基金代码 (如 002611)")
        f_shares = st.number_input("持有份额", value=None)
        f_cost = st.number_input("单位成本", value=None)
        
        c1, c2 = st.columns(2)
        if c1.form_submit_button("💾 保存并刷新", type="primary", use_container_width=True):
            if f_code and f_shares is not None:
                # 过滤掉旧的同代码持仓并添加新的
                db["holdings"] = [x for x in db["holdings"] if x["code"] != f_code]
                db["holdings"].append({"code": f_code, "shares": f_shares, "cost": f_cost if f_cost else 0.0})
                save_user_db(cur_u, db)
                st.rerun() # 提交后立即刷新

        if c2.form_submit_button("🗑️ 删除持仓", use_container_width=True):
            if f_code:
                db["holdings"] = [x for x in db["holdings"] if x["code"] != f_code]
                save_user_db(cur_u, db)
                st.rerun()
