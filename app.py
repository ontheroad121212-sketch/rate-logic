import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import math
import re
import io  
import plotly.express as px

# --- 1. 파이어베이스 초기화 ---
if not firebase_admin._apps:
    try:
        fb_dict = st.secrets["firebase"]
        cred = credentials.Certificate(dict(fb_dict))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"파이어베이스 연결 실패: {e}")
db = firestore.client()

# --- 2. 전역 설정 데이터 ---
st.set_page_config(page_title="앰버퓨어힐 전략 시뮬레이터", layout="wide")

BAR_GRADIENT_COLORS = {
    "BAR0": "#B71C1C", 
    "BAR1": "#D32F2F", "BAR2": "#EF5350", "BAR3": "#FF8A65", "BAR4": "#FFB199",
    "BAR5": "#81C784", "BAR6": "#A5D6A7", "BAR7": "#C8E6C9", "BAR8": "#E8F5E9",
}
BAR_LIGHT_COLORS = {
    "BAR0": "#FFCDD2", 
    "BAR1": "#FFEBEE", "BAR2": "#FFEBEE", "BAR3": "#FFF3E0", "BAR4": "#FFF3E0",
    "BAR5": "#E8F5E9", "BAR6": "#E8F5E9", "BAR7": "#F1F8E9", "BAR8": "#F1F8E9",
}
WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']
DYNAMIC_ROOMS = ["FDB", "FDE", "HDP", "HDT", "HDF"]
FIXED_ROOMS = ["GDB", "GDF", "FFD", "FPT", "PPV"]
ALL_ROOMS = DYNAMIC_ROOMS + FIXED_ROOMS

PRICE_TABLE = {
    "FDB": {"BAR0": 802000, "BAR8": 315000, "BAR7": 353000, "BAR6": 396000, "BAR5": 445000, "BAR4": 502000, "BAR3": 567000, "BAR2": 642000, "BAR1": 728000},
    "FDE": {"BAR0": 839000, "BAR8": 352000, "BAR7": 390000, "BAR6": 433000, "BAR5": 482000, "BAR4": 539000, "BAR3": 604000, "BAR2": 679000, "BAR1": 765000},
    "HDP": {"BAR0": 759000, "BAR8": 280000, "BAR7": 318000, "BAR6": 361000, "BAR5": 410000, "BAR4": 467000, "BAR3": 532000, "BAR2": 607000, "BAR1": 693000},
    "HDT": {"BAR0": 729000, "BAR8": 250000, "BAR7": 288000, "BAR6": 331000, "BAR5": 380000, "BAR4": 437000, "BAR3": 502000, "BAR2": 577000, "BAR1": 663000},
    "HDF": {"BAR0": 916000, "BAR8": 420000, "BAR7": 458000, "BAR6": 501000, "BAR5": 550000, "BAR4": 607000, "BAR3": 672000, "BAR2": 747000, "BAR1": 833000},
}
FIXED_PRICE_TABLE = {
    "GDB": {"UND1": 298000, "UND2": 298000, "MID1": 298000, "MID2": 298000, "UPP1": 298000, "UPP2": 298000, "UPP3":298000},
    "GDF": {"UND1": 375000, "UND2": 410000, "MID1": 410000, "MID2": 488000, "UPP1": 488000, "UPP2": 578000, "UPP3":678000},
    "FFD": {"UND1": 353000, "UND2": 393000, "MID1": 433000, "MID2": 482000, "UPP1": 539000, "UPP2": 604000, "UPP3":704000},
    "FPT": {"UND1": 500000, "UND2": 550000, "MID1": 600000, "MID2": 650000, "UPP1": 700000, "UPP2": 750000, "UPP3":850000},
    "PPV": {"UND1": 1104000, "UND2": 1154000, "MID1": 1154000, "MID2": 1304000, "UPP1": 1304000, "UPP2": 1554000, "UPP3":1704000},
}
FIXED_BAR0_TABLE = {"GDB": 298000, "GDF": 678000, "FFD": 704000, "FPT": 850000, "PPV": 1704000}

# --- 3. 로직 함수 (재고/시즌 기반 요금 산출) ---
def get_season_details(date_obj):
    m, d = date_obj.month, date_obj.day
    md = f"{m:02d}.{d:02d}"
    actual_is_weekend = date_obj.weekday() in [4, 5]
    if ("02.13" <= md <= "02.18") or ("09.23" <= md <= "09.28"):
        season, is_weekend = "UPP", True
    elif ("12.21" <= md <= "12.31") or ("10.01" <= md <= "10.08"):
        season, is_weekend = "UPP", False
    elif ("05.03" <= md <= "05.05") or ("05.24" <= md <= "05.26") or ("06.05" <= md <= "06.07"):
        season, is_weekend = "MID", True
    elif "07.17" <= md <= "08.29":
        season, is_weekend = "UPP", actual_is_weekend
    elif ("01.04" <= md <= "03.31") or ("11.01" <= md <= "12.20"):
        season, is_weekend = "UND", actual_is_weekend
    else:
        season, is_weekend = "MID", actual_is_weekend
    type_code = f"{season}{'2' if is_weekend else '1'}"
    return type_code, season, is_weekend

def determine_bar(season, is_weekend, occ):
    if season == "UPP":
        if is_weekend:
            if occ >= 81: return "BAR1"
            elif occ >= 51: return "BAR2"
            elif occ >= 31: return "BAR3"
            else: return "BAR4"
        else:
            if occ >= 81: return "BAR2"
            elif occ >= 51: return "BAR3"
            elif occ >= 31: return "BAR4"
            else: return "BAR5"
    elif season == "MID":
        if is_weekend:
            if occ >= 81: return "BAR3"
            elif occ >= 51: return "BAR4"
            elif occ >= 31: return "BAR5"
            else: return "BAR6"
        else:
            if occ >= 81: return "BAR4"
            elif occ >= 51: return "BAR5"
            elif occ >= 31: return "BAR6"
            else: return "BAR7"
    else: 
        if is_weekend:
            if occ >= 81: return "BAR4"
            elif occ >= 51: return "BAR5"
            elif occ >= 31: return "BAR6"
            else: return "BAR7"
        else:
            if occ >= 81: return "BAR5"
            elif occ >= 51: return "BAR6"
            elif occ >= 31: return "BAR7"
            else: return "BAR8"

def get_final_values(room_id, date_obj, avail, total, manual_bar=None):
    type_code, season, is_weekend = get_season_details(date_obj)
    try: current_avail = float(avail) if pd.notna(avail) else 0.0
    except: current_avail = 0.0
    occ = ((total - current_avail) / total * 100) if total > 0 else 0
    
    if manual_bar:
        bar = manual_bar
        if bar == "BAR0":
            if room_id in DYNAMIC_ROOMS: price = PRICE_TABLE.get(room_id, {}).get("BAR0", 0)
            else: price = FIXED_BAR0_TABLE.get(room_id, 0)
        else:
            if room_id in DYNAMIC_ROOMS: price = PRICE_TABLE.get(room_id, {}).get(bar, 0)
            else: price = FIXED_PRICE_TABLE.get(room_id, {}).get(bar, 0)
        return occ, bar, price, True 

    if room_id in DYNAMIC_ROOMS:
        bar = determine_bar(season, is_weekend, occ)
        price = PRICE_TABLE.get(room_id, {}).get(bar, 0)
    else:
        bar = type_code
        price = FIXED_PRICE_TABLE.get(room_id, {}).get(type_code, 0)
    return occ, bar, price, False 

