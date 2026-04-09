import streamlit as st
import pandas as pd
import math
import datetime
import plotly.express as px  # 👈 간트 차트를 위한 라이브러리
import re

# --- 1. 전역 설정 및 데이터 ---
st.set_page_config(page_title="앰버퓨어힐 전략 시뮬레이터", layout="wide")

DYNAMIC_ROOMS = ["FDB", "FDE", "HDP", "HDT", "HDF"]
FIXED_ROOMS = ["GDB", "GDF", "FFD", "FPT", "PPV"]

PRICE_TABLE = {
    "FDB": {"BAR8": 315000, "BAR7": 353000, "BAR6": 396000, "BAR5": 445000, "BAR4": 502000, "BAR3": 567000, "BAR2": 642000, "BAR1": 728000, "BAR0": 802000},
    "FDE": {"BAR8": 352000, "BAR7": 390000, "BAR6": 433000, "BAR5": 482000, "BAR4": 539000, "BAR3": 604000, "BAR2": 679000, "BAR1": 765000, "BAR0": 839000},
    "HDP": {"BAR8": 280000, "BAR7": 318000, "BAR6": 361000, "BAR5": 410000, "BAR4": 467000, "BAR3": 532000, "BAR2": 607000, "BAR1": 693000, "BAR0": 759000},
    "HDT": {"BAR8": 250000, "BAR7": 288000, "BAR6": 331000, "BAR5": 380000, "BAR4": 437000, "BAR3": 502000, "BAR2": 577000, "BAR1": 663000, "BAR0": 729000},
    "HDF": {"BAR8": 420000, "BAR7": 458000, "BAR6": 501000, "BAR5": 550000, "BAR4": 607000, "BAR3": 672000, "BAR2": 747000, "BAR1": 833000, "BAR0": 916000},
}

FIXED_PRICE_TABLE = {
    "GDB": {"UND1": 298000, "UND2": 298000, "MID1": 298000, "MID2": 298000, "UPP1": 298000, "UPP2": 298000, "UPP3":298000},
    "GDF": {"UND1": 375000, "UND2": 410000, "MID1": 410000, "MID2": 488000, "UPP1": 488000, "UPP2": 578000, "UPP3":678000},
    "FFD": {"UND1": 353000, "UND2": 393000, "MID1": 433000, "MID2": 482000, "UPP1": 539000, "UPP2": 604000, "UPP3":704000},
    "FPT": {"UND1": 500000, "UND2": 550000, "MID1": 600000, "MID2": 650000, "UPP1": 700000, "UPP2": 750000, "UPP3":850000},
    "PPV(온수O)": {"UND1": 1004000, "UND2": 1154000, "MID1": 1154000, "MID2": 1304000, "UPP1": 1304000, "UPP2": 1554000, "UPP3":1704000},
}

# 👈 [신규 추가] 엑셀 날짜 형식을 인식하기 위한 파서 함수
def robust_date_parser(d_val):
    if pd.isna(d_val): return None
    try:
        # 엑셀 날짜 일련번호 처리
        if isinstance(d_val, (int, float)): return (pd.to_datetime('1899-12-30') + pd.to_timedelta(d_val, 'D')).date()
        # 문자열 날짜 처리
        s = str(d_val).strip().replace('.', '-').replace('/', '-').replace(' ', '')
        match = re.search(r'(\d{1,2})-(\d{1,2})', s)
        if match: return datetime.date(2026, int(match.group(1)), int(match.group(2)))
    except: pass
    return None

# --- 채널 및 마스터 요금 세션 ---
if 'ota_channels' not in st.session_state:
    st.session_state.ota_channels = ["Trip.com", "Booking.com", "Agoda", "야놀자", "여기어때"] 
if 'master_rates' not in st.session_state:
    st.session_state.master_rates = pd.DataFrame() # 👈 [신규 추가] 엑셀 데이터 저장소

st.title("🏨 앰버퓨어힐 요금 및 프로모션 통합 시뮬레이터")

