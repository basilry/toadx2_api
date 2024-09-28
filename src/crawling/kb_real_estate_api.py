import requests

# API 엔드포인트 설정

# 1. 주간 아파트 매매가격지수
WEEKLY_APARTMENT_SALE_COST_INDEX = "https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/priceIndex?%EA%B8%B0%EA%B0%84=&%EB%A7%A4%EB%A7%A4%EC%A0%84%EC%84%B8%EC%BD%94%EB%93%9C=01&%EB%A7%A4%EB%AC%BC%EC%A2%85%EB%B3%84%EA%B5%AC%EB%B6%84=01&%EC%9B%94%EA%B0%84%EC%A3%BC%EA%B0%84%EA%B5%AC%EB%B6%84%EC%BD%94%EB%93%9C=02&%EC%A7%80%EC%97%AD%EC%BD%94%EB%93%9C=&%EC%A1%B0%ED%9A%8C%EC%8B%9C%EC%9E%91%EC%9D%BC%EC%9E%90=&%EC%A1%B0%ED%9A%8C%EC%A2%85%EB%A3%8C%EC%9D%BC%EC%9E%90=&type=false&%EB%A9%94%EB%89%B4%EC%BD%94%EB%93%9C=1"

# 2. 주간 아파트 전세가격지수
WEEKLY_APARTMENT_RENT_COST_INDEX = "https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/priceIndex?%EA%B8%B0%EA%B0%84=&%EB%A7%A4%EB%A7%A4%EC%A0%84%EC%84%B8%EC%BD%94%EB%93%9C=02&%EB%A7%A4%EB%AC%BC%EC%A2%85%EB%B3%84%EA%B5%AC%EB%B6%84=01&%EC%9B%94%EA%B0%84%EC%A3%BC%EA%B0%84%EA%B5%AC%EB%B6%84%EC%BD%94%EB%93%9C=02&%EC%A7%80%EC%97%AD%EC%BD%94%EB%93%9C=&%EC%A1%B0%ED%9A%8C%EC%8B%9C%EC%9E%91%EC%9D%BC%EC%9E%90=&%EC%A1%B0%ED%9A%8C%EC%A2%85%EB%A3%8C%EC%9D%BC%EC%9E%90=&type=false&%EB%A9%94%EB%89%B4%EC%BD%94%EB%93%9C=1"

# 3. 월간 아파트 매매가격지수
MONTHLY_APARTMENT_SALE_COST_INDEX = "https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/priceIndex?title=%EC%9B%94%EA%B0%84+%EC%95%84%ED%8C%8C%ED%8A%B8+%EB%A7%A4%EB%A7%A4%EA%B0%80%EA%B2%A9%EC%A7%80%EC%88%98&%EB%A7%A4%EB%A7%A4%EC%A0%84%EC%84%B8%EC%BD%94%EB%93%9C=01&%EB%A7%A4%EB%AC%BC%EC%A2%85%EB%B3%84%EA%B5%AC%EB%B6%84=01&%EC%9B%94%EA%B0%84%EC%A3%BC%EA%B0%84%EA%B5%AC%EB%B6%84%EC%BD%94%EB%93%9C=01&type=true&apiFlag=priceIndex&%EB%A9%94%EB%89%B4%EC%BD%94%EB%93%9C=1&%EB%8B%A8%EC%9C%84=(%EA%B8%B0%EC%A4%80:2022.1+%3D+100.0)"

# 4. 월간 아파트 전세가격지수
MONTHLY_APARTMENT_RENT_COST_INDEX = "https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/priceIndex?title=%EC%9B%94%EA%B0%84+%EC%95%84%ED%8C%8C%ED%8A%B8+%EC%A0%84%EC%84%B8%EA%B0%80%EA%B2%A9%EC%A7%80%EC%88%98&%EB%A7%A4%EB%A7%A4%EC%A0%84%EC%84%B8%EC%BD%94%EB%93%9C=02&%EB%A7%A4%EB%AC%BC%EC%A2%85%EB%B3%84%EA%B5%AC%EB%B6%84=01&%EC%9B%94%EA%B0%84%EC%A3%BC%EA%B0%84%EA%B5%AC%EB%B6%84%EC%BD%94%EB%93%9C=01&type=true&apiFlag=priceIndex&%EB%A9%94%EB%89%B4%EC%BD%94%EB%93%9C=1&%EB%8B%A8%EC%9C%84=(%EA%B8%B0%EC%A4%80:2022.1+%3D+100.0)"

# 5. 월별 아파트 매매평균가격
MONTHLY_APARTMENT_SALE_COST_AVG = "https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/avgPrc?%EB%A7%A4%EB%AC%BC%EC%A2%85%EB%B3%84%EA%B5%AC%EB%B6%84=01&%EB%A7%A4%EB%A7%A4%EC%A0%84%EC%84%B8%EC%BD%94%EB%93%9C=01"

# 6. 월별 아파트 전세평균가격
MONTHLY_APARTMENT_RENT_COST_AVG = "https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/avgPrc?%EB%A7%A4%EB%AC%BC%EC%A2%85%EB%B3%84%EA%B5%AC%EB%B6%84=01&%EB%A7%A4%EB%A7%A4%EC%A0%84%EC%84%B8%EC%BD%94%EB%93%9C=02"


# API 요청 함수
def get_weekly_apartment_sale_cost_index():
    """주간 아파트 매매가격지수를 가져오는 함수"""
    response = requests.get(WEEKLY_APARTMENT_SALE_COST_INDEX)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")


def get_weekly_apartment_rent_cost_index():
    """주간 아파트 전세가격지수를 가져오는 함수"""
    response = requests.get(WEEKLY_APARTMENT_RENT_COST_INDEX)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")


def get_monthly_apartment_sale_cost_index():
    """월간 아파트 매매가격지수를 가져오는 함수"""
    response = requests.get(MONTHLY_APARTMENT_SALE_COST_INDEX)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")


def get_monthly_apartment_rent_cost_index():
    """월간 아파트 전세가격지수를 가져오는 함수"""
    response = requests.get(MONTHLY_APARTMENT_RENT_COST_INDEX)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")


def get_monthly_apartment_sale_cost_avg():
    """월별 아파트 매매평균가격을 가져오는 함수"""
    response = requests.get(MONTHLY_APARTMENT_SALE_COST_AVG)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")


def get_monthly_apartment_rent_cost_avg():
    """월별 아파트 전세평균가격을 가져오는 함수"""
    response = requests.get(MONTHLY_APARTMENT_RENT_COST_AVG)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 호출 실패: {response.status_code}, {response.text}")
