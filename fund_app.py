import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime
import time
import json
import os

st.set_page_config(page_title="基金收益追踪", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.main{padding:0.5rem 1rem}
.fund-card{background:#fff;padding:12px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:10px;border-left:4px solid #3498db}
.positive{color:#e74c3c;font-weight:bold}
.negative{color:#27ae60;font-weight:bold}
.update-time{color:#95a5a6;font-size:11px;text-align:center;margin-top:15px}
#MainMenu,footer,header{visibility:hidden}
</style>
""", unsafe_allow_html=True)

DATA_FILE="fund_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,'r',encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return{"holdings":[{"code":"000001","name":"华夏成长混合","shares":5000,"cost":1.2345}]}

def save_data(data):
    with open(DATA_FILE,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

if'data'not in st.session_state:
    st.session_state.data=load_data()

@st.cache_data(ttl=60)
def get_fund_data(codes):
    data_list=[]
    for code in codes:
        try:
            df=ak.fund_open_fund_info_em(fund=code,indicator="单位净值走势")
            if not df.empty:
                latest=df.iloc[-1]
                prev=df.iloc[-2] if len(df)>1 else latest
                nav=float(latest['单位净值'])
                prev_nav=float(prev['单位净值'])
                growth=((nav-prev_nav)/prev_nav)*100 if prev_nav>0 else 0
                
                try:
                    info=ak.fund_individual_basic_info_xq(symbol=code)
                    name=info['name'].values[0] if not info.empty else f'基金{code}'
                except:
                    name=f'基金{code}'
                
                data_list.append({
                    'code':code,
                    'name':name,
                    'nav':nav,
                    'growth':growth,
                    'last':prev_nav
                })
        except Exception as e:
            st.error(f'获取基金{code}失败')
    return pd.DataFrame(data_list)

st.title("📱基金收益追踪")

with st.expander("➕添加基金"):
    c1,c2,c3=st.columns(3)
    with c1:
        code=st.text_input("基金代码",placeholder="如:000001")
    with c2:
        shares=st.number_input("持有份额",min_value=0.0,value=1000.0,step=100.0)
    with c3:
        cost=st.number_input("成本价",min_value=0.0001,value=1.0,step=0.0001,format="%.4f")
    if st.button("添加",type="primary")and code:
        try:
            info=ak.fund_individual_basic_info_xq(symbol=code)
            name=info['name'].values[0]if not info.empty else f"基金{code}"
            st.session_state.data['holdings'].append({'code':code,'name':name,'shares':shares,'cost':cost})
            save_data(st.session_state.data)
            st.success(f"已添加{name}")
            time.sleep(1)
            st.rerun()
        except:
            st.error("基金代码错误")

holdings=st.session_state.data['holdings']
if not holdings:
    st.info("请添加基金")
    st.stop()

codes=[h['code']for h in holdings]
fund_df=get_fund_data(tuple(codes))

if fund_df.empty:
    st.warning("获取数据中...")
    st.stop()

total_cost=total_value=0
results=[]

for h in holdings:
    row=fund_df[fund_df['code']==h['code']]
    if not row.empty:
        nav=row['nav'].values[0]
        growth=row['growth'].values[0]
        mv=h['shares']*nav
        c=h['shares']*h['cost']
        p=mv-c
        total_cost+=c
        total_value+=mv
        results.append({
            'name':h['name'],'code':h['code'],'nav':nav,'growth':growth,
            'mv':mv,'profit':p,'rate':(p/c)*100 if c>0 else 0
        })

profit=total_value-total_cost
c1,c2,c3=st.columns(3)
c1.metric("总资产",f"¥{total_value:,.2f}")
c2.metric("总收益",f"¥{profit:,.2f}",f"{(profit/total_cost)*100:.2f}%"if total_cost else"0%")
c3.metric("总成本",f"¥{total_cost:,.2f}")

st.markdown("---")

for r in results:
    gc="positive"if r['growth']>=0 else"negative"
    pc="positive"if r['profit']>=0 else"negative"
    st.markdown(f"""
    <div class="fund-card">
        <div style="display:flex;justify-content:space-between;">
            <div>
                <div style="font-weight:bold;">{r['name']}</div>
                <div style="font-size:12px;color:#666;">{r['code']}|成本¥{next(h['cost']for h in holdings if h['code']==r['code']):.4f}</div>
            </div>
            <div style="text-align:right;">
                <div class="{pc}" style="font-size:18px;font-weight:bold;">¥{r['profit']:,.2f}</div>
                <div class="{pc}" style="font-size:13px;">{r['rate']:+.2f}%</div>
            </div>
        </div>
        <div style="margin-top:8px;font-size:13px;color:#555;">
            净值:<span class="{gc}">¥{r['nav']:.4f}({r['growth']:+.2f}%)</span>|市值:¥{r['mv']:,.2f}
        </div>
    </div>
    """,unsafe_allow_html=True)

with st.expander("🗑️管理持仓"):
    for h in holdings:
        if st.button(f"删除{h['name']}",key=f"del_{h['code']}"):
            st.session_state.data['holdings']=[x for x in holdings if x['code']!=h['code']]
            save_data(st.session_state.data)
            st.rerun()

st.markdown(f"""
<div class="update-time">
    更新于:{datetime.now().strftime('%H:%M:%S')}|30秒后自动刷新<br><small>估值仅供参考</small>
</div>
""",unsafe_allow_html=True)

time.sleep(30)
st.rerun()