# --- 사이드바: 채널 추가 및 요금표 업로드 ---
with st.sidebar:
    st.header("⚙️ 스케줄러 채널 추가")
    st.write("새로운 OTA를 추가하면 '탭 4' 내부에 전용 스케줄 관리 탭이 생성됩니다.")
    new_ota = st.text_input("추가할 OTA 명칭 (예: 익스피디아)")
    
    if st.button("➕ 채널 탭 생성"):
        if new_ota and new_ota not in st.session_state.ota_channels:
            st.session_state.ota_channels.append(new_ota)
            st.rerun()
            
    st.divider()
    if st.button("🗑️ 추가된 채널 초기화"):
        st.session_state.ota_channels = ["Trip.com", "Booking.com", "Agoda"]
        st.rerun()
        
    st.divider()
    # 👈 [신규 추가] 엑셀 파일 업로더
    st.header("📂 장기 요금표 업데이트")
    st.caption("탭 6 프로젝션을 위해 요금 엑셀 파일을 업로드하세요.")
    uploaded_file = st.file_uploader("요금표 선택 (xlsx)", type="xlsx")
    
    if uploaded_file:
        new_extracted = []
        # 제공해주신 양식 기준 행 매핑
        ROW_MAP = {4:"GDB", 5:"GDF", 6:"FDB", 7:"FDE", 8:"FPT", 9:"FFD", 10:"HDP", 11:"HDT", 12:"HDF", 13:"PPV"}
        df_raw = pd.read_excel(uploaded_file, header=None)
        dates_raw = df_raw.iloc[2, 2:].values
        
        for r_idx, rid in ROW_MAP.items():
            if r_idx < len(df_raw):
                for d_val, price in zip(dates_raw, df_raw.iloc[r_idx, 2:].values):
                    d_obj = robust_date_parser(d_val)
                    if d_obj:
                        new_extracted.append({"Date": d_obj, "RoomID": rid, "BaseRate": price})
        
        if new_extracted:
            st.session_state.master_rates = pd.DataFrame(new_extracted)
            st.success(f"✅ {len(st.session_state.master_rates)}건 요금 데이터 업데이트 완료!")

# --- 메인 탭 구성 ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 1. 기준 요금표", 
    "🧮 2. 요금 역산 시뮬", 
    "🧱 3. 트립/부킹/아고다 실전", 
    "📅 4. 채널별 스케줄",
    "📋 5. 경영진 리포트",  
    "🗓️ 6. 장기 요금 프로젝션" # 👈 [신규 추가]
])

# ==========================================
# TAB 1: 전체 기준 요금표
# ==========================================
with tab1:
    st.header("전체 객실 기준 요금 (Master Rate)")
    
    show_direct_rate = st.toggle("🌐 홈페이지 요금 보기 (기준가 -20% 적용)")
    multiplier = 0.8 if show_direct_rate else 1.0
    
    def format_price_df(data_dict):
        df = pd.DataFrame(data_dict).T
        return df.map(lambda x: f"{int(math.floor((x * multiplier)/1000)*1000):,}원" if pd.notnull(x) else "-")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("변동 요금제 (Dynamic)")
        st.dataframe(format_price_df(PRICE_TABLE), use_container_width=True)
    with col2:
        st.subheader("고정 요금제 (Fixed)")
        st.dataframe(format_price_df(FIXED_PRICE_TABLE), use_container_width=True)

