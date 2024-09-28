import requests

# API 엔드포인트 설정

# 1. 주간 아파트 매매가격지수
# 전체기간
API_URL = "https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/priceIndex?%EA%B8%B0%EA%B0%84=&%EB%A7%A4%EB%A7%A4%EC%A0%84%EC%84%B8%EC%BD%94%EB%93%9C=01&%EB%A7%A4%EB%AC%BC%EC%A2%85%EB%B3%84%EA%B5%AC%EB%B6%84=01&%EC%9B%94%EA%B0%84%EC%A3%BC%EA%B0%84%EA%B5%AC%EB%B6%84%EC%BD%94%EB%93%9C=02&%EC%A7%80%EC%97%AD%EC%BD%94%EB%93%9C=&%EC%A1%B0%ED%9A%8C%EC%8B%9C%EC%9E%91%EC%9D%BC%EC%9E%90=&%EC%A1%B0%ED%9A%8C%EC%A2%85%EB%A3%8C%EC%9D%BC%EC%9E%90=&type=false&%EB%A9%94%EB%89%B4%EC%BD%94%EB%93%9C=1"


# API 요청 함수
def get_real_estate_data():
    response = requests.get(API_URL)

    if response.status_code == 200:
        # JSON 데이터 반환
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")
