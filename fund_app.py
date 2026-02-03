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

st.set_page_config(page_title="资产管理 Pro", layout="wide")

# --- 样式 ---
st.markdown("""
<style>
    .summary-card { background: #1c1e22; color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 15px; border-top: 4px solid #b8860b; }
    .gold-box { flex: 1; background: #fffcf0; padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #f0e6cc; }
    .gold-price { font-size: 1.1rem; font-weight: bold; color: #b8860b; }
    .fund-card { background: white; padding: 15px; margin-bottom: 10px; border-radius: 12px; border: 1px solid #eee; }
    .up { color: #e03131 !important; font-weight: bold; }
    .down { color: #2f9e44 !important; font-weight: bold; }
    .time-tag { font-size: 0.75rem; color: #999; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# --- 1. 纯净新浪抓取 ---
def fetch_sina_fund(code):
    try:
        url = f"http://hq.sinajs.cn/list=f_{code}"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('gbk')
            # 这里的正则匹配会直接提取新浪返回的最原始字符串
            match = re.search(r'"([^"]+)"', content)
            if not match: return None
            data = match.group(1).split(',')
            
            if len(data) > 4:
                price = float(data[1])
                last_p = float(data[3])
                date_label = data[4]
                rate = ((price - last_p) / last_p) * 100
                return {
                    "name": data[0], 
                    "price": price, 
                    "rate": rate, 
                    "last_p": last_p, 
                    "date": date_label
                }
    except:
        return None

def fetch_gold_sina():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([\d\.]+)', raw)
            m2 = re.search(r'hf_XAU="([\d\.]+)', raw)
            m3 = re.search(r'fx_susdcnh="[^,]+,([\d\.]+)', raw)
            if m1: d["au"] = float(m1.group(1))
            if m2: d["xau"] = float(m2.group(1))
            if m3 and d["xau"] > 0:
                d["cny"] = (d["xau"] * float(m3.group(1))) / 31.1035
    except: pass
    return d

# --- 2. 持仓与配置 ---
def load_json(p, d):
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f: return json.load(f)
    return d

cfg = load_json(USER_CONFIG_FILE, {"users": ["Default"], "current": "Default"})

with st.sidebar:
    st.header("👤 账户")
    cur_u = st.selectbox("当前", cfg["users"], index=cfg["users"].index(cfg["current"]))
    if cur_u != cfg["current"]:
        cfg["current"] = cur_u
        with open(USER_CONFIG_FILE, 'w') as f: json.dump(cfg, f)
        st.rerun()
    
    with st.expander("账号管理"):
        new_u = st.text_input("新增用户名")
        if st.button("添加用户"):
            if new_u and new_u not in cfg["users"]:
                cfg["users"].append(new_u); cfg["current"] = new_u
                with open(USER_CONFIG_FILE, 'w') as f: json.dump(cfg, f); st.rerun()
    st.divider()
    st.caption("🥛 睡前一小时记得喝杯热牛奶")

db_path = f"db_{cur_u}.json"
db = load_json(db_path, {"holdings": []})

# --- 3. 页面渲染 ---
# 记录点击刷新的时刻
refresh_time = datetime.now(TZ).strftime("%H:%M:%S")

c1, c2 = st.columns([4, 1])
c1.subheader(f"📊 {cur_u} 持仓看板")
if c2.button("🔄 刷新数据", type="primary", use_container_width=True): st.rerun()

# 黄金
g = fetch_gold_sina()
st.markdown(f"""
<div style="display:flex; gap:8px; margin-bottom:5px">
    <div class="gold-box">上海金<br><span class="gold-price">¥{g['au']:.2f}</span></div>
    <div class="gold-box">国际金<br><span class="gold-price">${g['xau']:.2f}</span></div>
    <div class="gold-box">折合价<br><span class="gold-price">¥{g['cny']:.2f}</span></div>
</div>
<div style="text-align:right; margin-bottom:15px"><span class="time-tag">刷新时间: {refresh_time}</span></div>
""", unsafe_allow_html=True)

# 基金列表展示
total_m, total_d = 0.0, 0.0
res_list = []
if db["holdings"]:
    for h in db["holdings"]:
        f = fetch_sina_fund(h['code'])
        if f:
            sh, ct = float(h['shares']), float(h['cost'])
            day_p = sh * (f['price'] - f['last_p'])
            total_m += (sh * f['price']); total_d += day_p
            res_list.append({**f, "day_p": day_p, "code": h['code']})
        else:
            st.warning(f"代码 {h['code']} 抓取失败")

    if res_list:
        color = "up" if total_d >= 0 else "down"
        st.markdown(f'<div class="summary-card">总市值: ¥{total_m:,.2f}<br>今日盈亏: <span class="{color}">{total_d:+.2f}</span></div>', unsafe_allow_html=True)
        for f in res_list:
            c = "up" if f['rate'] >= 0 else "down"
            st.markdown(f"""
            <div class="fund-card">
                <div style="display:flex; justify-content:space-between">
                    <b>{f['name']}</b>
                    <span class="time-tag">{f['date']}</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:10px; text-align:center">
                    <div style="flex:1">净值<br><span class="{c}">{f['price']:.4f}</span></div>
                    <div style="flex:1">涨幅<br><span class="{c}">{f['rate']:+.2f}%</span></div>
                    <div style="flex:1">今日盈亏<br><span class="{c}">{f['day_p']:+.2f}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- 4. 管理面板 ---
st.divider()
col_add, col_del = st.columns(2)

with col_add:
    st.markdown("##### ➕ 新增/修改持仓")
    with st.form("add_form", clear_on_submit=True):
        fc = st.text_input("代码")
        fs = st.number_input("份额", value=None)
        fco = st.number_input("成本", value=None)
        if st.form_submit_button("保存持仓", type="primary"):
            if fc and fs is not None:
                # 过滤掉旧的，添加新的
                db["holdings"] = [x for x in db["holdings"] if x["code"] != fc]
                db["holdings"].append({"code": fc, "shares": fs, "cost": fco if fco else 0.0})
                with open(db_path, 'w', encoding='utf-8') as f: json.dump(db, f)
                st.rerun()

with col_del:
    st.markdown("##### 🗑️ 删除现有持仓")
    # 动态生成当前持仓列表
    current_codes = [h['code'] for h in db["holdings"]]
    del_target = st.selectbox("选择代码", ["请选择"] + current_codes)
    if st.button("确认删除", type="secondary"):
        if del_target != "请选择":
            db["holdings"] = [x for x in db["holdings"] if x["code"] != del_target]
            with open(db_path, 'w', encoding='utf-8') as f: json.dump(db, f)
            st.rerun()