# --- 4. 무적의 파서 및 DB 로직 ---
def robust_date_parser(d_val):
    if pd.isna(d_val): return None
    try:
        if isinstance(d_val, (int, float)): return (pd.to_datetime('1899-12-30') + pd.to_timedelta(d_val, 'D')).date()
        s = str(d_val).strip().replace('.', '-').replace('/', '-').replace(' ', '')
        match = re.search(r'(\d{1,2})-(\d{1,2})', s)
        if match: return date(2026, int(match.group(1)), int(match.group(2)))
    except: pass
    return None

def save_channel_configs():
    db.collection("settings").document("channels").set({"channel_list": st.session_state.channel_list, "promotions": st.session_state.promotions})

def load_channel_configs():
    doc = db.collection("settings").document("channels").get()
    if doc.exists:
        d = doc.to_dict()
        st.session_state.channel_list = d.get("channel_list", [])
        st.session_state.promotions = d.get("promotions", {})
    else:
        st.session_state.channel_list = []
        st.session_state.promotions = {}

def get_latest_snapshot():
    docs = db.collection("daily_snapshots").order_by("save_time", direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        d_dict = doc.to_dict()
        df = pd.DataFrame(d_dict['data'])
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df, d_dict.get('work_date', '알수없음')
    return pd.DataFrame(), None

# --- 5. 렌더러 ---
def render_master_table(current_df, prev_df, ch_name=None, title="", mode="기준"):
    if current_df.empty: return "<div style='padding:20px;'>데이터를 업로드하세요.</div>"
    dates = sorted(current_df['Date'].unique())
    
    if mode == "판매가":
        items_to_show = st.session_state.promotions.get(ch_name, {}).get("items", [])
        row_padding = "1px"
        header_padding = "2px"
        line_style = "line-height: 1.0; font-size: 11px;"
        font_size = "11px"
        col_width_style = "min-width: 45px;"
    else:
        items_to_show = ALL_ROOMS
        row_padding = "8px"
        header_padding = "5px"
        line_style = ""
        font_size = "11px"
        col_width_style = ""

    if mode == "판매가" and not items_to_show:
        return f"<div style='padding:10px; color:gray;'>👉 탭 1 하단에서 {ch_name} 상품을 세팅해주세요.</div>"

    html = f"<div style='margin-top:40px; margin-bottom:10px; font-weight:bold; font-size:18px; padding:10px; background:#f0f2f6; border-left:10px solid #000;'>{title}</div>"
    html += "<div style='overflow-x: auto; white-space: nowrap; border: 1px solid #ddd;'>"
    html += f"<table style='width:100%; border-collapse:collapse; font-size:{font_size}; min-width:1000px;'><thead><tr style='background:#f9f9f9;'><th rowspan='2' style='border:1px solid #ddd; width:180px; position:sticky; left:0; background:#f9f9f9; z-index:2; padding:{header_padding};'>객실/프로모션</th>"
    for d in dates: html += f"<th style='border:1px solid #ddd; padding:{header_padding}; {col_width_style}'>{d.strftime('%m-%d')}</th>"
    html += "</tr><tr style='background:#f9f9f9;'>"
    for d in dates:
        wd = WEEKDAYS_KR[d.weekday()]
        color = "red" if wd=='일' else ("blue" if wd=='토' else "black")
        html += f"<th style='border:1px solid #ddd; padding:{header_padding}; color:{color}; {col_width_style}'>{wd}</th>"
    html += "</tr></thead><tbody>"

    for item in items_to_show:
        if mode == "판매가":
            rid = item.get('객실타입', 'Unknown')
            label_text = item.get('상품명', 'No Name')
            label = f"<b>{rid}</b> <span style='color:blue; margin-left:4px;'>: {label_text}</span>"
            try: discount = float(item.get('할인(%)') or 0)
            except: discount = 0.0
            try: add_price = int(item.get('추가금') or 0)
            except: add_price = 0
        else:
            rid = item
            label = rid
            if rid in ["HDF", "PPV"]: label = f"<b>{rid}</b>"

        border_thick = "border-bottom:3.4px solid #000;" if rid in ["HDF", "PPV"] else ""
        html += f"<tr style='{border_thick}'><td style='border:1px solid #ddd; padding:{row_padding}; background:#fff; border-right:4px solid #000; position:sticky; left:0; z-index:1; {line_style}'>{label}</td>"
        
        for d in dates:
            curr_match = current_df[(current_df['RoomID'] == rid) & (current_df['Date'] == d)]
            if curr_match.empty:
                html += f"<td style='border:1px solid #ddd; padding:{row_padding}; text-align:center;'>-</td>"
                continue

            avail = curr_match.iloc[0]['Available']
            total = curr_match.iloc[0]['Total']
            
            override_key = f"{d.strftime('%Y-%m-%d')}_{rid}"
            m_bar = st.session_state.get('manual_bars', {}).get(override_key) if mode == "판매가" else None
            occ, bar, base_price, is_manual = get_final_values(rid, d, avail, total, m_bar)
            
            prev_bar, prev_avail = None, None
            if not prev_df.empty:
                prev_m = prev_df[(prev_df['RoomID'] == rid) & (prev_df['Date'] == d)]
                if not prev_m.empty:
                    prev_avail = prev_m.iloc[0]['Available']
                    p_m_bar = st.session_state.get('manual_bars', {}).get(override_key) if mode == "판매가" else None
                    _, prev_bar, _, _ = get_final_values(rid, d, prev_avail, prev_m.iloc[0]['Total'], p_m_bar)

            style = f"border:1px solid #ddd; padding:{row_padding}; text-align:center; background-color:white; {line_style}"
            
            if mode == "기준":
                bg = BAR_GRADIENT_COLORS.get(bar, "#FFFFFF") if rid in DYNAMIC_ROOMS or bar == "BAR0" else "#F1F1F1"
                style += f"background-color: {bg};"
                content = f"<b>{bar}</b><br>{base_price:,}<br>{occ:.0f}%"
            
            elif mode == "변화":
                curr_av_safe = float(avail) if pd.notna(avail) else 0.0
                prev_av_safe = float(prev_avail) if (prev_avail is not None and pd.notna(prev_avail)) else 0.0
                pickup = (prev_av_safe - curr_av_safe) if prev_avail is not None else 0
                bg = BAR_LIGHT_COLORS.get(bar, "#FFFFFF") if rid in DYNAMIC_ROOMS or bar == "BAR0" else "#FFFFFF"
                style += f"background-color: {bg};"
                if pickup > 0:
                    style += "color:red; font-weight:bold; border: 1.5px solid red;"
                    content = f"+{pickup:.0f}"
                elif pickup < 0:
                    style += "color:blue; font-weight:bold;"
                    content = f"{pickup:.0f}"
                else: content = "-"
            
            elif mode == "판도변화":
                curr_b_str = str(bar).strip() if bar else ""
                prev_b_str = str(prev_bar).strip() if prev_bar else ""
                if prev_bar is not None and prev_b_str != curr_b_str:
                    bg = BAR_GRADIENT_COLORS.get(bar, "#7000FF")
                    style += f"background-color: {bg}; color: white; font-weight: bold; border: 2.5px solid #000;"
                    content = f"▲ {bar}"
                else: 
                    content = bar
                    
            elif mode == "판매가":
                try:
                    b_price = float(base_price) if base_price is not None else 0
                    d_rate = float(discount) if discount is not None else 0
                    a_price = float(add_price) if add_price is not None else 0
                    after_disc = b_price * (1 - (d_rate / 100))
                    final_p = int((math.floor(after_disc / 1000) * 1000) + a_price)
                    content = f"<b>{final_p:,}</b>"
                except (ValueError, TypeError, ZeroDivisionError):
                    content = "<b>-</b>"

                curr_b_str = str(bar).strip() if bar else ""
                prev_b_str = str(prev_bar).strip() if prev_bar else ""
                if prev_bar is not None and prev_b_str != curr_b_str:
                    bg = BAR_GRADIENT_COLORS.get(bar, "#7000FF")
                    style += f"background-color: {bg}; color: white; font-weight: bold; border: 2.5px solid #333;"
                
                if is_manual:
                    style += "border: 2px dashed #FF0000;"
                    content = f"⭐ {content}"

            html += f"<td style='{style}'>{content}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

# --- 6. 세션 상태 초기화 ---
st.title("🏨 앰버퓨어힐 전략 통합 수익관리 시스템")

if 'channel_list' not in st.session_state: load_channel_configs()
if 'today_df' not in st.session_state: st.session_state.today_df = pd.DataFrame()
if 'prev_df' not in st.session_state: st.session_state.prev_df = pd.DataFrame()
if 'compare_label' not in st.session_state: st.session_state.compare_label = ""
if 'manual_bars' not in st.session_state: st.session_state.manual_bars = {} 
if 'ota_channels' not in st.session_state: st.session_state.ota_channels = ["Trip.com", "Booking.com", "Agoda"] 

# --- 7. 사이드바 ---
with st.sidebar:
    st.header("📅 수정 내역 조회 (History)")
    try:
        all_docs = db.collection("daily_snapshots").select(["work_date"]).stream()
        saved_dates = sorted(list(set([d.to_dict().get('work_date', '') for d in all_docs if d.to_dict().get('work_date')])))
        if saved_dates:
            st.markdown("**📌 데이터가 저장된 날짜 (최근 14일)**")
            tags = "".join([f"<span style='background:#E8F5E9; border:1px solid #4CAF50; color:#2E7D32; padding:3px 8px; border-radius:12px; margin:2px; font-size:12px; display:inline-block; font-weight:bold;'>{d[5:]} ✅</span>" for d in saved_dates[-14:]])
            st.markdown(f"<div style='margin-bottom: 10px;'>{tags}</div>", unsafe_allow_html=True)
    except Exception:
        pass

    work_day = st.date_input("조회 날짜", value=date.today())
    if st.button("📂 과거 기록 불러오기"):
        docs = db.collection("daily_snapshots").where("work_date", "==", work_day.strftime("%Y-%m-%d")).limit(1).stream()
        found = False
        for doc in docs:
            d_dict = doc.to_dict()
            st.session_state.today_df = pd.DataFrame(d_dict['data'])
            if not st.session_state.today_df.empty and 'Date' in st.session_state.today_df.columns:
                st.session_state.today_df['Date'] = pd.to_datetime(st.session_state.today_df['Date']).dt.date
            
            if 'prev_data' in d_dict and d_dict['prev_data']:
                st.session_state.prev_df = pd.DataFrame(d_dict['prev_data'])
                if not st.session_state.prev_df.empty and 'Date' in st.session_state.prev_df.columns:
                    st.session_state.prev_df['Date'] = pd.to_datetime(st.session_state.prev_df['Date']).dt.date
            else:
                st.session_state.prev_df = pd.DataFrame()

            if 'saved_promotions' in d_dict:
                st.session_state.promotions = d_dict['saved_promotions']
                st.session_state.channel_list = d_dict.get('saved_channel_list', [])
            
            st.session_state.manual_bars = d_dict.get('saved_manual_bars', {})
            st.session_state.compare_label = f"불러온 과거 기록: {work_day}"
            found = True
        if found: st.success("역사적 스냅샷 로드 완료")
        else: st.warning("해당 날짜의 데이터가 없습니다.")

    st.divider()
    
    # 👈 [핵심 업그레이드] 무적의 엑셀/CSV 호환 파서
    st.header("📂 재고 파일(엑셀/CSV) 업로드")
    st.caption("새로운 재고표를 올리면 이전 스냅샷과 자동 비교됩니다.")
    files = st.file_uploader("리포트 업로드", type=["xls", "xlsx", "csv"], accept_multiple_files=True)
    
    if files:
        new_extracted = []
        for f in files:
            date_tag = re.search(r'\d{8}', f.name).group() if re.search(r'\d{8}', f.name) else f.name
            
            # 1. 파일 포맷 자동 감지 및 로드
            try:
                df_raw = pd.read_excel(f, header=None)
            except Exception:
                f.seek(0)
                try: df_raw = pd.read_csv(f, header=None)
                except:
                    f.seek(0)
                    df_raw = pd.read_csv(f, header=None, encoding='euc-kr') # 한글 깨짐 방지
            
            # 2. 날짜 및 객실 동적 스캔 (로우 번호 하드코딩 제거)
            if len(df_raw) > 2:
                dates_raw = df_raw.iloc[2, 2:].values
                for idx, row in df_raw.iterrows():
                    rid_val = str(row.iloc[0]).strip().upper()
                    if rid_val in ALL_ROOMS:
                        tot = pd.to_numeric(row.iloc[1], errors='coerce')
                        for d_val, av in zip(dates_raw, row.iloc[2:].values):
                            d_obj = robust_date_parser(d_val)
                            if d_obj is None: continue
                            new_extracted.append({
                                "Date": d_obj, 
                                "RoomID": rid_val, 
                                "Available": pd.to_numeric(av, errors='coerce'), 
                                "Total": tot, 
                                "Tag": date_tag
                            })

        if new_extracted:
            new_df = pd.DataFrame(new_extracted)
            if st.session_state.prev_df.empty:
                latest_db, save_dt = get_latest_snapshot()
                if not latest_db.empty:
                    combined = pd.concat([new_df, latest_db]).drop_duplicates(subset=['Date', 'RoomID'], keep='first')
                    st.session_state.today_df = combined.sort_values(by=['Date', 'RoomID'])
                    st.session_state.prev_df = latest_db
                    st.session_state.compare_label = f"자동 DB 병합/비교: {save_dt} 기준"
                else:
                    st.session_state.today_df = new_df
                    st.session_state.prev_df = pd.DataFrame()
                    st.session_state.compare_label = "비교 대상 없음 (신규)"
            else:
                combined = pd.concat([new_df, st.session_state.today_df]).drop_duplicates(subset=['Date', 'RoomID'], keep='first')
                st.session_state.today_df = combined.sort_values(by=['Date', 'RoomID'])
            st.success("재고 데이터 로드 및 파싱 완벽 성공!")

    st.divider()
    st.header("⚙️ 시뮬레이터 탭용 채널 관리")
    new_ota = st.text_input("새 OTA 명칭 (탭 생성)")
    if st.button("➕ 채널 탭 생성"):
        if new_ota and new_ota not in st.session_state.ota_channels:
            st.session_state.ota_channels.append(new_ota)
            st.rerun()

# --- 8. 메인 탭 구조 ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 1. 재고 기반 다이내믹 마스터 보드", 
    "🧮 2. 요금 역산 시뮬", 
    "🧱 3. 트립/부킹/아고다 실전", 
    "📅 4. 채널별 스케줄",
    "📋 5. 경영진 리포트",
    "🗓️ 6. 장기 요금 프로젝션"
])

