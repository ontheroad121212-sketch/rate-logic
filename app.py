import streamlit as st
import pandas as pd
import math

# --- 1. 전역 설정 및 데이터 ---
st.set_page_config(page_title="요금 시뮬레이터", layout="wide")

# 앰버 퓨어 힐 객실 데이터 (제공된 코드에서 추출)
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
    "PPV(온수O)": {"UND1": 1004000, "UND2": 1154000, "MID1": 1154000, "MID2": 1304000, "UPP1": 1304000, "UPP2": 1554000}, # 제공해주신 데이터 기준 반영
}

st.title("🏨 요금 및 프로모션 시뮬레이터")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📊 1. 전체 기준 요금표", "🧮 2. 요금 역산 시뮬레이터", "전략 3. 채널별 최종 판매가 비교"])

# --- TAB 1: 전체 기준 요금표 (언제든 열람 & 홈페이지만 -20% 비교) ---
with tab1:
    st.header("전체 객실 기준 요금 (Master Rate)")
    
    # 홈페이지 요금 토글
    show_direct_rate = st.toggle("🌐 홈페이지 요금 보기 (기준가 -20% 적용)")
    multiplier = 0.8 if show_direct_rate else 1.0
    
    def format_price_df(data_dict):
        df = pd.DataFrame(data_dict).T
        # applymap -> map 으로 이름만 변경
        return df.map(lambda x: f"{int(math.floor((x * multiplier)/1000)*1000):,}원" if pd.notnull(x) else "-")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("변동 요금제 (Dynamic)")
        st.dataframe(format_price_df(PRICE_TABLE), use_container_width=True)
    with col2:
        st.subheader("고정 요금제 (Fixed)")
        st.dataframe(format_price_df(FIXED_PRICE_TABLE), use_container_width=True)

with tab2:
    st.header("🧮 전략적 요금 할증 & 패리티 시뮬레이터")
    st.write("인상 방식부터 할인율까지 모든 변수를 조절하여 최적의 OTA 등록가를 찾습니다.")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        st.subheader("1. 기준 및 할증 설정")
        # 객실 및 기준가 선택
        room_type = st.selectbox("객실 타입", DYNAMIC_ROOMS + list(FIXED_PRICE_TABLE.keys()), index=2) # 기본 FDB
        if room_type in DYNAMIC_ROOMS:
            rate_level = st.selectbox("요금 단계", list(PRICE_TABLE[room_type].keys()), index=2) # 기본 BAR6
            base_rate = PRICE_TABLE[room_type][rate_level]
        else:
            rate_level = st.selectbox("시즌/요일", list(FIXED_PRICE_TABLE[room_type].keys()))
            base_rate = FIXED_PRICE_TABLE[room_type][rate_level]
            
        st.info(f"**선택된 기준 요금:** {base_rate:,}원")
        
        st.divider()
        # 할증(Markup) 방식 선택
        markup_method = st.radio("마크업 계산 방식", ["역산 방식 (/ 0.xx)", "단순 가산 방식 (* 1.xx)"])
        markup_val = st.number_input("마크업 비율 (%)", value=35, step=1)
        
        st.divider()
        # 할인 및 수수료 설정
        ota_discount_val = st.number_input("OTA 프로모션 할인 (%)", value=45, step=1)
        commission_val = st.number_input("채널 수수료 (%)", value=15, step=1)
        
    with col_result:
        st.subheader("2. 시뮬레이션 결과")
        
        # 1. 홈페이지 판매가 (-20%)
        web_price = int(base_rate * 0.8)
        
        # 2. 엑스트라넷 등록가 계산
        if markup_method == "역산 방식 (/ 0.xx)":
            reg_price = int(base_rate / (1 - markup_val/100)) if markup_val < 100 else 0
        else:
            reg_price = int(base_rate * (1 + markup_val/100))
            
        # 3. 최종 OTA 판매가 및 입금가
        final_ota_price = int(reg_price * (1 - ota_discount_val/100))
        net_income = int(final_ota_price * (1 - commission_val/100))
        
        # 4. 패리티 비교
        price_diff = final_ota_price - web_price
        
        # 결과 대시보드 표시
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
            
