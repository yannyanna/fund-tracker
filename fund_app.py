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

st.set_page_config(page_title="资产管理 Pro - 自动刷新版", layout="wide", initial_sidebar_state="expanded")

# --- 样式 ---
st.markdown("""
<style>
    .summary-card { background: #212529; color: white; padding: 15px; border-radius: 12px; margin-bottom: 12px; text-align: center; }
    .gold-box { flex: 1; background: #fff9e6; padding: 8px 4px; border-radius: 8px; text-align: center; border: 1px solid #f0e6cc; }
    .gold-price { font-size: 1.1rem; font-weight: bold; color: #b8860b; }
    .fund-card { background: white; padding: 12px; margin-bottom: 10px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .up { color: #e03131 !important; font-weight: bold; }
    .down { color: #2f9e44 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 数据抓取逻辑 ---
def fetch_fund_data_robust(code):
    try:
        # 优先使用精准的网页数据
        url = f"http://fund.eastmoney.com/{code}.html"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            name = re.search(r'<div class="fundDetail-tit">([^<]+)<span>', content).group(1)
            # 兼容不同颜色的净值标签
            price_match = re.search(r'<span class="ui-font-large.*?ui-num">([^<]+)</span>', content)
            # 优先从页面 ID 获取涨幅，确保 6.17% 这种大幅度能抓到
            rate_match = re.search(r'id="gz_gszzl">([^<+-][^<]*)%</span>', content)
            if not rate_match:
                rate_match = re.search(r'ui-font-middle.*?ui-num">([^<+-][^<]*)%</span>', content)
            
            price = float(price_match.group(1))
            rate = float(rate_match.group(1).replace('+', ''))
            return {
                "name": name, "price": price, "rate": rate,
                "last_p": price / (1 + rate/100),
                "time": datetime.now(TZ).strftime("%m-%d %H:%M")
            }
    except:
        # 备选接口
        try:
            url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(datetime.now().timestamp())}"
            req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                data = json.loads(c[c.find('{'):c.rfind('}')+1])
                p, r = float(data['gsz']), float(data['gszzl'])
                return {"name": data['name'], "price": p, "rate": r, "last_p": p / (1 + r/100), "time": data['gztime']}
        except: return None

def fetch_gold():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([^"]+)"', raw); m2 = re.search(r'hf_XAU="([^"]+)"', raw); m3 = re.search(r'fx_susdcnh="([^"]+)"', raw)
            if m1: d["au"] = float(m1.group(1).split(',')[0])
            if m2: d["xau"] = float(m2.group(1).split(',')[0])
            fx = float(m3.group(1).split(',')[1]) if m3 else 7.2
            if d["xau"] > 0: d["cny"] = (d["xau"] * fx) / 31.1035
    except: pass
    return d

# --- 用户系统 ---
def load_json(p, d):
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f: return json.load(f)
    return d

cfg = load_json(USER_CONFIG_FILE, {"users": ["Default"], "current": "Default"})

with st.sidebar:
    st.subheader("👤 用户管理")
    cur_u = st.selectbox("当前登录", cfg["users"], index=cfg["users"].index(cfg["current"]))
    if cur_u != cfg["current"]:
        cfg["current"] = cur_u
        with open(USER_CONFIG_FILE, 'w') as f: json.dump(cfg, f)
        st.rerun()
    st.caption("🥛 睡前一小时记得喝杯热牛奶")

# --- 资产主界面 ---
db_path = f"db_{cur_u}.json"
db = load_json(db_path, {"holdings": []})

col_t1, col_t2 = st.columns([3, 1])
with col_t1: st.subheader(f"📊 {cur_u} 的持仓")
with col_t2: 
    if st.button("🔄 手动刷新", use_container_width=True):
        st.rerun()

# 黄金显示
g = fetch_gold()
st.markdown(f'<div style="display:flex;gap:10px;margin-bottom:15px"><div class="gold-box">上海金<br><span class="gold-price">¥{g["au"]:.2f}</span></div><div class="gold-box">国际金<br><span class="gold-price">${g["xau"]:.2f}</span></div><div class="gold-box">折合价<br><span class="gold-price">¥{g["cny"]:.2f}</span></div></div>', unsafe_allow_html=True)

# 处理显示持仓
results = []
total_market, total_day = 0.0, 0.0

if db["holdings"]:
    for h in db["holdings"]:
        f = fetch_fund_data_robust(h['code'])
        if f:
            shares, cost = float(h['shares']), float(h['cost'])
            day_p = shares * (f['price'] - f['last_p'])
            total_p = shares * (f['price'] - cost)
            total_market += (shares * f['price'])
            total_day += day_p
            results.append({**f, "day_p": day_p, "total_p": total_p, "code": h['code']})

    if results:
        p_color = "up" if total_day >= 0 else "down"
        st.markdown(f'<div class="summary-card"><div style="font-size:0.8rem;opacity:0.8">预估总市值</div><div style="font-size:1.8rem;font-weight:bold">¥{total_market:,.2f}</div><div style="margin-top:10px">今日盈亏：<span class="{p_color}">{total_day:+.2f}</span></div></div>', unsafe_allow_html=True)
        for f in results:
            r_cls = "up" if f['rate'] >= 0 else "down"
            t_cls = "up" if f['total_p'] >= 0 else "down"
            st.markdown(f'<div class="fund-card"><div style="display:flex;justify-content:space-between"><b>{f["name"]}</b> <small>{f["code"]}</small></div><div style="display:flex;justify-content:space-between;text-align:center;margin-top:10px"><div style="flex:1">当前价<br><span class="{r_cls}">{f["price"]:.4f}</span></div><div style="flex:1">今日盈亏<br><span class="{r_cls}">{f["day_p"]:+.2f}</span></div><div style="flex:1">累计盈亏<br><span class="{t_cls}">{f["total_p"]:+.2f}</span></div></div></div>', unsafe_allow_html=True)
else:
    st.info("💡 暂无持仓，请在下方添加。")

# --- 管理区：保存即自动刷新 ---
st.markdown('<hr>', unsafe_allow_html=True)
with st.expander("⚙️ 管理持仓 (提交后自动刷新)", expanded=True):
    with st.form("manage_form", clear_on_submit=True):
        m_code = st.text_input("基金代码 (如 002611)")
        m_shares = st.number_input("持有份额", value=None)
        m_cost = st.number_input("单位成本", value=None)
        
        c1, c2 = st.columns(2)
        if c1.form_submit_button("💾 保存并自动刷新", type="primary", use_container_width=True):
            if m_code and m_shares:
                # 更新持仓
                db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
                db["holdings"].append({"code": m_code, "shares": m_shares, "cost": m_cost if m_cost else 0.0})
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(db, f)
                # 关键：提交保存后立即刷新页面，显示最新计算结果
                st.rerun()
        
        if c2.form_submit_button("🗑️ 删除并刷新", use_container_width=True):
            if m_code:
                db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(db, f)
                st.rerun()
