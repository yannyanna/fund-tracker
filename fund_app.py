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
    
    /* 黄金看板 */
    .gold-row { display: flex; gap: 6px; margin-bottom: 12px; }
    .gold-box {
        flex: 1; background: linear-gradient(135deg, #fffdf2 0%, #fff9e6 100%);
        padding: 8px 4px; border-radius: 8px; text-align: center; border: 1px solid #f0e6cc;
    }
    .gold-price { font-size: 1.1rem; font-weight: bold; color: #b8860b; }

    /* 基金卡片 */
    .fund-card {
        background: white; padding: 12px; margin-bottom: 10px;
        border-radius: 10px; border: 1px solid #eee;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .fund-header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #f0f0f0; padding-bottom: 5px; margin-bottom: 5px; }
    .fund-name { font-size: 1rem; font-weight: bold; color: #333; }
    .fund-code { font-size: 0.75rem; color: #888; background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
    .fund-date { font-size: 0.7rem; color: #aaa; }
    
    .fund-grid { display: flex; justify-content: space-between; text-align: center; margin-top: 8px; }
    .fund-item { flex: 1; }
    .fund-label { font-size: 0.65rem; color: #999; margin-bottom: 2px; }
    .fund-value { font-size: 0.9rem; font-weight: 600; }
    .fund-sub { font-size: 0.65rem; color: #bbb; }
    
    .up { color: #e03131; } .down { color: #2f9e44; }
    
    /* 底部管理区：强制左右对齐 */
    .admin-section {
        margin-top: 20px; padding: 15px; background: #f8f9fa;
        border-top: 2px solid #ddd; border-radius: 15px 15px 0 0;
    }
    div[data-testid="column"] { display: flex; align-items: center; } 
    .input-label { width: 100%; text-align: right; padding-right: 10px; font-weight: bold; font-size: 0.9rem; color: #333; }
    
    /* 修复表单内按钮样式 */
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 状态管理 ---
if 'admin_expanded' not in st.session_state:
    st.session_state.admin_expanded = True

# --- 数据处理（已修复语法错误） ---
def load_config():
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"users": ["Default"], "current": "Default"}

def save_config(cfg):
    with open(USER_CONFIG_FILE, 'w') as f:
        json.dump(cfg, f)

def get_db(username):
    path = f"db_{username}.json"
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"holdings": []}

def save_db(username, data):
    with open(f"db_{username}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_gold():
    d = {"au": 0.0, "xau": 0.0, "cny": 0.0}
    try:
        url = "http://hq.sinajs.cn/list=gds_AU9999,hf_XAU,fx_susdcnh"
        req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            raw = res.read().decode('gbk')
            m1 = re.search(r'gds_AU9999="([^"]+)"', raw)
            m2 = re.search(r'hf_XAU="([^"]+)"', raw)
            m3 = re.search(r'fx_susdcnh="([^"]+)"', raw)
            if m1: d["au"] = float(m1.group(1).split(',')[0])
            if m2: d["xau"] = float(m2.group(1).split(',')[0])
            fx = float(m3.group(1).split(',')[1]) if m3 else 0
            if d["xau"] > 0 and fx > 0: d["cny"] = (d["xau"] * fx) / 31.1035
    except: pass
    return d

def fetch_fund_realtime(code):
    try:
        ts = int(datetime.now().timestamp() * 1000)
        url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
        req = urllib.request.Request(url, headers={'Referer': 'http://fund.eastmoney.com'})
        with urllib.request.urlopen(req, timeout=3, context=ssl_ctx) as res:
            content = res.read().decode('utf-8')
            json_str = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_str)
            return {
                "name": data['name'],
                "nav": float(data['dwjz']),
                "est": float(data['gsz']),
                "rate": float(data['gszzl']),
                "time": data['gztime']
            }
    except: return None

# --- 侧边栏 ---
config = load_config()
with st.sidebar:
    st.subheader("👤 账号切换")
    cur_u = st.selectbox("当前用户", config["users"], index=config["users"].index(config["current"]) if config["current"] in config["users"] else 0)
    if cur_u != config["current"]:
        config["current"] = cur_u
        save_config(config)
        st.session_state.admin_expanded = True
        st.rerun()
    
    with st.expander("管理用户"):
        new_u = st.text_input("新增用户")
        if st.button("添加") and new_u and new_u not in config["users"]:
            config["users"].append(new_u)
            save_config(config)
            st.rerun()
        del_u = st.selectbox("删除用户", [u for u in config["users"] if u != "Default"])
        if st.button("删除"):
            config["users"].remove(del_u)
            if config["current"] == del_u: config["current"] = "Default"
            save_config(config)
            st.rerun()
    st.divider()
    st.caption("🥛 睡前一小时记得喝杯热牛奶")

# --- 主页面 ---
st.markdown('<div class="spacer-top"></div>', unsafe_allow_html=True)
db = get_db(cur_u)

# 1. 刷新按钮
if st.button("🔄 刷新行情", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# 2. 黄金看板
g = fetch_gold()
st.markdown(f"""
<div class="gold-row">
    <div class="gold-box"><div style="font-size:0.6rem;color:#856404">上海金</div><div class="gold-price">¥{g['au']:.2f}</div></div>
    <div class="gold-box"><div style="font-size:0.6rem;color:#856404">国际金</div><div class="gold-price">${g['xau']:.2f}</div></div>
    <div class="gold-box"><div style="font-size:0.6rem;color:#856404">折合价</div><div class="gold-price">¥{g['cny']:.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# 3. 基金持仓
st.write(f"当前用户：**{cur_u}**")
if not db["holdings"]:
    st.info("暂无持仓，请在下方添加")
else:
    for h in db["holdings"]:
        realtime = fetch_fund_realtime(h['code'])
        name = realtime['name'] if realtime else h.get('name', '加载失败')
        est_val = realtime['est'] if realtime else 0
        rate = realtime['rate'] if realtime else 0
        
        shares = float(h['shares'])
        cost = float(h['cost'])
        day_inc = shares * est_val * rate / 100
        hold_inc = (est_val - cost) * shares
        
        c_cls = "up" if rate >= 0 else "down"
        t_cls = "up" if hold_inc >= 0 else "down"
        
        st.markdown(f"""
        <div class="fund-card">
            <div class="fund-header">
                <div><span class="fund-name">{name}</span> <span class="fund-code">{h['code']}</span></div>
                <div class="fund-date">{realtime['time'][-5:] if realtime else '--:--'}</div>
            </div>
            <div class="fund-grid">
                <div class="fund-item">
                    <div class="fund-label">估值</div>
                    <div class="fund-value {c_cls}">{est_val:.4f}</div>
                    <div class="fund-sub {c_cls}">{rate:+.2f}%</div>
                </div>
                <div class="fund-item">
                    <div class="fund-label">当日盈亏</div>
                    <div class="fund-value {c_cls}">{day_inc:+.0f}</div>
                </div>
                <div class="fund-item">
                    <div class="fund-label">累计盈亏</div>
                    <div class="fund-value {t_cls}">{hold_inc:+.0f}</div>
                </div>
                <div class="fund-item">
                    <div class="fund-label">持有份额</div>
                    <div class="fund-value" style="color:#333">{shares:g}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 4. 底部管理区（Form表单版 - 解决输入问题）
st.markdown('<div class="admin-section">', unsafe_allow_html=True)

with st.expander("⚙️ 增减/修改持仓 (点击展开)", expanded=st.session_state.admin_expanded):
    with st.form("fund_manager_form", clear_on_submit=False):
        # 代码行
        r1_c1, r1_c2 = st.columns([1, 4])
        with r1_c1: st.markdown('<div class="input-label">代码</div>', unsafe_allow_html=True)
        with r1_c2: m_code = st.text_input("code", max_chars=6, placeholder="输入6位代码", label_visibility="collapsed")
        
        # 份额行
        r2_c1, r2_c2 = st.columns([1, 4])
        with r2_c1: st.markdown('<div class="input-label">份额</div>', unsafe_allow_html=True)
        with r2_c2: m_shares = st.number_input("shares", value=None, placeholder="0.00", step=100.0, label_visibility="collapsed")
        
        # 成本行
        r3_c1, r3_c2 = st.columns([1, 4])
        with r3_c1: st.markdown('<div class="input-label">成本</div>', unsafe_allow_html=True)
        with r3_c2: m_cost = st.number_input("cost", value=None, placeholder="0.0000", step=0.001, format="%.4f", label_visibility="collapsed")
        
        # 按钮区域
        b1, b2 = st.columns(2)
        with b1:
            submitted_save = st.form_submit_button("💾 保存并收起", type="primary", use_container_width=True)
        with b2:
            submitted_del = st.form_submit_button("🗑️ 删除持仓", use_container_width=True)
            
        # 表单逻辑处理
        if submitted_save:
            if m_code and m_shares is not None:
                info = fetch_fund_realtime(m_code)
                fname = info['name'] if info else "未知基金"
                idx = next((i for i, x in enumerate(db["holdings"]) if x["code"] == m_code), None)
                new_item = {"code": m_code, "name": fname, "shares": m_shares, "cost": m_cost if m_cost else 0.0}
                if idx is not None: db["holdings"][idx] = new_item
                else: db["holdings"].append(new_item)
                save_db(cur_u, db)
                st.toast(f"✅ {fname} 已保存")
                st.session_state.admin_expanded = False
                st.rerun()
            else:
                st.error("请输入代码和份额")

        if submitted_del:
            if m_code:
                new_h = [x for x in db["holdings"] if x["code"] != m_code]
                if len(new_h) < len(db["holdings"]):
                    db["holdings"] = new_h
                    save_db(cur_u, db)
                    st.toast(f"🗑️ 已删除 {m_code}")
                    st.session_state.admin_expanded = False
                    st.rerun()
                else:
                    st.warning("未找到该代码，请检查输入")
            else:
                st.error("请填写要删除的代码")

st.markdown('</div>', unsafe_allow_html=True)
