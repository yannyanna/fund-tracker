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

st.set_page_config(page_title="资产管理 - 精准校准版", layout="wide")

# --- 增强样式 ---
st.markdown("""
<style>
    .summary-card { background: #1c1e22; color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 15px; }
    .gold-box { flex: 1; background: #fffcf0; padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #f0e6cc; }
    .gold-price { font-size: 1.2rem; font-weight: bold; color: #b8860b; }
    .fund-card { background: white; padding: 15px; margin-bottom: 12px; border-radius: 12px; border: 1px solid #eee; }
    .up { color: #e03131 !important; font-weight: bold; }
    .down { color: #2f9e44 !important; font-weight: bold; }
    .source-tag { font-size: 0.65rem; background: #f0f2f6; padding: 2px 5px; border-radius: 4px; color: #666; }
</style>
""", unsafe_allow_html=True)

# --- 1. 用户配置 ---
def load_cfg():
    if not os.path.exists(USER_CONFIG_FILE):
        d = {"users": ["Default"], "current": "Default"}
        with open(USER_CONFIG_FILE, 'w') as f: json.dump(d, f)
        return d
    with open(USER_CONFIG_FILE, 'r') as f: return json.load(f)

def save_cfg(c):
    with open(USER_CONFIG_FILE, 'w') as f: json.dump(c, f)

# --- 2. 强力爬虫 (直取 3.4470) ---
def fetch_fund_data_ultra(code):
    try:
        url = f"http://fund.eastmoney.com/{code}.html"
        # 伪装成真实的 PC 浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            
            # 提取名称
            name = re.search(r'<div class="fundDetail-tit">([^<]+)<span>', content).group(1)
            
            # 核心：晚间优先抓取“单位净值”区域，这里才是 3.4470
            # 匹配 3.4470 所在的 dl 标签
            price_box = re.search(r'<dl class="dataItem02">.*?(ui-num">)([\d\.]+)(</span>)', content, re.S)
            rate_box = re.search(r'<dl class="dataItem02">.*?(ui-num">)([\+\-\d\.]+)(%</span>)', content, re.S)
            
            if price_box and rate_box:
                price = float(price_box.group(2))
                rate = float(rate_box.group(2))
                source = "官方确认净值"
            else:
                # 如果是白天，尝试抓取实时估值 ID
                price_gz = re.search(r'id="gz_gsz">([\d\.]+)<', content)
                rate_gz = re.search(r'id="gz_gszzl">([\+\-\d\.]+)\%<', content)
                price = float(price_gz.group(1))
                rate = float(rate_gz.group(1))
                source = "实时估值"

            return {
                "name": name, "price": price, "rate": rate,
                "last_p": price / (1 + rate/100), "source": source
            }
    except Exception as e:
        return None

def fetch_gold_robust():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
    try:
        # 新浪财经接口
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            # 提取上海金
            m_au = re.search(r'gds_AU9999="([\d\.]+)', raw)
            # 提取国际金
            m_xau = re.search(r'hf_XAU="([\d\.]+)', raw)
            # 提取汇率
            m_fx = re.search(r'fx_susdcnh="[^,]+,([\d\.]+)', raw)
            
            if m_au: d["au"] = float(m_au.group(1))
            if m_xau: d["xau"] = float(m_xau.group(1))
            if m_fx:
                fx = float(m_fx.group(1))
                d["cny"] = (d["xau"] * fx) / 31.1035
    except: pass
    return d

# --- 3. 页面逻辑 ---
cfg = load_cfg()
with st.sidebar:
    st.header("👤 账号管理")
    # 修复：确保当前用户在列表中
    if cfg["current"] not in cfg["users"]: cfg["current"] = cfg["users"][0]
    cur_u = st.selectbox("当前登录", cfg["users"], index=cfg["users"].index(cfg["current"]))
    
    if cur_u != cfg["current"]:
        cfg["current"] = cur_u
        save_cfg(cfg)
        st.rerun()
    
    new_u = st.text_input("新增用户名")
    if st.button("添加用户") and new_u:
        if new_u not in cfg["users"]:
            cfg["users"].append(new_u)
            cfg["current"] = new_u
            save_cfg(cfg)
            st.rerun()
    st.divider()
    st.caption("🥛 睡前一小时记得喝杯热牛奶")

