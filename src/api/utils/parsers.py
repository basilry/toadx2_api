import re
from datetime import datetime, timedelta

# 파싱된 결과에 기본값을 추가하는 함수
def fill_parsing_defaults(parsed_text):
    try:
        # 불필요한 공백 및 개행 제거
        parsed_text = re.sub(r"\s+", " ", parsed_text)
        print(parsed_text)

        # 각 필드 추출
        region_match = re.search(r"지역:\s*([가-힣\s]+)", parsed_text)
        deal_type_match = re.search(r"매매/전세 여부:\s*(매매|전세)", parsed_text)
        time_info_match = re.search(r"시간 정보:\s*([0-9년월일\s]+)", parsed_text)

        # 추출된 값이 없으면 기본값으로 대체
        region = region_match.group(1).strip() if region_match else "전국"
        deal_type = deal_type_match.group(1) if deal_type_match else "매매"
        time_info = time_info_match.group(1).strip() if time_info_match else "현재"

        print("================파싱결과====================")
        print(region, deal_type, time_info)

        return {
            "지역": region,
            "매매/전세 여부": 'sale' if deal_type == '매매' else 'rent',
            "시간 정보": time_info
        }
    except Exception as e:
        print(f"파싱 오류: {e}")
        # 오류 발생 시 기본값 반환
        return {
            "지역": "전국",
            "매매/전세 여부": "sale",
            "시간 정보": "현재"
        }

# 데이터 포맷팅 함수
def format_price_data(region_name, price_data):
    """
    부동산 가격 데이터를 포맷하는 함수.
    """
    formatted_price_data = []
    for item in price_data:
        prediction_mark = " (예측치)" if item.get('is_prediction', False) else ""
        formatted_price_data.append(
            f"- 날짜: {item['date']}, 거래 유형: {item['deal_type']}, 평균 가격: {item['price'] * 10000:,}원{prediction_mark}"
        )
    return "\n".join(formatted_price_data)

# 분석 요약 생성 함수
def generate_analysis_summary(price_data):
    """
    가격 데이터를 분석하고 요약 생성.
    """
    avg_price = sum(item['price'] for item in price_data) / len(price_data)
    trend = "상승" if price_data[-1]['price'] > price_data[0]['price'] else "하락"
    return f"최근 평균 가격은 {avg_price * 10000:,.0f}원이며, 가격 추이는 {trend}세입니다." 