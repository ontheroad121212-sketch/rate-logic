import streamlit as st
import pandas as pd

st.set_page_config(page_title="OTA 요금 할증 시뮬레이터", layout="wide")

st.title("🏨 OTA 캠페인 요금 할증(Markup) 시뮬레이터")
st.markdown("기준 요금(BAR)을 방어하면서 OTA의 고배율 할인 프로모션에 참여하기 위한 엑스트라넷 등록 요금을 계산합니다.")

# 1. 기준 요금 및 목표 설정 (사이드바)
with st.sidebar:
    st.header("1. 기준 요금 & 목표 설정")
    bar_price = st.number_input("기준 요금 (BAR)", value=250000, step=10000)
    
    st.subheader("허용 가능한 실제 할인율")
    min_discount = st.slider("최소 할인율 (%)", 0, 50, 10)
    max_discount = st.slider("최대 할인율 (%)", 0, 50, 20)
    
    # 목표 판매가 계산
    target_max_price = bar_price * (1 - (min_discount / 100))
    target_min_price = bar_price * (1 - (max_discount / 100))
    
    st.info(f"**우리의 목표 판매가 범위:**\n\n{int(target_min_price):,}원 ~ {int(target_max_price):,}원")

# 2. OTA 채널별 시뮬레이션
st.header("2. 채널별 프로모션 시뮬레이션")

col1, col2 = st.columns(2)

with col1:
    st.subheader("채널 A (예: 35~45% 할인 요구)")
    ota_a_name = st.text_input("채널명 입력 (A)", "OTA Channel A")
    ota_a_discount = st.slider(f"{ota_a_name} 총 요구 할인율 (%)", 0, 80, 40)
    
    # 역산 로직: 목표 최저가 기준 할증 요금 계산
    # 목표 금액 = 등록요금 * (1 - OTA할인율)  =>  등록요금 = 목표 금액 / (1 - OTA할인율)
    if ota_a_discount < 100:
        markup_price_a = target_min_price / (1 - (ota_a_discount / 100))
        actual_sell_price_a = markup_price_a * (1 - (ota_a_discount / 100))
        
        st.success(f"**추천 엑스트라넷 등록 요금: {int(markup_price_a):,}원**")
        st.write(f"👉 이 요금으로 등록 후 **{ota_a_discount}%** 할인이 적용되면, 최종 판매가는 **{int(actual_sell_price_a):,}원**이 됩니다. (기준가 대비 실제 할인율: {max_discount}%)")
    else:
        st.error("할인율은 100% 미만이어야 합니다.")

with col2:
    st.subheader("채널 B (중복 할인 구조)")
    ota_b_name = st.text_input("채널명 입력 (B)", "OTA Channel B")
    st.markdown("할인 중복 적용 방식 (복리 계산)")
    
    b_promo_1 = st.number_input("기본 프로모션 할인 (%)", value=20)
    b_promo_2 = st.number_input("추가 쿠폰/멤버십 할인 (%)", value=15)
    
    # 복리(순차) 할인 계산: (1 - 0.20) * (1 - 0.15) = 0.8 * 0.85 = 0.68 (즉 32% 총 할인)
    total_b_discount_rate = 1 - ((1 - b_promo_1/100) * (1 - b_promo_2/100))
    
    if total_b_discount_rate < 1:
        markup_price_b = target_min_price / (1 - total_b_discount_rate)
        actual_sell_price_b = markup_price_b * (1 - total_b_discount_rate)
        
        st.info(f"**실제 적용되는 총 OTA 할인율: {total_b_discount_rate*100:.1f}%**")
        st.success(f"**추천 엑스트라넷 등록 요금: {int(markup_price_b):,}원**")
        st.write(f"👉 이 요금으로 등록 시 최종 판매가는 **{int(actual_sell_price_b):,}원**입니다.")

# 3. 요약 테이블
st.header("3. 요금 설정 요약 테이블")
summary_data = {
    "채널명": [ota_a_name, ota_b_name],
    "OTA 표면상 할인율": [f"{ota_a_discount}%", f"{total_b_discount_rate*100:.1f}%"],
    "엑스트라넷 등록가(할증)": [f"{int(markup_price_a):,}원", f"{int(markup_price_b):,}원"],
    "최종 판매가": [f"{int(actual_sell_price_a):,}원", f"{int(actual_sell_price_b):,}원"],
    "BAR 대비 실제 할인율": [f"{max_discount}%", f"{max_discount}%"]
}

st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