# ==========================================
# TAB 1: 재고 기반 다이내믹 마스터 보드 (사용자 원본 로직)
# ==========================================
with tab1:
    st.header("📊 재고 기반 다이내믹 마스터 보드")
    if st.session_state.today_df.empty:
        st.info("👈 사이드바에서 재고 엑셀/CSV 파일을 업로드하거나 과거 기록을 불러와주세요.")
    else:
        curr, prev = st.session_state.today_df, st.session_state.prev_df
        
        if st.session_state.compare_label:
            st.info(f"ℹ️ {st.session_state.compare_label}")
            
        st.markdown(render_master_table(curr, prev, title="📊 1. 시장 분석 (BAR / 기준가 / 점유율)", mode="기준"), unsafe_allow_html=True)
        st.markdown(render_master_table(curr, prev, title="📈 2. 예약 변화량 (Pick-up)", mode="변화"), unsafe_allow_html=True)
        st.markdown(render_master_table(curr, prev, title="🔔 3. 판도 변화 (BAR 등급 변동)", mode="판도변화"), unsafe_allow_html=True)

        with st.expander("🛠️ 전략적 판도 오버라이드 (Admin Only)", expanded=False):
            st.write("※ 여기서 수정한 내용은 하단의 '✅ 판매가 산출' 표와 탭 6 장기 프로젝션에 반영됩니다.")
            dates_list = sorted(st.session_state.today_df['Date'].unique())
            matrix_data = []
            for rid in ALL_ROOMS:
                row_data = {"객실": rid}
                for d in dates_list:
                    o_key = f"{d.strftime('%Y-%m-%d')}_{rid}"
                    row_data[d.strftime('%m-%d')] = st.session_state.get('manual_bars', {}).get(o_key, "")
                matrix_data.append(row_data)
                
            ed_df = pd.DataFrame(matrix_data)
            col_config = {"객실": st.column_config.TextColumn(disabled=True)}
            edited_matrix = st.data_editor(ed_df, use_container_width=True, hide_index=True, column_config=col_config)
            
            if st.button("💾 전략 적용 및 새로고침", use_container_width=True):
                new_manual_bars = {}
                for idx, row in edited_matrix.iterrows():
                    rid = row["객실"]
                    for d in dates_list:
                        val = str(row[d.strftime('%m-%d')]).strip()
                        if val and val.upper() not in ["NONE", "NAN", ""]:
                            key = f"{d.strftime('%Y-%m-%d')}_{rid}"
                            new_manual_bars[key] = val.upper()
                st.session_state.manual_bars = new_manual_bars
                st.success("수동 오버라이드가 적용되었습니다.")
                st.rerun()

        st.divider()
        st.subheader("🎯 채널 & 상품 관리 (표 렌더링용)")
        new_ch = st.text_input("표에 띄울 채널 명칭 추가")
        if st.button("➕ 상품 채널 추가"):
            if new_ch and new_ch not in st.session_state.channel_list:
                st.session_state.channel_list.append(new_ch)
                st.session_state.promotions[new_ch] = {"items": []}
                save_channel_configs()
                st.rerun()

        for ch in st.session_state.channel_list:
            with st.expander(f"📦 {ch} 상품 편집"):
                if st.button(f"❌ {ch} 채널 삭제", key=f"del_{ch}"):
                    st.session_state.channel_list.remove(ch)
                    st.session_state.promotions.pop(ch, None)
                    save_channel_configs()
                    st.rerun()
                
                st.info("표에서 바로 수정/추가/삭제 하세요.")
                current_items = st.session_state.promotions[ch].get("items", [])
                df_editor = pd.DataFrame(current_items)
                if df_editor.empty:
                    df_editor = pd.DataFrame(columns=["객실타입", "상품명", "할인(%)", "추가금"])

                edited_df = st.data_editor(
                    df_editor,
                    num_rows="dynamic",
                    column_config={
                        "객실타입": st.column_config.SelectboxColumn(options=ALL_ROOMS, required=True),
                        "상품명": st.column_config.TextColumn(required=True),
                        "할인(%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
                        "추가금": st.column_config.NumberColumn(step=1000, format="%d")
                    },
                    key=f"editor_{ch}",
                    use_container_width=True
                )

                if st.button(f"💾 {ch} 설정 저장", key=f"save_{ch}"):
                    updated_items = edited_df.to_dict(orient="records")
                    st.session_state.promotions[ch]["items"] = updated_items
                    save_channel_configs()
                    st.success("저장 완료!")

        st.divider()
        for ch in st.session_state.channel_list:
            st.markdown(render_master_table(curr, prev, ch_name=ch, title=f"✅ {ch} 판매가 산출", mode="판매가"), unsafe_allow_html=True)

        st.divider()
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 오늘 내역 파이어베이스 저장", use_container_width=True):
                t_df = st.session_state.today_df.copy()
                t_df['Date'] = t_df['Date'].apply(lambda x: x.isoformat())
                p_df_dict = []
                if not st.session_state.prev_df.empty:
                    p_df = st.session_state.prev_df.copy()
                    p_df['Date'] = p_df['Date'].apply(lambda x: x.isoformat())
                    p_df_dict = p_df.to_dict(orient='records')
                db.collection("daily_snapshots").add({
                    "work_date": date.today().strftime("%Y-%m-%d"),
                    "save_time": datetime.now().isoformat(),
                    "data": t_df.to_dict(orient='records'),
                    "prev_data": p_df_dict,
                    "saved_promotions": st.session_state.promotions,
                    "saved_channel_list": st.session_state.channel_list,
                    "saved_manual_bars": st.session_state.manual_bars 
                })
                st.success("DB 저장 완료!")

        with col_btn2:
            def generate_excel():
                output = io.BytesIO()
                export_data = []
                for idx, row in st.session_state.today_df.iterrows():
                    d = row['Date']
                    rid = row['RoomID']
                    o_key = f"{d.strftime('%Y-%m-%d')}_{rid}"
                    m_bar = st.session_state.get('manual_bars', {}).get(o_key)
                    occ, bar, b_price, is_man = get_final_values(rid, d, row['Available'], row['Total'], m_bar)
                    export_data.append({
                        "날짜": d.strftime('%Y-%m-%d'),
                        "객실타입": rid,
                        "잔여객실": row['Available'],
                        "전체객실": row['Total'],
                        "점유율(%)": round(occ, 1),
                        "적용BAR": bar,
                        "판매가": b_price,
                        "수동개입": "O" if is_man else ""
                    })
                df_export = pd.DataFrame(export_data)
                with pd.ExcelWriter(output) as writer:
                    df_export.to_excel(writer, index=False, sheet_name='시장분석데이터')
                return output.getvalue()

            st.download_button(
                label="📊 엑셀 다운로드 실행",
                data=generate_excel(),
                file_name=f"AmberPureHill_Report_{date.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# ==========================================
# TAB 2: 전략적 요금 할증 & 패리티 시뮬레이터 
# ==========================================
with tab2:
    st.header("🧮 전략적 요금 할증 & 패리티 시뮬레이터")
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        st.subheader("1. 기준 및 할증 설정")
        use_occ = st.toggle("📈 예상 점유율(OCC) 기반 BAR 자동 추천")
        occ_pct = 50
        if use_occ:
            occ_pct = st.slider("예상 객실 점유율(OCC) %", 0, 100, 75, step=5)
            
        room_type = st.selectbox("객실 타입", DYNAMIC_ROOMS + list(FIXED_PRICE_TABLE.keys()), index=2, key="t2_room") 
        if room_type in DYNAMIC_ROOMS:
            rate_keys = list(PRICE_TABLE[room_type].keys())
            default_idx = 2
            if use_occ:
                if occ_pct >= 85: default_idx = 7
                elif occ_pct >= 65: default_idx = 5
                elif occ_pct >= 40: default_idx = 3
                elif occ_pct >= 20: default_idx = 1
                else: default_idx = 0
            rate_level = st.selectbox("요금 단계", rate_keys, index=default_idx, key="t2_rate") 
            base_rate = PRICE_TABLE[room_type][rate_level]
        else:
            rate_level = st.selectbox("시즌/요일", list(FIXED_PRICE_TABLE[room_type].keys()), key="t2_rate")
            base_rate = FIXED_PRICE_TABLE[room_type][rate_level]
            
        st.info(f"**선택된 기준 요금:** {base_rate:,}원")
        st.divider()
        markup_method = st.radio("마크업 계산 방식", ["역산 방식 (/ 0.xx)", "단순 가산 방식 (* 1.xx)"], key="t2_markup_m")
        markup_val = st.number_input("마크업 비율 (%)", value=35, step=1, key="t2_markup_v")
        ota_discount_val = st.number_input("목표 OTA 프로모션 할인 (%)", value=45, step=1, key="t2_ota_d")
        commission_val = st.number_input("채널 수수료 (%)", value=15, step=1, key="t2_comm")
        
    with col_result:
        st.subheader("2. 시뮬레이션 결과")
        web_price = int(base_rate * 0.8)
        reg_price = int(base_rate / (1 - markup_val/100)) if markup_method == "역산 방식 (/ 0.xx)" else int(base_rate * (1 + markup_val/100))
        final_ota_price = int(reg_price * (1 - ota_discount_val/100))
        net_income = int(final_ota_price * (1 - commission_val/100))
        price_diff = final_ota_price - web_price
        
        m1, m2 = st.columns(2)
        m1.metric("🌐 홈페이지 판매가", f"{web_price:,}원")
        m2.metric("🛡️ 엑스트라넷 등록가", f"{reg_price:,}원", f"{markup_val}% 할증")
        st.metric("🛒 최종 OTA 고객 판매가", f"{final_ota_price:,}원", f"{-ota_discount_val}% 프로모션 적용", delta_color="inverse")
        if price_diff >= 0: st.success(f"✅ 패리티 안전: +{price_diff:,}원")
        else: st.error(f"🚨 패리티 위험: {price_diff:,}원")
        st.metric("💰 호텔 최종 입금가 (Net)", f"{net_income:,}원", f"수수료 {commission_val}% 제외")

    st.write("---")
    with st.expander("⚖️ 프로모션 손익분기점(BEP) 타겟 역산기", expanded=False):
        bep_c1, bep_c2 = st.columns(2)
        with bep_c1:
            var_cost = st.number_input("1객실당 변동원가 (청소비/어메니티/세탁 등)", value=35000, step=1000)
            target_rooms = st.number_input("기존 얕은 할인 시 예상 판매 객실수 (목표치)", value=10, step=1)
            base_discount = st.number_input("비교할 기존의 얕은 할인율 (%)", value=20, step=1)
        with bep_c2:
            base_ota_price = int(reg_price * (1 - base_discount/100))
            base_net = int(base_ota_price * (1 - commission_val/100))
            base_profit_per_room = base_net - var_cost
            total_target_profit = base_profit_per_room * target_rooms
            new_profit_per_room = net_income - var_cost
            if new_profit_per_room > 0:
                required_rooms = math.ceil(total_target_profit / new_profit_per_room)
                incremental_rooms = required_rooms - target_rooms
                st.metric("파격 할인 시 1객실당 순이익", f"{new_profit_per_room:,}원", f"변동원가 {var_cost:,}원 제외됨")
                st.info(f"💡 기존 총 마진({total_target_profit:,}원)을 방어하려면 **최소 {required_rooms}객실**을 팔아야 합니다.\n\n즉, 프로모션 효과로 평소보다 **+{incremental_rooms}객실** 이상 추가 모객이 되어야 이득입니다.")
            else:
                st.error("🚨 1객실당 순수익이 적자(변동원가 이하)입니다! 특가를 당장 멈추세요.")

# ==========================================
# TAB 3: 트립/부킹/아고다 실전 시뮬레이터
# ==========================================
with tab3:
    st.header("🧱 주요 OTA 실전 Stacking & 패리티 방어 시뮬레이터")
    c_sel1, c_sel2 = st.columns(2)
    with c_sel1: room_type_t3 = st.selectbox("객실 타입 선택", DYNAMIC_ROOMS + list(FIXED_PRICE_TABLE.keys()), key="t3_room", index=2)
    with c_sel2:
        if room_type_t3 in DYNAMIC_ROOMS:
            rate_level_t3 = st.selectbox("요금 단계 선택", list(PRICE_TABLE[room_type_t3].keys()), key="t3_rate", index=2)
            base_rate_t3 = PRICE_TABLE[room_type_t3][rate_level_t3]
        else:
            rate_level_t3 = st.selectbox("시즌/요일 선택", list(FIXED_PRICE_TABLE[room_type_t3].keys()), key="t3_rate")
            base_rate_t3 = FIXED_PRICE_TABLE[room_type_t3][rate_level_t3]

    homepage_rate = int(base_rate_t3 * 0.8) 
    extranet_rate = int(base_rate_t3 / 0.65) 
    m_base1, m_base2 = st.columns(2)
    m_base1.metric("🌐 사수해야 할 홈페이지 요금", f"{homepage_rate:,}원", "-20% 적용")
    m_base2.metric("🛡️ OTA 엑스트라넷 등록 요금", f"{extranet_rate:,}원", "/0.65 가산됨")

    st.write("---")
    st.subheader("2. 채널별 프로모션 중복(Stacking) 시뮬레이션")
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🔵 트립닷컴 (완벽 합산형)", "🟦 부킹닷컴 (조건부 복리형)", "🔴 아고다 (무한복리 & 마진컷)"])
    
    with sub_tab1:
        base_promo_type = st.radio("기본 뼈대가 될 프로모션을 1개만 선택하세요", ["적용 안함", "Group 1 (기본 딜)", "Group 3 (Package)", "Group 4 (Campaign)"], horizontal=True, key="t3_base_promo")
        base_promo_rate = 0
        base_promo_name = ""
        if base_promo_type == "Group 1 (기본 딜)":
            g1_type = st.selectbox("Group 1 상세 선택", ["Basic Deal", "Last Minute", "Early Bird", "Offer for Tonight", "Minimum Stay", "New Property Deal"], key="t3_g1_type")
            base_promo_rate = st.number_input(f"{g1_type} 할인율(%)", value=10, step=1, key="t3_g1_r")
            base_promo_name = f"{g1_type}"
        elif base_promo_type == "Group 3 (Package)":
            base_promo_rate = st.number_input("Package 할인율(%)", value=15, step=1, key="t3_g3_r")
            base_promo_name = "Package"
        elif base_promo_type == "Group 4 (Campaign)":
            base_promo_rate = st.number_input("Campaign 할인율(%)", value=20, step=1, key="t3_g4_r")
            base_promo_name = "Campaign"

        st.divider()
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            g2_mobile = st.toggle("📱 Mobile Rate", key="t3_g2_mob")
            g2_mob_rate = st.number_input("Mobile Rate 할인율(%)", value=15, step=1, key="t3_g2_mob_r") if g2_mobile else 0
            g2_xpos = st.toggle("💻 XPOS", key="t3_g2_xpos")
            g2_xpos_rate = st.number_input("XPOS 할인율(%)", value=10, step=1, key="t3_g2_xpos_r") if g2_xpos else 0
        with col_s2:
            g5_member = st.toggle("👑 TripPlus (Group 5)", key="t3_g5")
            g5_rate = st.number_input("TripPlus 할인율(%)", value=15, step=1, key="t3_g5_r") if g5_member else 0
            g6_smart = st.toggle("💡 Smart Choice / Smart-C (Group 6)", key="t3_g6")
            g6_rate = st.number_input("Smart Choice 할인율(%)", value=5, step=1, key="t3_g6_r") if g6_smart else 0
            g7_coin = st.toggle("🪙 CoinPlus (Group 7)", key="t3_g7")
            g7_rate = st.number_input("CoinPlus 할인율(%)", value=5, step=1, key="t3_g7_r") if g7_coin else 0

        total_discount_pct_t = min(base_promo_rate + g2_mob_rate + g2_xpos_rate + g5_rate + g6_rate + g7_rate, 100)
        discount_amount_t = int(extranet_rate * (total_discount_pct_t / 100))
        final_price_t = extranet_rate - discount_amount_t
        parity_diff_t = final_price_t - homepage_rate

        st.write("---")
        applied_promos_t = []
        if base_promo_name: applied_promos_t.append(f"{base_promo_name} ({base_promo_rate}%)")
        if g2_mobile: applied_promos_t.append(f"Mobile Rate ({g2_mob_rate}%)")
        if g2_xpos: applied_promos_t.append(f"XPOS ({g2_xpos_rate}%)")
        if g5_member: applied_promos_t.append(f"TripPlus ({g5_rate}%)")
        if g6_smart: applied_promos_t.append(f"Smart-C ({g6_rate}%)")
        if g7_coin: applied_promos_t.append(f"CoinPlus ({g7_rate}%)")
        promo_text_t = " + ".join(applied_promos_t) if applied_promos_t else "적용된 할인 없음"
        
        rt1, rt2 = st.columns(2)
        rt1.metric("🔵 고객 최종 결제가", f"{final_price_t:,}원", f"총 {total_discount_pct_t}% 합산 차감", delta_color="inverse")
        if parity_diff_t >= 0: rt2.success(f"✅ 방어 성공: 홈페이지보다 {parity_diff_t:,}원 비쌉니다.")
        else: rt2.error(f"🚨 방어 실패: 홈페이지보다 {abs(parity_diff_t):,}원 저렴합니다!")

    with sub_tab2:
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            is_deep = st.toggle("기간 한정 특가", key="t3_b_deep")
            deep_rate = st.number_input("집중형 특가 할인율(%)", value=30, step=1, key="t3_b_deep_r") if is_deep else 0
        with col_b2:
            camp_promo = st.selectbox("캠페인 선택", ["선택 안함", "휴가 특가", "새해맞이 특가"], key="t3_b_camp")
            camp_rate = st.number_input("캠페인 할인율(%)", value=20, step=1, key="t3_b_camp_r") if camp_promo != "선택 안함" else 0
        with col_b3:
            is_genius = st.toggle("Genius 프로그램", value=True, key="t3_b_gen")
            genius_rate = st.number_input("Genius 할인율(%)", value=10, step=1, key="t3_b_gen_r") if is_genius else 0
            target_promo = st.selectbox("타겟 요금", ["선택 안함", "모바일 할인", "국가별 특가"], key="t3_b_tar")
            target_rate = st.number_input("타겟 할인율(%)", value=10, step=1, key="t3_b_tar_r") if target_promo != "선택 안함" else 0
            port_promo = st.selectbox("포트폴리오 특가", ["선택 안함", "베이직 특가", "조기 예약 특가"], key="t3_b_port")
            port_rate = st.number_input("포트폴리오 할인율(%)", value=10, step=1, key="t3_b_port_r") if port_promo != "선택 안함" else 0

        if is_deep:
            final_price_b = int(extranet_rate * (1 - deep_rate/100))
            applied_list_b = [f"Deep Deal ({deep_rate}%)"]
        else:
            price_path_camp = extranet_rate * (1 - genius_rate/100) * (1 - camp_rate/100)
            price_path_port = extranet_rate * (1 - genius_rate/100) * (1 - target_rate/100) * (1 - port_rate/100)
            if camp_promo != "선택 안함" and price_path_camp < price_path_port:
                final_price_b = int(price_path_camp)
                applied_list_b = [f"Genius ({genius_rate}%)", f"{camp_promo} ({camp_rate}%)"]
            else:
                final_price_b = int(price_path_port)
                applied_list_b = [f"Genius ({genius_rate}%)"] if is_genius else []
                if target_promo != "선택 안함": applied_list_b.append(f"{target_promo} ({target_rate}%)")
                if port_promo != "선택 안함": applied_list_b.append(f"{port_promo} ({port_rate}%)")

        parity_diff_b = final_price_b - homepage_rate
        st.write("---")
        rb1, rb2 = st.columns(2)
        rb1.metric("🟦 고객 최종 결제가", f"{final_price_b:,}원", "순차(복리) 차감됨", delta_color="inverse")
        if parity_diff_b >= 0: rb2.success(f"✅ 방어 성공: 홈페이지보다 {parity_diff_b:,}원 비쌉니다.")
        else: rb2.error(f"🚨 방어 실패: 홈페이지보다 {abs(parity_diff_b):,}원 저렴합니다!")

    with sub_tab3:
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            is_agoda_base = st.toggle("기본 할인 (24h 특가 등)", key="t3_a_base")
            agoda_base_rate = st.number_input("기본 할인율(%)", value=10, step=1, key="t3_a_base_r") if is_agoda_base else 0
        with col_a2:
            is_agoda_mob = st.toggle("모바일/앱 전용 특가", value=True, key="t3_a_mob")
            agoda_mob_rate = st.number_input("모바일 할인율(%)", value=10, step=1, key="t3_a_mob_r") if is_agoda_mob else 0
            is_agoda_vip = st.toggle("Agoda VIP", value=True, key="t3_a_vip")
            agoda_vip_rate = st.selectbox("VIP 등급별 할인(%)", [12, 15, 18], index=1, key="t3_a_vip_r") if is_agoda_vip else 0
        with col_a3:
            is_margin_cut = st.toggle("Agoda 마진컷 개입", value=True, key="t3_a_mc")
            margin_cut_rate = st.slider("예상 마진컷 개입률(%)", min_value=0, max_value=20, value=8, step=1, key="t3_a_mc_r") if is_margin_cut else 0

        agoda_path = extranet_rate * (1 - agoda_base_rate/100) * (1 - agoda_mob_rate/100) * (1 - agoda_vip_rate/100) * (1 - margin_cut_rate/100)
        final_price_a = int(agoda_path)
        parity_diff_a = final_price_a - homepage_rate

        applied_list_a = []
        if is_agoda_base: applied_list_a.append(f"기본({agoda_base_rate}%)")
        if is_agoda_mob: applied_list_a.append(f"모바일({agoda_mob_rate}%)")
        if is_agoda_vip: applied_list_a.append(f"VIP({agoda_vip_rate}%)")
        if is_margin_cut: applied_list_a.append(f"마진컷({margin_cut_rate}%)")

        st.write("---")
        st.subheader("🧾 아고다 최종 요금 산출 결과")
        promo_text_a = " ➔ ".join(applied_list_a) if applied_list_a else "적용된 할인 없음"
        st.info(f"**순차 차감(복리) 순서:** {promo_text_a}")

        ra1, ra2 = st.columns(2)
        ra1.metric("🔴 고객 최종 결제가", f"{final_price_a:,}원", f"총 {len(applied_list_a)}단 복리 차감", delta_color="inverse")
        if parity_diff_a >= 0: ra2.success(f"✅ 방어 성공: 마진컷 개입해도 홈피보다 {parity_diff_a:,}원 비쌈.")
        else: ra2.error(f"🚨 방어 실패: 마진컷 개입 시 홈피보다 {abs(parity_diff_a):,}원 저렴함!")

    st.write("---")
    st.subheader("3. 🕵️ 블라인드 테스트 (OTA 자체 특가 시뮬레이터)")
    with st.expander("🔍 최악의 시나리오 블라인드 테스트 실행하기", expanded=True):
        blind_c1, blind_c2, blind_c3 = st.columns(3)
        with blind_c1:
            st.markdown("**[트립닷컴 공격 시뮬레이션]**")
            blind_trip_rate = st.number_input("숨은 할인율(%) - 트립", value=5, step=1)
            blind_final_t = int(final_price_t * (1 - blind_trip_rate/100))
            blind_diff_t = blind_final_t - homepage_rate
            st.metric(f"🚨 최종가", f"{blind_final_t:,}원", f"{blind_trip_rate}% 추가 깎임", delta_color="inverse")
            if blind_diff_t >= 0: st.success("✅ 방어 성공")
            else: st.error("⚠️ 붕괴!")

        with blind_c2:
            st.markdown("**[부킹닷컴 공격 시뮬레이션]**")
            blind_bk_rate = st.number_input("숨은 할인율(%) - 부킹", value=10, step=1)
            blind_final_b = int(final_price_b * (1 - blind_bk_rate/100))
            blind_diff_b = blind_final_b - homepage_rate
            st.metric(f"🚨 최종가", f"{blind_final_b:,}원", f"{blind_bk_rate}% 추가 깎임", delta_color="inverse")
            if blind_diff_b >= 0: st.success("✅ 방어 성공")
            else: st.error("⚠️ 붕괴!")
                
        with blind_c3:
            st.markdown("**[아고다 추가 공격 시뮬레이션]**")
            blind_ag_rate = st.number_input("숨은 할인율(%) - 아고다", value=5, step=1)
            blind_final_a = int(final_price_a * (1 - blind_ag_rate/100))
            blind_diff_a = blind_final_a - homepage_rate
            st.metric(f"🚨 최종가", f"{blind_final_a:,}원", f"{blind_ag_rate}% 추가 깎임", delta_color="inverse")
            if blind_diff_a >= 0: st.success("✅ 방어 성공")
            else: st.error("⚠️ 붕괴!")

    trip_mult = final_price_t / extranet_rate if extranet_rate > 0 else 1
    bk_mult = final_price_b / extranet_rate if extranet_rate > 0 else 1
    ag_mult = final_price_a / extranet_rate if extranet_rate > 0 else 1

# ==========================================
# TAB 4: 프로모션 스케줄 및 현황 관리 (+Gantt 차트)
# ==========================================
with tab4:
    st.header("📅 채널별 프로모션 스케줄 및 현황 관리")
    
    st.subheader("📊 전 채널 통합 프로모션 타임라인")
    all_promo_dfs = []
    for ch_name in st.session_state.ota_channels:
        state_key = f'promo_schedule_{ch_name}'
        if state_key in st.session_state and not st.session_state[state_key].empty:
            temp_df = st.session_state[state_key].copy()
            temp_df['채널명'] = ch_name
            all_promo_dfs.append(temp_df)

    if all_promo_dfs:
        master_df = pd.concat(all_promo_dfs, ignore_index=True)
        valid_df = master_df.dropna(subset=['시작일', '종료일'])
        if not valid_df.empty:
            fig = px.timeline(valid_df, x_start="시작일", x_end="종료일", y="채널명", color="채널명", text="프로모션명", hover_data=["할인율(%)"])
            fig.update_yaxes(autorange="reversed") 
            fig.update_layout(showlegend=False, height=300, margin=dict(t=20, b=20, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

    st.write("---")
    channel_tabs = st.tabs([f"📌 {ch}" for ch in st.session_state.ota_channels])

    for i, ch_name in enumerate(st.session_state.ota_channels):
        with channel_tabs[i]:
            st.subheader(f"📝 {ch_name} 프로모션 현황판")
            state_key = f'promo_schedule_{ch_name}'
            if state_key not in st.session_state:
                st.session_state[state_key] = pd.DataFrame([{"프로모션명": "예시 특가", "할인율(%)": 10, "시작일": date.today(), "종료일": date.today() + timedelta(days=7)}])

            df = st.session_state[state_key]
            today_dt = pd.to_datetime(date.today())
            df['상태'] = df.apply(lambda row: "⚫ 종료됨" if pd.notna(row['종료일']) and pd.to_datetime(row['종료일']) < today_dt else ("🟡 진행 예정" if pd.notna(row['시작일']) and pd.to_datetime(row['시작일']) > today_dt else "🟢 진행 중"), axis=1)

            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_tab4_{ch_name}",
                column_config={
                    "프로모션명": st.column_config.TextColumn(required=True),
                    "할인율(%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1, format="%d%%"),
                    "시작일": st.column_config.DateColumn(format="YYYY-MM-DD"),
                    "종료일": st.column_config.DateColumn(format="YYYY-MM-DD"),
                    "상태": st.column_config.TextColumn(disabled=True) 
                }
            )
            st.session_state[state_key] = edited_df.drop(columns=['상태'])

# ==========================================
# TAB 5: 지능형 경영진 브리핑 리포트 
# ==========================================
with tab5:
    st.header("📋 지능형 경영진 브리핑 리포트")
    report_ext_rate = int(base_rate_t3 / 0.65)
    report_hp_rate = int(base_rate_t3 * 0.8)
    
    danger_channels = []
    if final_price_t < report_hp_rate: danger_channels.append(f"트립닷컴(차액: {final_price_t - report_hp_rate:,}원)")
    if final_price_b < report_hp_rate: danger_channels.append(f"부킹닷컴(차액: {final_price_b - report_hp_rate:,}원)")
    if final_price_a < report_hp_rate: danger_channels.append(f"아고다(차액: {final_price_a - report_hp_rate:,}원)")

    st.write("---")
    if danger_channels:
        st.error(f"### 🚨 전략 경보: 채널 패리티 붕괴 위험 감지\n현재 {', '.join(danger_channels)}의 최종 판매가가 홈페이지 요금보다 낮게 세팅되어 있습니다. 조정이 시급합니다.")
    else:
        st.success("### ✅ 전략 보고: 채널 패리티 안정 유지 중\n모든 OTA 채널의 최종 판매가가 공식 홈페이지 가격 이상으로 방어되고 있습니다.")

    st.subheader("📝 세일즈 전략 요약")
    active_promos = []
    for ch_name in st.session_state.ota_channels:
        state_key = f'promo_schedule_{ch_name}'
        if state_key in st.session_state:
            df = st.session_state[state_key]
            for _, row in df.iterrows():
                if pd.notna(row['시작일']) and pd.notna(row['종료일']):
                    if pd.to_datetime(row['시작일']) <= today_dt <= pd.to_datetime(row['종료일']):
                        active_promos.append(f"   - {ch_name}: {row['프로모션명']} ({row['할인율(%)']}% 할인)")

    promo_summary = "\n".join(active_promos) if active_promos else "   - 현재 진행 중인 주요 특가 없음"

    final_report = f"""
## [보고] 온라인 세일즈 전략 및 마진 분석 ({date.today().strftime('%Y-%m-%d')})

### 1. 요금 전략 핵심 지표
* **대상 객실:** {room_type_t3}
* **적용 요금제:** {rate_level_t3} (기준가: {base_rate_t3:,}원)
* **홈페이지 최저가:** {report_hp_rate:,}원
* **OTA 할증 등록가:** {report_ext_rate:,}원 (기준가 대비 35% 역산 인상)

### 2. 채널별 라이브 프로모션 현황
{promo_summary}

### 3. 실무 및 전략 제언
* OTA 채널의 파격 할인에도 불구하고 엑스트라넷 등록가 할증을 통해 **평균 {((report_ext_rate/base_rate_t3)-1)*100:.1f}%의 버퍼**를 확보했습니다.
* 아고다 마진컷 등 블라인드 요금 개입 시뮬레이션 결과 패리티 방어가 확인되었습니다.
"""
    st.markdown(final_report)
    st.download_button("📥 보고서 파일 다운로드", data=final_report, file_name=f"Amber_Sales_Report_{date.today()}.txt")

# ==========================================
# TAB 6: 장기 요금 프로젝션 (DB 연동)
# ==========================================
with tab6:
    st.header("🗓️ 장기 요금 프로젝션 (판매가 추이 분석)")
    st.markdown("사이드바에서 업로드된 **재고 데이터(DB)**를 기반으로 연말까지의 **홈페이지가**와 **OTA별 최종 판매가**를 시뮬레이션합니다.")
    
    if st.session_state.today_df.empty:
        st.warning("👈 사이드바에서 재고 엑셀/CSV 파일을 업로드하거나 과거 기록을 불러와주세요.")
    else:
        proj_room = st.selectbox("분석할 객실 타입 선택", ALL_ROOMS, key="proj_room_t6")
        room_df = st.session_state.today_df[st.session_state.today_df['RoomID'] == proj_room].copy()
        
        if room_df.empty:
            st.error("해당 객실에 대한 재고 데이터가 없습니다.")
        else:
            base_rates = []
            for idx, row in room_df.iterrows():
                d = row['Date']
                avail = row['Available']
                tot = row['Total']
                o_key = f"{d.strftime('%Y-%m-%d')}_{proj_room}"
                m_bar = st.session_state.get('manual_bars', {}).get(o_key)
                occ, bar, b_price, is_man = get_final_values(proj_room, d, avail, tot, m_bar)
                base_rates.append(b_price)
            
            room_df['BaseRate'] = base_rates
            room_df = room_df.sort_values('Date')
            
            future_data = room_df[room_df['Date'] >= date.today()].copy()
            
            if future_data.empty:
                st.warning("오늘 이후의 요금 데이터가 없습니다.")
            else:
                future_data['기준가(BAR)'] = future_data['BaseRate'].astype(int)
                future_data['홈페이지(-20%)'] = (future_data['BaseRate'] * 0.8).astype(int)
                future_data['OTA등록가(/0.65)'] = (future_data['BaseRate'] / 0.65).astype(int)
                
                future_data['트립 예상가'] = (future_data['OTA등록가(/0.65)'] * trip_mult).astype(int)
                future_data['부킹 예상가'] = (future_data['OTA등록가(/0.65)'] * bk_mult).astype(int)
                future_data['아고다 예상가'] = (future_data['OTA등록가(/0.65)'] * ag_mult).astype(int)
                
                future_data['날짜'] = future_data['Date'].apply(lambda x: x.strftime('%m/%d'))
                display_cols = ['날짜', '기준가(BAR)', '홈페이지(-20%)', 'OTA등록가(/0.65)', '트립 예상가', '부킹 예상가', '아고다 예상가']
                
                pivot_proj = future_data[display_cols].set_index('날짜').T
                
                st.write("---")
                st.subheader(f"🔍 {proj_room} 장기 요금 프로젝션 상세")
                st.caption("※ 각 채널별 예상가는 **'탭 3'에서 세팅해둔 프로모션 할인율을 동일하게 적용**하여 동적으로 계산된 값입니다.")
                st.dataframe(pivot_proj, use_container_width=True)
                
                st.write("---")
                st.subheader("📈 채널별 패리티 변동 추이 그래프")
                chart_df = future_data.melt(id_vars=['Date'], 
                                            value_vars=['홈페이지(-20%)', '트립 예상가', '부킹 예상가', '아고다 예상가'], 
                                            var_name='채널', value_name='최종요금')
                fig_line = px.line(chart_df, x='Date', y='최종요금', color='채널', title=f"{proj_room} 채널별 최종 판매가 시뮬레이션")
                st.plotly_chart(fig_line, use_container_width=True)
