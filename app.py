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
        # 홈페이지 요금 적용 시 100원 단위 버림 처리 등 포맷팅
        return df.applymap(lambda x: f"{int(math.floor((x * multiplier)/1000)*1000):,}원" if pd.notnull(x) else "-")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("변동 요금제 (Dynamic)")
        st.dataframe(format_price_df(PRICE_TABLE), use_container_width=True)
    with col2:
        st.subheader("고정 요금제 (Fixed)")
        st.dataframe(format_price_df(FIXED_PRICE_TABLE), use_container_width=True)

# --- TAB 2: 요금 역산 및 수익 시뮬레이터 ---
with tab2:
    st.header("마크업(할증) 및 입금가(Net) 계산기")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        st.subheader("1. 조건 입력")
        room_type = st.selectbox("객실 타입", DYNAMIC_ROOMS + list(FIXED_PRICE_TABLE.keys()))
        
        # 선택한 객실에 따라 선택 가능한 요금 단계 변경
        if room_type in DYNAMIC_ROOMS:
            rate_level = st.selectbox("요금 단계", list(PRICE_TABLE[room_type].keys()))
            base_rate = PRICE_TABLE[room_type][rate_level]
        else:
            rate_level = st.selectbox("시즌/요일", list(FIXED_PRICE_TABLE[room_type].keys()))
            base_rate = FIXED_PRICE_TABLE[room_type][rate_level]
            
        st.write(f"**선택된 기준 요금:** {base_rate:,}원")
        
        st.divider()
        markup_pct = st.number_input("임의 요금 인상 (Markup %)", value=20, step=5)
        ota_discount_pct = st.number_input("OTA 요구 프로모션 할인 (%)", value=30, step=5)
        commission_pct = st.number_input("채널 수수료 (%)", value=15, step=1)
        
    with col_result:
        st.subheader("2. 시뮬레이션 결과")
        
        # 계산 로직
        website_rate = int(base_rate * 0.8) # 홈페이지 요금 (비교 기준)
        registered_price = int(base_rate * (1 + markup_pct/100)) # 엑스트라넷 등록가
        final_sell_price = int(registered_price * (1 - ota_discount_pct/100)) # 최종 고객 노출가
        net_price = int(final_sell_price * (1 - commission_pct/100)) # 호텔 실제 입금가
        
        diff_from_web = final_sell_price - website_rate
        
        # 메트릭 카드로 깔끔하게 표시
        st.write("---")
        m1, m2, m3 = st.columns(3)
        m1.metric(label="🌐 공식 홈페이지 요금 (기준 -20%)", value=f"{website_rate:,}원")
        m2.metric(label="⬆️ 엑스트라넷 등록가 (할증 적용)", value=f"{registered_price:,}원", delta=f"{markup_pct}% 인상")
        m3.metric(label="🛒 최종 OTA 판매가 (프로모션 적용)", value=f"{final_sell_price:,}원", delta=f"{-ota_discount_pct}% 할인", delta_color="inverse")
        
        st.write("---")
        st.metric(label="💰 최종 호텔 입금가 (Net Income)", value=f"{net_price:,}원", delta=f"수수료 {commission_pct}% 제외")
        
        # 인사이트 메시지
        if diff_from_web < 0:
            st.error(f"⚠️ **주의:** OTA 판매가가 자사 홈페이지보다 **{abs(diff_from_web):,}원** 더 저렴합니다. 마크업을 높이거나 할인을 줄이세요.")
        else:
            st.success(f"✅ **안전:** 홈페이지 요금보다 **{diff_from_web:,}원** 더 비싸게 세팅되어 채널 패리티가 방어됩니다.")

# --- TAB 3: 채널별 프로모션 매트릭스 ---
with tab3:
    st.header("주요 채널 최종 판매가 동시 비교")
    st.write("기준 요금 하나를 설정하면, 각 채널별로 설정된 프로모션 규칙에 따라 최종 판매가가 어떻게 변하는지 한눈에 봅니다.")
    
    sim_base_rate = st.number_input("테스트할 기준 요금 (원)", value=315000, step=10000)
    
    # 예시 프로모션 데이터 (원하는 대로 수정 가능)
    promo_data = [
        {"채널명": "Agoda", "마크업(%)": 15, "기본할인(%)": 10, "추가쿠폰(%)": 10, "할인방식": "복리"},
        {"채널명": "Booking.com", "마크업(%)": 20, "기본할인(%)": 15, "추가쿠폰(%)": 0, "할인방식": "합산"},
        {"채널명": "Expedia", "마크업(%)": 25, "기본할인(%)": 20, "추가쿠폰(%)": 10, "할인방식": "합산"},
        {"채널명": "Direct (홈페이지)", "마크업(%)": 0, "기본할인(%)": 20, "추가쿠폰(%)": 0, "할인방식": "합산"}
    ]
    
    results = []
    for p in promo_data:
        mark_price = sim_base_rate * (1 + p["마크업(%)"]/100)
        
        if p["할인방식"] == "복리":
            discounted = mark_price * (1 - p["기본할인(%)"]/100) * (1 - p["추가쿠폰(%)"]/100)
        else: # 합산
            total_discount = p["기본할인(%)"] + p["추가쿠폰(%)"]
            discounted = mark_price * (1 - total_discount/100)
            
        results.append({
            "채널명": p["채널명"],
            "등록 요금": f"{int(mark_price):,}원",
            "총 적용 할인율": f"{p['기본할인(%)']+p['추가쿠폰(%)']}% ({p['할인방식']})",
            "고객 최종 결제가": f"{int(discounted):,}원"
        })
        
    st.dataframe(pd.DataFrame(results), use_container_width=True)
    st.info("💡 위 프로모션 테이블은 하드코딩된 예시이며, 향후 st.data_editor를 붙여 직접 수치를 변경하게 업그레이드할 수 있습니다.")
