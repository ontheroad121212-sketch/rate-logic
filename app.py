import streamlit as st
import pandas as pd
import math
import datetime

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
    "GDB": {"UND1": 298000, "UND2": 298000, "MID1": 298000, "MID2": 298000, "UPP1": 298000, "UPP2": 298000},
    "GDF": {"UND1": 375000, "UND2": 410000, "MID1": 410000, "MID2": 488000, "UPP1": 488000, "UPP2": 578000},
    "FFD": {"UND1": 353000, "UND2": 393000, "MID1": 433000, "MID2": 482000, "UPP1": 539000, "UPP2": 604000},
    "FPT": {"UND1": 500000, "UND2": 550000, "MID1": 600000, "MID2": 650000, "UPP1": 700000, "UPP2": 750000},
    "PPV(온수O)": {"UND1": 1004000, "UND2": 1154000, "MID1": 1154000, "MID2": 1304000, "UPP1": 1304000, "UPP2": 1554000},
}

# --- 동적 채널 관리 세션 ---
if 'custom_channels' not in st.session_state:
    st.session_state.custom_channels = ["야놀자", "여기어때"] # 기본 생성해둘 커스텀 채널

st.title("🏨 앰버퓨어힐 요금 및 프로모션 통합 시뮬레이터")

# --- 사이드바: 커스텀 채널 추가 ---
with st.sidebar:
    st.header("⚙️ 새 채널 추가하기")
    st.write("트립닷컴, 부킹닷컴 외의 OTA를 탭으로 추가하세요.")
    new_ota = st.text_input("추가할 OTA 명칭 (예: 익스피디아)")
    
    if st.button("➕ 탭 생성"):
        if new_ota and new_ota not in st.session_state.custom_channels:
            st.session_state.custom_channels.append(new_ota)
            st.rerun()
            
    st.divider()
    if st.button("🗑️ 추가된 채널 모두 지우기"):
        st.session_state.custom_channels = []
        st.rerun()

# --- 동적 탭 구성 ---
# 기존 4개 탭 + 사용자가 추가한 커스텀 채널 탭들을 합칩니다.
tab_names = ["📊 1. 기준 요금표", "🧮 2. 요금 역산 시뮬", "🧱 3. 트립/부킹 실전", "📅 4. 프로모션 스케줄"] + [f"🏢 {ch}" for ch in st.session_state.custom_channels]
tabs = st.tabs(tab_names)

tab1, tab2, tab3, tab4 = tabs[0], tabs[1], tabs[2], tabs[3]
custom_tabs = tabs[4:]

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
# TAB 2: 전략적 요금 할증 & 패리티 시뮬레이터
# ==========================================
with tab2:
    st.header("🧮 전략적 요금 할증 & 패리티 시뮬레이터")
    st.write("인상 방식부터 할인율까지 모든 변수를 조절하여 최적의 OTA 등록가를 찾습니다.")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        st.subheader("1. 기준 및 할증 설정")
        room_type = st.selectbox("객실 타입", DYNAMIC_ROOMS + list(FIXED_PRICE_TABLE.keys()), index=2, key="t2_room") 
        if room_type in DYNAMIC_ROOMS:
            rate_level = st.selectbox("요금 단계", list(PRICE_TABLE[room_type].keys()), index=2, key="t2_rate") 
            base_rate = PRICE_TABLE[room_type][rate_level]
        else:
            rate_level = st.selectbox("시즌/요일", list(FIXED_PRICE_TABLE[room_type].keys()), key="t2_rate")
            base_rate = FIXED_PRICE_TABLE[room_type][rate_level]
            
        st.info(f"**선택된 기준 요금:** {base_rate:,}원")
        
        st.divider()
        markup_method = st.radio("마크업 계산 방식", ["역산 방식 (/ 0.xx)", "단순 가산 방식 (* 1.xx)"], key="t2_markup_m")
        markup_val = st.number_input("마크업 비율 (%)", value=35, step=1, key="t2_markup_v")
        
        st.divider()
        ota_discount_val = st.number_input("OTA 프로모션 할인 (%)", value=45, step=1, key="t2_ota_d")
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

# ==========================================
# TAB 3: 트립닷컴 / 부킹닷컴 실전 (사용자 오리지널 로직)
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
    
    sub_tab1, sub_tab2 = st.tabs(["🔵 트립닷컴 (완벽 합산형)", "🟦 부킹닷컴 (조건부 복리형)"])
    
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