# ==========================================
# TAB 2: 전략적 요금 할증 & 패리티 시뮬레이터 (+OCC/BEP)
# ==========================================
with tab2:
    st.header("🧮 전략적 요금 할증 & 패리티 시뮬레이터")
    st.write("인상 방식부터 할인율까지 모든 변수를 조절하여 최적의 OTA 등록가를 찾습니다.")
    
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
            default_idx = 2 # 기본 BAR6
            
            if use_occ:
                if occ_pct >= 85: default_idx = 7 # BAR1
                elif occ_pct >= 65: default_idx = 5 # BAR3
                elif occ_pct >= 40: default_idx = 3 # BAR5
                elif occ_pct >= 20: default_idx = 1 # BAR7
                else: default_idx = 0 # BAR8
                st.caption(f"💡 점유율 {occ_pct}% 기준 추천 요금제: **{rate_keys[default_idx]}**")

            rate_level = st.selectbox("요금 단계", rate_keys, index=default_idx, key="t2_rate") 
            base_rate = PRICE_TABLE[room_type][rate_level]
        else:
            rate_level = st.selectbox("시즌/요일", list(FIXED_PRICE_TABLE[room_type].keys()), key="t2_rate")
            base_rate = FIXED_PRICE_TABLE[room_type][rate_level]
            
        st.info(f"**선택된 기준 요금:** {base_rate:,}원")
        
        st.divider()
        markup_method = st.radio("마크업 계산 방식", ["역산 방식 (/ 0.xx)", "단순 가산 방식 (* 1.xx)"], key="t2_markup_m")
        markup_val = st.number_input("마크업 비율 (%)", value=35, step=1, key="t2_markup_v")
        
        st.divider()
        ota_discount_val = st.number_input("목표 OTA 프로모션 할인 (%)", value=45, step=1, key="t2_ota_d")
        commission_val = st.number_input("채널 수수료 (%)", value=15, step=1, key="t2_comm")
        
    with col_result:
        st.subheader("2. 시뮬레이션 결과")
        
        web_price = int(base_rate * 0.8)
        
        if markup_method == "역산 방식 (/ 0.xx)":
            reg_price = int(base_rate / (1 - markup_val/100)) if markup_val < 100 else 0
        else:
            reg_price = int(base_rate * (1 + markup_val/100))
            
        final_ota_price = int(reg_price * (1 - ota_discount_val/100))
        net_income = int(final_ota_price * (1 - commission_val/100))
        
        price_diff = final_ota_price - web_price
        
        m1, m2 = st.columns(2)
        m1.metric("🌐 홈페이지 판매가", f"{web_price:,}원")
        m2.metric("🛡️ 엑스트라넷 등록가", f"{reg_price:,}원", f"{markup_val}% 할증")
        
        st.write("---")
        st.metric("🛒 최종 OTA 고객 판매가", f"{final_ota_price:,}원", f"{-ota_discount_val}% 프로모션 적용", delta_color="inverse")
        
        if price_diff >= 0:
            st.success(f"✅ **패리티 안전:** 홈페이지보다 **{price_diff:,}원** 비싸게 판매됩니다.")
        else:
            st.error(f"🚨 **패리티 위험:** 홈페이지보다 **{abs(price_diff):,}원** 저렴합니다! 설정을 변경하세요.")
            
        st.divider()
        st.metric("💰 호텔 최종 입금가 (Net)", f"{net_income:,}원", f"수수료 {commission_val}% 제외")

    st.write("---")
    with st.expander("⚖️ 프로모션 손익분기점(BEP) 타겟 역산기", expanded=False):
        st.markdown("현재 설정된 파격 할인율을 적용했을 때, **몇 객실을 더 팔아야 기존의 적은 할인율로 팔았을 때의 마진을 방어(본전)할 수 있는지** 계산합니다.")
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
# TAB 3: 실전 시뮬레이터 (트립 / 부킹 / 아고다 / 블라인드 테스트 유지)
# ==========================================
with tab3:
    st.header("🧱 주요 OTA 실전 Stacking & 패리티 방어 시뮬레이터")
    st.markdown("객실과 요금제를 선택하면 **홈페이지 요금(-20%)**과 **엑스트라넷 박제 요금(/0.65)**이 자동 로드됩니다.")
    
    st.subheader("1. 기준 요금 불러오기")
    col_sel1, col_sel2 = st.columns(2)
    
    with col_sel1:
        room_type_t3 = st.selectbox("객실 타입 선택", DYNAMIC_ROOMS + list(FIXED_PRICE_TABLE.keys()), key="t3_room", index=2)
        
    with col_sel2:
        if room_type_t3 in DYNAMIC_ROOMS:
            rate_level_t3 = st.selectbox("요금 단계 선택", list(PRICE_TABLE[room_type_t3].keys()), key="t3_rate", index=2)
            base_rate_t3 = PRICE_TABLE[room_type_t3][rate_level_t3]
        else:
            rate_level_t3 = st.selectbox("시즌/요일 선택", list(FIXED_PRICE_TABLE[room_type_t3].keys()), key="t3_rate")
            base_rate_t3 = FIXED_PRICE_TABLE[room_type_t3][rate_level_t3]

    homepage_rate = int(base_rate_t3 * 0.8) 
    extranet_rate = int(base_rate_t3 / 0.65) 
    
    st.info(f"💡 **[{room_type_t3} - {rate_level_t3}]** 오리지널 기준가: **{base_rate_t3:,}원**")
    
    m_base1, m_base2 = st.columns(2)
    m_base1.metric("🌐 사수해야 할 홈페이지 요금", f"{homepage_rate:,}원", "-20% 적용")
    m_base2.metric("🛡️ OTA 엑스트라넷 등록 요금", f"{extranet_rate:,}원", "/0.65 가산됨")

    st.write("---")
    st.subheader("2. 채널별 프로모션 중복(Stacking) 시뮬레이션")
    
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🔵 트립닷컴 (완벽 합산형)", "🟦 부킹닷컴 (조건부 복리형)", "🔴 아고다 (무한복리 & 마진컷)"])
    
    # ---------------- 트립닷컴 ----------------
    with sub_tab1:
        st.markdown("#### 트립닷컴 실전 시뮬레이션")
        st.markdown("가로축(Group 1, 3, 4)은 중복이 불가하며, 세로축(Group 2, 5, 6, 7)은 선택된 가로축과 함께 모두 중복 **합산**됩니다.")
        
        st.markdown("##### ⛔ Non-Stackable Discount (택 1)")
        base_promo_type = st.radio("기본 뼈대가 될 프로모션을 1개만 선택하세요", 
                                   ["적용 안함", "Group 1 (기본 딜)", "Group 3 (Package)", "Group 4 (Campaign)"], 
                                   horizontal=True, key="t3_base_promo")

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

        st.markdown("##### 🔽 Stackable Discount (위에서 선택한 항목과 중복 합산됨)")
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("**🟦 Group 2**")
            g2_mobile = st.toggle("📱 Mobile Rate", key="t3_g2_mob")
            g2_mob_rate = st.number_input("Mobile Rate 할인율(%)", value=15, step=1, key="t3_g2_mob_r") if g2_mobile else 0

            g2_xpos = st.toggle("💻 XPOS", key="t3_g2_xpos")
            g2_xpos_rate = st.number_input("XPOS 할인율(%)", value=10, step=1, key="t3_g2_xpos_r") if g2_xpos else 0

        with col_s2:
            st.markdown("**🟧🟩 Group 5, 6, 7**")
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
        st.subheader("🧾 트립닷컴 최종 요금 산출 결과")
        
        applied_promos_t = []
        if base_promo_name: applied_promos_t.append(f"{base_promo_name} ({base_promo_rate}%)")
        if g2_mobile: applied_promos_t.append(f"Mobile Rate ({g2_mob_rate}%)")
        if g2_xpos: applied_promos_t.append(f"XPOS ({g2_xpos_rate}%)")
        if g5_member: applied_promos_t.append(f"TripPlus ({g5_rate}%)")
        if g6_smart: applied_promos_t.append(f"Smart-C ({g6_rate}%)")
        if g7_coin: applied_promos_t.append(f"CoinPlus ({g7_rate}%)")
        
        promo_text_t = " + ".join(applied_promos_t) if applied_promos_t else "적용된 할인 없음"
        st.info(f"**활성화된 프로모션 조합:** {promo_text_t}")

        rt1, rt2 = st.columns(2)
        rt1.metric("🔵 고객 최종 결제가", f"{final_price_t:,}원", f"총 {total_discount_pct_t}% 합산 차감", delta_color="inverse")
        
        if parity_diff_t >= 0:
            rt2.success(f"✅ **방어 성공:** 홈페이지 요금보다 **{parity_diff_t:,}원** 비쌉니다.")
        else:
            rt2.error(f"🚨 **방어 실패:** 홈페이지 요금보다 **{abs(parity_diff_t):,}원** 저렴합니다! 할인율을 낮추세요.")

    # ---------------- 부킹닷컴 ----------------
    with sub_tab2:
        st.markdown("#### 부킹닷컴 실전 시뮬레이션")
        st.markdown("부킹닷컴은 카테고리별로 할인이 겹칠 때 **순차적 차감(복리형)**이 적용되며, 고객에게 가장 유리한 트랙이 자동 선택됩니다.")
        
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            st.markdown("#### 1. 집중형 특가")
            st.caption("※ 단독 적용")
            is_deep = st.toggle("기간 한정 특가", key="t3_b_deep")
            deep_rate = st.number_input("집중형 특가 할인율(%)", value=30, step=1, key="t3_b_deep_r") if is_deep else 0
        with col_b2:
            st.markdown("#### 2. 캠페인 특가")
            st.caption("※ Genius 중복")
            camp_promo = st.selectbox("캠페인 선택", ["선택 안함", "휴가 특가", "새해맞이 특가"], key="t3_b_camp")
            camp_rate = st.number_input("캠페인 할인율(%)", value=20, step=1, key="t3_b_camp_r") if camp_promo != "선택 안함" else 0
        with col_b3:
            st.markdown("#### 3. 타겟/포트폴리오")
            st.caption("※ 상호 중복")
            is_genius = st.toggle("Genius 프로그램", value=True, key="t3_b_gen")
            genius_rate = st.number_input("Genius 할인율(%)", value=10, step=1, key="t3_b_gen_r") if is_genius else 0
            target_promo = st.selectbox("타겟 요금", ["선택 안함", "모바일 할인", "국가별 특가"], key="t3_b_tar")
            target_rate = st.number_input("타겟 할인율(%)", value=10, step=1, key="t3_b_tar_r") if target_promo != "선택 안함" else 0
            port_promo = st.selectbox("포트폴리오 특가", ["선택 안함", "베이직 특가", "조기 예약 특가"], key="t3_b_port")
            port_rate = st.number_input("포트폴리오 할인율(%)", value=10, step=1, key="t3_b_port_r") if port_promo != "선택 안함" else 0

        if is_deep:
            final_price_b = int(extranet_rate * (1 - deep_rate/100))
            active_path = "집중형 특가 (단독 적용 트랙)"
            applied_list_b = [f"Deep Deal ({deep_rate}%)"]
        else:
            price_path_camp = extranet_rate * (1 - genius_rate/100) * (1 - camp_rate/100)
            price_path_port = extranet_rate * (1 - genius_rate/100) * (1 - target_rate/100) * (1 - port_rate/100)
            
            if camp_promo != "선택 안함" and price_path_camp < price_path_port:
                final_price_b = int(price_path_camp)
                active_path = "Genius + 캠페인 특가 트랙"
                applied_list_b = [f"Genius ({genius_rate}%)", f"{camp_promo} ({camp_rate}%)"]
            else:
                final_price_b = int(price_path_port)
                active_path = "Genius + 타겟/포트폴리오 트랙"
                applied_list_b = [f"Genius ({genius_rate}%)"] if is_genius else []
                if target_promo != "선택 안함": applied_list_b.append(f"{target_promo} ({target_rate}%)")
                if port_promo != "선택 안함": applied_list_b.append(f"{port_promo} ({port_rate}%)")

        parity_diff_b = final_price_b - homepage_rate

        st.write("---")
        st.subheader("🧾 부킹닷컴 최종 요금 산출 결과")
        
        promo_text_b = " ➔ ".join(applied_list_b) if applied_list_b else "적용된 할인 없음"
        st.info(f"**활성화된 중복 규칙:** {active_path}\n\n**순차 차감(복리) 순서:** {promo_text_b}")

        rb1, rb2 = st.columns(2)
        rb1.metric("🟦 고객 최종 결제가", f"{final_price_b:,}원", "순차(복리) 차감됨", delta_color="inverse")
        
        if parity_diff_b >= 0:
            rb2.success(f"✅ **방어 성공:** 홈페이지 요금보다 **{parity_diff_b:,}원** 비쌉니다.")
        else:
            rb2.error(f"🚨 **방어 실패:** 홈페이지 요금보다 **{abs(parity_diff_b):,}원** 저렴합니다! 할인 중복을 해제하세요.")

    # ---------------- 아고다 ----------------
    with sub_tab3:
        st.markdown("#### 아고다 실전 시뮬레이션 (마진컷 대비)")
        st.markdown("아고다는 모든 할인이 **무자비한 순차적 복리**로 적용되며, 호텔의 통제를 벗어나는 **'마진컷(Agoda Funded)'**이 수시로 개입하여 패리티를 박살 냅니다.")
        
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            st.markdown("#### 1. 기본 프로모션")
            is_agoda_base = st.toggle("기본 할인 (24h 특가 등)", key="t3_a_base")
            agoda_base_rate = st.number_input("기본 할인율(%)", value=10, step=1, key="t3_a_base_r") if is_agoda_base else 0
            
        with col_a2:
            st.markdown("#### 2. 채널 특가 & VIP")
            is_agoda_mob = st.toggle("모바일/앱 전용 특가", value=True, key="t3_a_mob")
            agoda_mob_rate = st.number_input("모바일 할인율(%)", value=10, step=1, key="t3_a_mob_r") if is_agoda_mob else 0
            
            is_agoda_vip = st.toggle("Agoda VIP", value=True, key="t3_a_vip")
            agoda_vip_rate = st.selectbox("VIP 등급별 할인(%)", [12, 15, 18], index=1, key="t3_a_vip_r") if is_agoda_vip else 0
            
        with col_a3:
            st.markdown("#### 3. 💣 아고다 마진컷")
            st.caption("※ 호텔 몰래 수수료를 태우는 자체 쿠폰")
            is_margin_cut = st.toggle("Agoda 마진컷 개입", value=True, key="t3_a_mc")
            margin_cut_rate = st.slider("예상 마진컷 개입률(%)", min_value=0, max_value=20, value=8, step=1, key="t3_a_mc_r") if is_margin_cut else 0

        # 아고다 무한 복리 계산 (순차 차감)
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
        
        if parity_diff_a >= 0:
            ra2.success(f"✅ **방어 성공:** 마진컷이 개입해도 홈페이지 요금보다 **{parity_diff_a:,}원** 비쌉니다.")
        else:
            ra2.error(f"🚨 **방어 실패 (패리티 붕괴):** 마진컷 개입 시 홈페이지 요금보다 **{abs(parity_diff_a):,}원** 저렴해집니다! 엑스트라넷 요금을 더 할증하거나 VIP 할인을 조정하세요.")

    # ---------------- 블라인드 테스트 ----------------
    st.write("---")
    st.subheader("3. 🕵️ 블라인드 테스트 (OTA 자체 특가 시뮬레이터)")
    st.markdown("우리가 통제할 수 없는 OTA의 **'자체 쿠폰'**, **'비공개 회원가(Private Rate)'**, **'지역 한정 특가'**가 위에서 계산된 최종 요금에 갑자기 덧붙었을 때, 홈페이지 패리티가 털리는지 미리 점검합니다.")

    with st.expander("🔍 최악의 시나리오 블라인드 테스트 실행하기", expanded=True):
        blind_c1, blind_c2, blind_c3 = st.columns(3)
        
        with blind_c1:
            st.markdown("**[트립닷컴 공격 시뮬레이션]**")
            blind_trip_desc = st.text_input("예상 숨은 할인", value="트립닷컴 VIP 시크릿 할인")
            blind_trip_rate = st.number_input("숨은 할인율(%) - 트립", value=5, step=1)
            
            blind_final_t = int(final_price_t * (1 - blind_trip_rate/100))
            blind_diff_t = blind_final_t - homepage_rate
            
            st.metric(f"🚨 최종가", f"{blind_final_t:,}원", f"{blind_trip_rate}% 추가 깎임", delta_color="inverse")
            if blind_diff_t >= 0:
                st.success(f"✅ **방어!** 홈피보다 {blind_diff_t:,}원 비쌈")
            else:
                st.error(f"⚠️ **붕괴!** 홈피보다 {abs(blind_diff_t):,}원 저렴함")

        with blind_c2:
            st.markdown("**[부킹닷컴 공격 시뮬레이션]**")
            blind_bk_desc = st.text_input("예상 숨은 할인", value="Booking 자체 프로모코드")
            blind_bk_rate = st.number_input("숨은 할인율(%) - 부킹", value=10, step=1)
            
            blind_final_b = int(final_price_b * (1 - blind_bk_rate/100))
            blind_diff_b = blind_final_b - homepage_rate
            
            st.metric(f"🚨 최종가", f"{blind_final_b:,}원", f"{blind_bk_rate}% 추가 깎임", delta_color="inverse")
            if blind_diff_b >= 0:
                st.success(f"✅ **방어!** 홈피보다 {blind_diff_b:,}원 비쌈")
            else:
                st.error(f"⚠️ **붕괴!** 홈피보다 {abs(blind_diff_b):,}원 저렴함")
                
        with blind_c3:
            st.markdown("**[아고다 추가 공격 시뮬레이션]**")
            blind_ag_desc = st.text_input("예상 숨은 할인", value="Agoda 게릴라 쿠폰")
            blind_ag_rate = st.number_input("숨은 할인율(%) - 아고다", value=5, step=1)
            
            blind_final_a = int(final_price_a * (1 - blind_ag_rate/100))
            blind_diff_a = blind_final_a - homepage_rate
            
            st.metric(f"🚨 최종가", f"{blind_final_a:,}원", f"{blind_ag_rate}% 추가 깎임", delta_color="inverse")
            if blind_diff_a >= 0:
                st.success(f"✅ **방어!** 홈피보다 {blind_diff_a:,}원 비쌈")
            else:
                st.error(f"⚠️ **붕괴!** 홈피보다 {abs(blind_diff_a):,}원 저렴함")

    # 👇 탭 6 연동을 위한 승수(Multiplier) 저장 (ZeroDivisionError 방지)
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
            fig = px.timeline(valid_df, x_start="시작일", x_end="종료일", y="채널명", 
                              color="채널명", text="프로모션명", hover_data=["할인율(%)"])
            fig.update_yaxes(autorange="reversed") 
            fig.update_layout(showlegend=False, height=300, margin=dict(t=20, b=20, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("진행 중인 프로모션 일정이 없습니다.")
    else:
        st.caption("프로모션 데이터를 입력하면 타임라인이 생성됩니다.")

    st.write("---")
    st.markdown("사이드바에서 추가한 모든 채널들이 아래에 탭으로 생성됩니다. 각 채널 탭에 들어가 독립적으로 스케줄을 관리하세요.")
    
    today_dt = pd.to_datetime(datetime.date.today())
    def get_status(row):
        start = pd.to_datetime(row['시작일'])
        end = pd.to_datetime(row['종료일'])
        if pd.isna(start) or pd.isna(end): return "⚪ 미정"
        elif end < today_dt: return "⚫ 종료됨"
        elif start > today_dt: return "🟡 진행 예정"
        else: return "🟢 진행 중"

    channel_tabs = st.tabs([f"📌 {ch}" for ch in st.session_state.ota_channels])

    for i, ch_name in enumerate(st.session_state.ota_channels):
        with channel_tabs[i]:
            st.subheader(f"📝 {ch_name} 프로모션 현황판")
            
            state_key = f'promo_schedule_{ch_name}'
            if state_key not in st.session_state:
                today = datetime.date.today()
                initial_data = [
                    {"프로모션명": "예시 특가", "할인율(%)": 10, "시작일": today, "종료일": today + datetime.timedelta(days=7)}
                ]
                st.session_state[state_key] = pd.DataFrame(initial_data)

            df = st.session_state[state_key]
            df['상태'] = df.apply(get_status, axis=1)

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
            st.caption("💡 표 하단의 빈 공간을 클릭하면 새로운 프로모션을 추가할 수 있으며, 셀을 클릭하고 키보드 'Delete' 키를 누르면 삭제됩니다.")

# ==========================================
# TAB 5: 지능형 경영진 브리핑 리포트 
# ==========================================
with tab5:
    st.header("📋 지능형 경영진 브리핑 리포트")
    st.markdown("현재 시뮬레이션 데이터와 프로모션 현황을 AI처럼 분석하여 보고서 초안을 생성합니다.")

    report_ext_rate = int(base_rate_t3 / 0.65)
    report_hp_rate = int(base_rate_t3 * 0.8)
    
    analysis_results = []
    danger_channels = []
    
    if 'total_discount_pct_t' in locals():
        if final_price_t < report_hp_rate:
            danger_channels.append(f"트립닷컴(차액: {final_price_t - report_hp_rate:,}원)")
            
    if 'final_price_b' in locals():
        if final_price_b < report_hp_rate:
            danger_channels.append(f"부킹닷컴(차액: {final_price_b - report_hp_rate:,}원)")

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
            df['상태_임시'] = df.apply(get_status, axis=1)
            active = df[df['상태_임시'] == '🟢 진행 중']
            for _, row in active.iterrows():
                active_promos.append(f"   - {ch_name}: {row['프로모션명']} ({row['할인율(%)']}% 할인)")

    promo_summary = "\n".join(active_promos) if active_promos else "   - 현재 진행 중인 주요 특가 없음"

    dynamic_comment = ""
    if use_occ:
        dynamic_comment += f"* 현재 예상 점유율 {occ_pct}%에 맞춰 **{rate_level_t3}** 요금제를 전략적으로 선택하였습니다.\n"
    
    final_report = f"""
## [보고] 온라인 세일즈 전략 및 마진 분석 ({datetime.date.today().strftime('%Y-%m-%d')})

### 1. 요금 전략 핵심 지표
* **대상 객실:** {room_type_t3}
* **적용 요금제:** {rate_level_t3} (기준가: {base_rate_t3:,}원)
* **홈페이지 최저가:** {report_hp_rate:,}원
* **OTA 할증 등록가:** {report_ext_rate:,}원 (기준가 대비 35% 역산 인상)

### 2. 채널별 라이브 프로모션 현황
{promo_summary}

### 3. 실무 및 전략 제언
{dynamic_comment}
* OTA 채널의 높은 할인율(45%+)에도 불구하고 엑스트라넷 등록가 할증을 통해 **평균 {((report_ext_rate/base_rate_t3)-1)*100:.1f}%의 버퍼**를 확보했습니다.
* 현재 세팅 유지 시, 공식 홈페이지로의 예약 유도(Direct Booking) 경쟁력이 유지될 것으로 판단됩니다.
"""

    st.markdown(final_report)
    
    st.divider()
    st.download_button(
        label="📥 보고서 파일(TXT) 다운로드", 
        data=final_report, 
        file_name=f"Amber_Sales_Report_{datetime.date.today()}.txt"
    )

# ==========================================
# 👈 [신규 추가] TAB 6: 장기 요금 프로젝션 (오늘 ~ 12월)
# ==========================================
with tab6:
    st.header("🗓️ 장기 요금 프로젝션 (판매가 추이 분석)")
    st.markdown("사이드바에서 업로드된 마스터 요금표를 기반으로 연말까지의 **홈페이지가**와 **OTA별 최종 판매가**를 시뮬레이션합니다.")
    
    if st.session_state.master_rates.empty:
        st.warning("👈 사이드바 '장기 요금표 업데이트'에서 엑셀 파일을 먼저 업로드해주세요.")
    else:
        proj_room = st.selectbox("분석할 객실 타입 선택", DYNAMIC_ROOMS + list(FIXED_PRICE_TABLE.keys()), key="proj_room")
        
        room_data = st.session_state.master_rates[st.session_state.master_rates['RoomID'] == proj_room].copy()
        
        if room_data.empty:
            st.error("해당 객실에 대한 데이터가 엑셀 요금표에 없습니다.")
        else:
            room_data = room_data.sort_values('Date')
            # 오늘 이후 데이터만 필터링
            future_data = room_data[room_data['Date'] >= datetime.date.today()].copy()
            
            if future_data.empty:
                st.warning("오늘 이후의 요금 데이터가 없습니다.")
            else:
                # 1. 동적 요금 계산 로직
                future_data['기준가(BAR)'] = future_data['BaseRate'].astype(int)
                future_data['홈페이지(-20%)'] = (future_data['BaseRate'] * 0.8).astype(int)
                future_data['OTA등록가(/0.65)'] = (future_data['BaseRate'] / 0.65).astype(int)
                
                # 2. 탭 3의 승수를 가져와서 채널별 예상 최종가 자동 계산 (핵심 기능)
                future_data['트립 예상가'] = (future_data['OTA등록가(/0.65)'] * trip_mult).astype(int)
                future_data['부킹 예상가'] = (future_data['OTA등록가(/0.65)'] * bk_mult).astype(int)
                future_data['아고다 예상가'] = (future_data['OTA등록가(/0.65)'] * ag_mult).astype(int)
                
                future_data['날짜'] = future_data['Date'].apply(lambda x: x.strftime('%m/%d'))
                
                display_cols = ['날짜', '기준가(BAR)', '홈페이지(-20%)', 'OTA등록가(/0.65)', '트립 예상가', '부킹 예상가', '아고다 예상가']
                display_proj = future_data[display_cols]
                
                # 3. 가로형 표 (날짜가 가로축) 변환
                pivot_proj = display_proj.set_index('날짜').T
                
                st.write("---")
                st.subheader(f"🔍 {proj_room} 장기 요금 프로젝션 상세")
                st.caption("※ 각 채널별 예상가는 **'탭 3'에서 현재 세팅해둔 프로모션 할인율을 동일하게 적용**하여 동적으로 계산된 값입니다.")
                st.dataframe(pivot_proj, use_container_width=True)
                
                # 4. 시각화 그래프
                st.write("---")
                st.subheader("📈 채널별 패리티 변동 추이 그래프")
                chart_df = future_data.melt(id_vars=['Date'], 
                                            value_vars=['홈페이지(-20%)', '트립 예상가', '부킹 예상가', '아고다 예상가'], 
                                            var_name='채널', value_name='최종요금')
                fig_line = px.line(chart_df, x='Date', y='최종요금', color='채널', title=f"{proj_room} 채널별 최종 판매가 시뮬레이션")
                st.plotly_chart(fig_line, use_container_width=True)
