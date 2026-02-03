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

st.set_page_config(page_title="资产管理 - 稳定版", layout="wide", initial_sidebar_state="expanded")

# --- 样式 ---
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

# --- 1. 用户配置逻辑 (确保侧边栏功能) ---
def get_config():
    if not os.path.exists(USER_CONFIG_FILE):
        d = {"users": ["Default"], "current": "Default"}
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(d, f)
        return d
    with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_config(c):
    with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(c, f, ensure_ascii=False)

# --- 2. 基金数据抓取 (改用高稳定性移动接口) ---
def fetch_fund_data_stable(code):
    # 方案 A: 移动端 JSON 接口 (通常不会被屏蔽)
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(datetime.now().timestamp())}"
        headers = {'Referer': 'http://fund.eastmoney.com/'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            text = res.read().decode('utf-8')
            # 提取 jsonp 中的数据
            match = re.search(r'\{.*\}', text)
            if match:
                data = json.loads(match.group(0))
                price = float(data['gsz'])
                rate = float(data['gszzl'])
                return {
                    "name": data['name'], "price": price, "rate": rate,
                    "last_p": price / (1 + rate/100), "time": data['gztime']
                }
    except: pass
    
    # 方案 B: 网页端兜底
    try:
        url = f"http://fund.eastmoney.com/{code}.html"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            name = re.search(r'<div class="fundDetail-tit">([^<]+)<span>', content).group(1)
            # 提取最新价格
            p_match = re.search(r'id="gz_gsz">([\d\.]+)<', content)
            r_match = re.search(r'id="gz_gszzl">([\+\-\d\.]+)\%<', content)
            if p_match:
                price, rate = float(p_match.group(1)), float(r_match.group(1))
                return {"name": name, "price": price, "rate": rate, "last_p": price / (1 + rate/100), "time": "网页数据"}
    except: pass
    return None

def fetch_gold():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([^"]+)"', raw)
            m3 = re.search(r'fx_susdcnh="([^"]+)"', raw)
            if m1: d["au"] = float(m1.group(1).split(',')[0])
            if m3: 
                fx = float(m3.group(1).split(',')[1])
                # 简单估算
                m2 = re.search(r'hf_XAU="([^"]+)"', raw)
                if m2:
                    d["xau"] = float(m2.group(1).split(',')[0])
                    d["cny"] = (d["xau"] * fx) / 31.1035
    except: pass
    return d

# --- 3. 侧边栏交互 ---
cfg = get_config()
with st.sidebar:
    st.header("👤 账号管理")
    cur_u = st.selectbox("当前用户", cfg["users"], index=cfg["users"].index(cfg["current"]))
    
    if cur_u != cfg["current"]:
        cfg["current"] = cur_u
        save_config(cfg)
        st.rerun()
    
    new_user = st.text_input("新增用户名")
    if st.button("添加用户"):
        if new_user and new_user not in cfg["users"]:
            cfg["users"].append(new_user)
            cfg["current"] = new_user
            save_config(cfg)
            st.rerun()
    
    st.divider()
    st.caption("🥛 睡前一小时记得喝杯热牛奶")

# --- 4. 持仓数据逻辑 ---
db_path = f"db_{cur_u}.json"
if not os.path.exists(db_path):
    with open(db_path, 'w', encoding='utf-8') as f: json.dump({"holdings": []}, f)

with open(db_path, 'r', encoding='utf-8') as f:
    db = json.load(f)

# --- 主界面 ---
st.subheader(f"📈 {cur_u} 的资产明细")

# 黄金
g = fetch_gold()
st.markdown(f'<div style="display:flex; gap:10px; margin-bottom:15px"><div class="gold-box">上海金<br><span class="gold-price">¥{g["au"]:.2f}</span></div><div class="gold-box">折合价<br><span class="gold-price">¥{g["cny"]:.2f}</span></div></div>', unsafe_allow_html=True)

results = []
total_m, total_d = 0.0, 0.0

if db["holdings"]:
    with st.spinner('正在获取实时数据...'):
        for h in db["holdings"]:
            f = fetch_fund_data_stable(h['code'])
            if f:
                shares, cost = float(h['shares']), float(h['cost'])
                day_p = shares * (f['price'] - f['last_p'])
                total_p = shares * (f['price'] - cost)
                total_m += (shares * f['price'])
                total_d += day_p
                results.append({**f, "day_p": day_p, "total_p": total_p, "code": h['code']})
            else:
                st.error(f"无法连接到基金 {h['code']} 的数据源，请检查代码或重试。")

    if results:
        p_color = "up" if total_d >= 0 else "down"
        st.markdown(f'<div class="summary-card"><div style="opacity:0.8">总市值</div><div style="font-size:2rem;font-weight:bold">¥{total_m:,.2f}</div><div>今日盈亏：<span class="{p_color}">{total_d:+.2f}</span></div></div>', unsafe_allow_html=True)
        for f in results:
            r_cls = "up" if f['rate'] >= 0 else "down"
            t_cls = "up" if f['total_p'] >= 0 else "down"
            st.markdown(f'<div class="fund-card"><b>{f["name"]}</b> ({f["code"]})<br><div style="display:flex;justify-content:space-between;margin-top:10px;text-align:center"><div style="flex:1">当前价<br><span class="{r_cls}">{f["price"]:.4f}</span></div><div style="flex:1">今日盈亏<br><span class="{r_cls}">{f["day_p"]:+.2f}</span></div><div style="flex:1">累计盈亏<br><span class="{t_cls}">{f["total_p"]:+.2f}</span></div></div></div>', unsafe_allow_html=True)
else:
    st.info("💡 当前账号暂无持仓。请在下方输入代码、份额和成本并保存。")

# --- 5. 管理区 ---
st.divider()
with st.expander("⚙️ 持仓管理", expanded=True):
    with st.form("my_form", clear_on_submit=True):
        c_code = st.text_input("基金代码 (6位)")
        c_shares = st.number_input("持有份额", value=None)
        c_cost = st.number_input("单位成本", value=None)
        
        save_btn = st.form_submit_button("💾 保存并自动刷新", type="primary")
        if save_btn:
            if c_code and c_shares is not None:
                db["holdings"] = [x for x in db["holdings"] if x["code"] != c_code]
                db["holdings"].append({"code": c_code, "shares": c_shares, "cost": c_cost if c_cost else 0.0})
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(db, f, ensure_ascii=False)
                st.rerun()

    del_code = st.text_input("要删除的基金代码")
    if st.button("🗑️ 确认删除"):
        db["holdings"] = [x for x in db["holdings"] if x["code"] != del_code]
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        st.rerun()