# --- TAB 3: 채널별 실전 프로모션 중복(Stacking) 시뮬레이터 ---
with tab3:
    st.header("🧱 주요 OTA 실전 Stacking 시뮬레이터")
    st.markdown("채널별 고유의 프로모션 중복 규칙을 적용하여, 할인이 겹쳤을 때 최종 판매가가 어떻게 변하는지 확인합니다.")
    
    # 엑스트라넷 박제 요금 입력
    test_base_rate = st.number_input("테스트할 엑스트라넷 등록 요금 (Selling Rate)", value=609231, step=10000)
    st.write("---")
    
    # 트립닷컴과 부킹닷컴을 서브 탭으로 분리하여 관리
    sub_tab1, sub_tab2 = st.tabs(["🔵 트립닷컴 (합산형)", "🟦 부킹닷컴 (조건부 복리형)"])
    
    with sub_tab1:
        st.subheader("트립닷컴 실전 시뮬레이션")
        st.markdown("트립닷컴은 활성화된 프로모션의 %를 모두 더해 한 번에 깎는 **합산형** 방식을 주로 사용합니다.")
        
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            g1_promo = st.radio("Group 1 (기본 딜)", ["적용 안함", "Basic Deal", "Early Bird"])
            g1_rate = st.number_input("Group 1 할인율(%)", value=10, step=1) if g1_promo != "적용 안함" else 0
        with col_t2:
            g2_mobile = st.toggle("📱 모바일 요금 (Group 2)")
            g2_rate = st.number_input("모바일 할인율(%)", value=15, step=1) if g2_mobile else 0
        with col_t3:
            g5_member = st.toggle("👑 트립플러스 (Group 5)")
            g5_rate = st.number_input("트립플러스 할인율(%)", value=15, step=1) if g5_member else 0

        # 트립닷컴 합산 계산 로직
        total_discount_pct_t = min(g1_rate + g2_rate + g5_rate, 100)
        final_price_t = int(test_base_rate * (1 - total_discount_pct_t / 100))
        
        st.info(f"**적용 방식:** {g1_rate}% + {g2_rate}% + {g5_rate}% = 총 {total_discount_pct_t}% 합산 차감")
        st.metric("🔵 트립닷컴 고객 최종 결제가", f"{final_price_t:,}원")

    # ==========================================
    # 부킹닷컴 전용 로직 시작
    # ==========================================
    with sub_tab2:
        st.subheader("부킹닷컴 실전 시뮬레이션")
        st.markdown("부킹닷컴은 카테고리별로 중복 가능 여부가 엄격하며, 할인이 겹칠 때 **순차적 차감(복리형)**이 적용됩니다.")
        
        col_b1, col_b2, col_b3 = st.columns(3)
        
        with col_b1:
            st.markdown("#### 1. 집중형 특가")
            st.caption("※ Deep deals: 타 할인과 절대 중복 불가")
            is_deep = st.toggle("기간 한정 특가 (블랙프라이데이 등)")
            deep_rate = st.number_input("집중형 특가 할인율(%)", value=30, step=1) if is_deep else 0
            
        with col_b2:
            st.markdown("#### 2. 캠페인 특가")
            st.caption("※ Genius와만 중복 가능")
            camp_promo = st.selectbox("캠페인 선택", ["선택 안함", "휴가 특가", "2026 새해맞이 특가"])
            camp_rate = st.number_input("캠페인 할인율(%)", value=20, step=1) if camp_promo != "선택 안함" else 0
            
        with col_b3:
            st.markdown("#### 3. 타겟 & 포트폴리오")
            st.caption("※ Genius 및 상호 간 중복 가능")
            is_genius = st.toggle("Genius 프로그램", value=True)
            genius_rate = st.number_input("Genius 할인율(%)", value=10, step=1) if is_genius else 0
            
            target_promo = st.selectbox("타겟 요금", ["선택 안함", "모바일 할인", "국가별 특가"])
            target_rate = st.number_input("타겟 할인율(%)", value=10, step=1) if target_promo != "선택 안함" else 0
            
            port_promo = st.selectbox("포트폴리오 특가", ["선택 안함", "베이직 특가", "조기 예약 특가"])
            port_rate = st.number_input("포트폴리오 할인율(%)", value=10, step=1) if port_promo != "선택 안함" else 0

        st.write("---")
        st.subheader("🧾 부킹닷컴 최종 요금 산출 결과")
        
        # [핵심 로직] 배타적 트랙 계산
        if is_deep:
            # 트랙 1: 집중형 특가 단독
            final_price_b = int(test_base_rate * (1 - deep_rate/100))
            active_path = "집중형 특가 (단독 적용 트랙)"
            applied_list = [f"Deep Deal ({deep_rate}%)"]
        else:
            # 트랙 2: Genius + 캠페인 (복리)
            price_path_camp = test_base_rate * (1 - genius_rate/100) * (1 - camp_rate/100)
            
            # 트랙 3: Genius + 타겟 + 포트폴리오 (복리)
            price_path_port = test_base_rate * (1 - genius_rate/100) * (1 - target_rate/100) * (1 - port_rate/100)
            
            # 부킹닷컴은 고객에게 더 유리한(최종가가 더 낮은) 조합을 자동 적용함
            if camp_promo != "선택 안함" and price_path_camp < price_path_port:
                final_price_b = int(price_path_camp)
                active_path = "Genius + 캠페인 특가 트랙"
                applied_list = [f"Genius ({genius_rate}%)", f"{camp_promo} ({camp_rate}%)"]
            else:
                final_price_b = int(price_path_port)
                active_path = "Genius + 타겟/포트폴리오 트랙"
                applied_list = [f"Genius ({genius_rate}%)"]
                if target_promo != "선택 안함": applied_list.append(f"{target_promo} ({target_rate}%)")
                if port_promo != "선택 안함": applied_list.append(f"{port_promo} ({port_rate}%)")

        # 시각적 결과 출력
        promo_text_b = " ➔ ".join(applied_list) if applied_list != [f"Genius (0%)"] else "적용된 할인 없음"
        
        st.success(f"**활성화된 중복 규칙:** {active_path}\n\n**순차 차감(복리) 순서:** {promo_text_b}")
        
        rb1, rb2, rb3 = st.columns(3)
        rb1.metric("1. 엑스트라넷 판매가", f"{test_base_rate:,}원")
        rb2.metric("2. 총 할인 금액", f"-{(test_base_rate - final_price_b):,}원", "조건부 복리 계산됨", delta_color="inverse")
        rb3.metric("🟦 부킹닷컴 고객 최종 결제가", f"{final_price_b:,}원", "홈페이지 요금과 패리티를 비교하세요", delta_color="off")