# ==========================================
# TAB 4: 프로모션 스케줄 및 현황 관리
# ==========================================
with tab4:
    st.header("📅 채널별 프로모션 스케줄 및 현황 관리")
    st.markdown("각 OTA 채널에 세팅해 둔 프로모션의 기간과 할인율을 기록하고 관리합니다.")

    if 'promo_schedule' not in st.session_state:
        today = datetime.date.today()
        initial_data = [
            {"채널명": "Trip.com", "프로모션명": "Spring Early Bird", "그룹(구분)": "Group 1", "할인율(%)": 10, "시작일": today, "종료일": today + datetime.timedelta(days=30)},
            {"채널명": "Booking.com", "프로모션명": "모바일 타겟 요금", "그룹(구분)": "타겟 요금", "할인율(%)": 10, "시작일": today - datetime.timedelta(days=10), "종료일": today + datetime.timedelta(days=90)},
            {"채널명": "Agoda", "프로모션명": "24h 팝업 특가", "그룹(구분)": "타임세일", "할인율(%)": 45, "시작일": today - datetime.timedelta(days=2), "종료일": today - datetime.timedelta(days=1)},
        ]
        st.session_state.promo_schedule = pd.DataFrame(initial_data)

    df = st.session_state.promo_schedule
    today_dt = pd.to_datetime(datetime.date.today())
    
    def get_status(row):
        start = pd.to_datetime(row['시작일'])
        end = pd.to_datetime(row['종료일'])
        if pd.isna(start) or pd.isna(end):
            return "⚪ 미정"
        elif end < today_dt:
            return "⚫ 종료됨"
        elif start > today_dt:
            return "🟡 진행 예정"
        else:
            return "🟢 진행 중"

    df['상태'] = df.apply(get_status, axis=1)

    st.subheader("📝 프로모션 관리 대시보드")
    
    # 📌 동적으로 추가된 채널 목록을 에디터의 드롭다운 옵션에 합칩니다!
    all_channel_options = ["Trip.com", "Booking.com", "Agoda", "Expedia", "Direct(홈페이지)"] + st.session_state.custom_channels
    filter_ch = st.multiselect("특정 채널 필터링", options=all_channel_options)
    display_df = df if not filter_ch else df[df['채널명'].isin(filter_ch)]

    edited_df = st.data_editor(
        display_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "채널명": st.column_config.SelectboxColumn(options=all_channel_options, required=True),
            "프로모션명": st.column_config.TextColumn(required=True),
            "할인율(%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1, format="%d%%"),
            "시작일": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "종료일": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "상태": st.column_config.TextColumn(disabled=True) 
        }
    )

    st.session_state.promo_schedule = edited_df.drop(columns=['상태'])
    st.caption("💡 표 하단의 빈 공간을 클릭하면 새로운 프로모션을 추가할 수 있으며, 셀을 클릭하고 'Delete' 키를 누르면 삭제됩니다.")

# ==========================================
# TAB 5 ~ : 사용자 정의 채널 탭 (야놀자, 여기어때 등)
# ==========================================
for i, tab in enumerate(custom_tabs):
    ch_name = st.session_state.custom_channels[i]
    with tab:
        st.header(f"📊 {ch_name} 전용 전략 시뮬레이터")
        st.markdown(f"사이드바에서 추가하신 **{ch_name}**의 특가 중복 로직을 시뮬레이션합니다.")
        
        c1, c2 = st.columns(2)
        with c1:
            room_dyn = st.selectbox("객실 타입", DYNAMIC_ROOMS + list(FIXED_PRICE_TABLE.keys()), index=2, key=f"dyn_room_{ch_name}")
        with c2:
            if room_dyn in DYNAMIC_ROOMS:
                rate_dyn = st.selectbox("요금 단계", list(PRICE_TABLE[room_dyn].keys()), index=2, key=f"dyn_rate_{ch_name}")
                base_dyn = PRICE_TABLE[room_dyn][rate_dyn]
            else:
                rate_dyn = st.selectbox("시즌/요일", list(FIXED_PRICE_TABLE[room_dyn].keys()), key=f"dyn_rate_{ch_name}")
                base_dyn = FIXED_PRICE_TABLE[room_dyn][rate_dyn]
                
        hp_rate = int(base_dyn * 0.8)
        ext_rate = int(base_dyn / 0.65)
        
        st.info(f"**[{room_dyn} - {rate_dyn}]** 홈페이지 사수선: **{hp_rate:,}원** / 엑스트라넷 박제 요금: **{ext_rate:,}원**")
        st.divider()
        
        col_ctrl, col_view = st.columns([1, 2])
        
        with col_ctrl:
            st.subheader("채널 프로모션 설정")
            calc_type = st.radio("다중 할인 계산 방식", ["합산형 (할인율을 모두 더함)", "복리형 (순차적으로 차감)"], key=f"calc_{ch_name}")
            
            st.write(f"**{ch_name} 활성화 프로모션**")
            if f'promo_df_{ch_name}' not in st.session_state:
                st.session_state[f'promo_df_{ch_name}'] = pd.DataFrame([{"프로모션명": "특가 기획전", "할인율(%)": 10}])
            
            edited_promo_dyn = st.data_editor(st.session_state[f'promo_df_{ch_name}'], num_rows="dynamic", key=f"edit_{ch_name}", use_container_width=True)
            st.session_state[f'promo_df_{ch_name}'] = edited_promo_dyn

        with col_view:
            st.subheader("최종 가격 및 패리티 확인")
            
            promo_list = edited_promo_dyn['할인율(%)'].tolist()
            if calc_type == "합산형 (할인율을 모두 더함)":
                total_disc = min(sum(promo_list), 100)
                final_p = int(ext_rate * (1 - total_disc/100))
                desc = f"총 {total_disc}% 합산 차감"
            else:
                curr_p = float(ext_rate)
                for d in promo_list:
                    curr_p *= (1 - d/100)
                final_p = int(curr_p)
                desc = "순차(복리) 차감 적용"
            
            diff = final_p - hp_rate
            
            md1, md2 = st.columns(2)
            md1.metric(f"{ch_name} 최종 결제가", f"{final_p:,}원", desc, delta_color="inverse")
            if diff >= 0:
                md2.success(f"✅ **패리티 안전:** 홈피보다 {diff:,}원 비쌈")
            else:
                md2.error(f"🚨 **패리티 위험:** 홈피보다 {abs(diff):,}원 저렴함")