db_path = f"db_{cur_u}.json"
db = {"holdings": []}
if os.path.exists(db_path):
    with open(db_path, 'r', encoding='utf-8') as f: db = json.load(f)

# 主看板
col_h1, col_h2 = st.columns([3, 1])
with col_h1: st.subheader(f"📊 {cur_u} 的资产明细")
with col_h2: 
    if st.button("🔄 刷新数据", type="primary", use_container_width=True): st.rerun()

# 黄金显示
g = fetch_gold_robust()
st.markdown(f"""
<div style="display:flex; gap:10px; margin-bottom:15px">
    <div class="gold-box">上海金<br><span class="gold-price">¥{g['au']:.2f}</span></div>
    <div class="gold-box">国际金<br><span class="gold-price">${g['xau']:.2f}</span></div>
    <div class="gold-box">折合价<br><span class="gold-price">¥{g['cny']:.2f}</span></div>
</div>
""", unsafe_allow_html=True)

results = []
total_market, total_day = 0.0, 0.0

if db["holdings"]:
    for h in db["holdings"]:
        f = fetch_fund_data_ultra(h['code'])
        if f:
            sh, ct = float(h['shares']), float(h['cost'])
            day_p = sh * (f['price'] - f['last_p'])
            total_p = sh * (f['price'] - ct)
            total_market += (sh * f['price'])
            total_day += day_p
            results.append({**f, "day_p": day_p, "total_p": total_p, "code": h['code']})
        else:
            st.error(f"无法抓取基金 {h['code']}，天天基金可能拦截了请求。")

    if results:
        p_color = "up" if total_day >= 0 else "down"
        st.markdown(f'<div class="summary-card"><div style="opacity:0.8">总市值 (CNY)</div><div style="font-size:2.2rem;font-weight:bold">¥{total_market:,.2f}</div><div style="margin-top:10px">今日盈亏：<span class="{p_color}">{total_day:+.2f}</span></div></div>', unsafe_allow_html=True)
        for f in results:
            r_c = "up" if f['rate'] >= 0 else "down"
            t_c = "up" if f['total_p'] >= 0 else "down"
            st.markdown(f"""
            <div class="fund-card">
                <div style="display:flex;justify-content:space-between">
                    <b>{f['name']}</b>
                    <span class="source-tag">{f['source']}</span>
                </div>
                <div style="display:flex;justify-content:space-between;text-align:center;margin-top:10px">
                    <div style="flex:1">当前价<br><span class="{r_c}">{f['price']:.4f}</span><br><small class="{r_c}">{f['rate']:+.2f}%</small></div>
                    <div style="flex:1">今日盈亏<br><span class="{r_c}">{f['day_p']:+.2f}</span></div>
                    <div style="flex:1">持仓盈亏<br><span class="{t_c}">{f['total_p']:+.2f}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# 管理持仓
st.divider()
with st.expander("⚙️ 管理我的持仓", expanded=True):
    with st.form("edit_form", clear_on_submit=True):
        m_code = st.text_input("基金代码")
        m_shares = st.number_input("持有份额", value=None)
        m_cost = st.number_input("单位成本", value=None)
        if st.form_submit_button("💾 保存并刷新", type="primary"):
            if m_code and m_shares is not None:
                db["holdings"] = [x for x in db["holdings"] if x["code"] != m_code]
                db["holdings"].append({"code": m_code, "shares": m_shares, "cost": m_cost if m_cost else 0.0})
                with open(db_path, 'w', encoding='utf-8') as f: json.dump(db, f)
                st.rerun()
