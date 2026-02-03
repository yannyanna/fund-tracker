import streamlit as st
import json
import os
import urllib.request
import ssl

# --- 1. 基础配置 ---
ssl_ctx = ssl._create_unverified_context()
DATA_FILE = "fund_master.json"

st.set_page_config(page_title="收益追踪 V28", layout="wide")

# --- 2. 稳固的本地存取 ---
def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"Default": []}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if 'db' not in st.session_state:
    st.session_state.db = load_db()

# --- 3. 账户选择 (侧边栏) ---
with st.sidebar:
    u_list = list(st.session_state.db.keys())
    if 'curr_u' not in st.session_state: st.session_state.curr_u = u_list[0]
    selected_user = st.selectbox("账户", u_list, index=u_list.index(st.session_state.curr_u))
    st.session_state.curr_u = selected_user
    
    new_u = st.text_input("新建用户")
    if st.button("创建"):
        if new_u and new_u not in st.session_state.db:
            st.session_state.db[new_u] = []
            save_db(st.session_state.db); st.rerun()

# --- 4. 核心：极速刷新 (解决卡死关键) ---
# 默认不自动抓取，只有点击刷新或第一次运行才抓
if st.button("🔄 刷新", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# --- 5. 极简抓取函数 (设置0.5秒严格超时) ---
@st.cache_data(ttl=600)
def fetch_data(holdings):
    g_p, g_t = "0.00", "--:--"
    # 黄金抓取
    try:
        req = urllib.request.Request("http://hq.sinajs.cn/list=gds_AU9999", headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=0.5, context=ssl_ctx) as res:
            r = res.read().decode('gbk').split('"')[1].split(',')
            g_p, g_t = r[0], r[5]
    except: pass

    f_res = []
    for h in holdings:
        try:
            url = f"http://fundgz.1234567.com.cn/js/{h['code']}.js"
            with urllib.request.urlopen(url, timeout=0.5, context=ssl_ctx) as res:
                c = res.read().decode('utf-8')
                d = json.loads(c[c.find('{'):c.rfind('}')+1])
                f_res.append({
                    "name": d['name'], "code": h['code'], "time": d['gztime'][-8:],
                    "price": float(d['gsz']), "prev": float(d['dwjz']),
                    "ratio": float(d['gszzl']), "shares": h['shares'], "cost": h['cost']
                })
        except:
            # 抓取失败显示保底数据，防止页面崩掉
            f_res.append({"name": "待刷新", "code": h['code'], "time": "--", "price": 0.0, "prev": 0.0, "ratio": 0.0, "shares": h['shares'], "cost": h['cost']})
    return g_p, g_t, f_res

# 获取数据
gp, gt, funds = fetch_data(st.session_state.db[st.session_state.curr_u])

# --- 6. 界面渲染 (简洁美观) ---
st.markdown(f"""
<div style="background:#fffcf0; padding:10px; border-radius:10px; text-align:center; border:1px solid #ffe082; margin-bottom:10px;">
    <span style="font-size:1.5rem; color:#f57f17; font-weight:bold;">¥{gp}</span><br>
    <span style="font-size:0.7rem; color:#999;">AU9999 更新: {gt}</span>
</div>
""", unsafe_allow_html=True)

total_v = sum(f['price'] * f['shares'] for f in funds)
total_dp = sum((f['price'] - f['prev']) * f['shares'] for f in funds)

st.write(f"### 资产: ¥{total_v:,.2f} | 盈亏: {total_dp:+,.2f}")

for f in funds:
    color = "#e74c3c" if f['ratio'] >= 0 else "#27ae60"
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #eee;">
        <div><b>{f['name']}</b><br><small>{f['code']} ({f['time']})</small></div>
        <div style="text-align:right;"><span style="color:{color}; font-weight:bold;">{f['ratio']:+.2f}%</span></div>
    </div>
    """, unsafe_allow_html=True)

# --- 7. 管理区 (保存后立即生效) ---
with st.expander("💼 持仓管理"):
    c1, c2, c3 = st.columns(3)
    a_code = c1.text_input("代码")
    a_share = c2.number_input("份额", value=None)
    a_cost = c3.number_input("成本", value=None)
    if st.button("保存并更新"):
        if a_code and a_share:
            st.session_state.db[st.session_state.curr_u].append({"code": a_code, "shares": a_share, "cost": a_cost or 0.0})
            save_db(st.session_state.db)
            st.cache_data.clear(); st.rerun()

    st.divider()
    for i, h in enumerate(st.session_state.db[st.session_state.curr_u]):
        if st.button(f"删除 {h['code']}", key=f"del_{i}"):
            st.session_state.db[st.session_state.curr_u].pop(i)
            save_db(st.session_state.db)
            st.cache_data.clear(); st.rerun()
