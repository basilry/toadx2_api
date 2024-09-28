import logging
import os

import requests
import xmltodict
from dotenv import load_dotenv
from fastapi import APIRouter

load_dotenv()
router = APIRouter()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.DEBUG)

koreaLandUrl = os.getenv('KOREA_LAND_API_URL')
ministryUrl = os.getenv('MINISTRY_OF_LAND_API_URL')
encodingKey = os.getenv('ENCODING_KEY')
decodingKey = os.getenv('DECODING_KEY')


# 국토교통부 아파트 실거래가 Open API를 활용한 부동산 데이터 지역별/날짜별 조회
@router.get("/ministry/{lawd_cd}/{deal_ymd}")
def get_sale_cost_from_ministry(lawd_cd: str, deal_ymd: str):
    params = {
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
    }
    url = ministryUrl + '/getRTMSDataSvcAptTrade' + f'?serviceKey={encodingKey}'

    print(url)

    response = requests.get(url, params=params)

    print(response.text)

    if response.status_code == 200:
        data_dict = xmltodict.parse(response.content)

        items = data_dict['response']['body']['items']['item']
        return items
    else:
        return {"error": "Failed to fetch data"}


# 한국부동산원 월별/지역별 아파트 매매가격지수 동향 조회
@router.get("/korea-land/sale-index/{page}")
def get_sale_index_from_korea_land(page: int):
    params = {
        'page': page,
        'perPage': 10,
    }
    url = koreaLandUrl + '/15069826/v1/uddi:754c056e-8dea-4201-8a61-88e56da67e83' + f'?serviceKey={encodingKey}'

    response = requests.get(url, params=params)

    if response.status_code == 200:
        json_data = response.json()

        return json_data
    else:
        return {"error": "Failed to fetch data"}


# 한국부동산원 월별 아파트 평균 매매가격 조회
@router.get("/korea-land/sale-cost/{page}")
def get_sale_avg_cost_from_korea_land(page: int):
    params = {
        'page': page,
        'perPage': 10,
    }
    url = koreaLandUrl + '/15069826/v1/uddi:c921d88a-6deb-4904-a658-e1fdb5437c92' + f'?serviceKey={encodingKey}'

    response = requests.get(url, params=params)

    if response.status_code == 200:
        json_data = response.json()

        return json_data
    else:
        return {"error": "Failed to fetch data"}


# 한국부동산원 월별/지역별 아파트 전세가격지수 동향 조회
@router.get("/korea-land/rent-index/{page}")
def get_rent_index_from_korea_land(page: int):
    params = {
        'page': page,
        'perPage': 10,
    }
    url = koreaLandUrl + '/15044018/v1/uddi:dd77d0b6-6927-46f4-884c-b5a0c1751b65' + f'?serviceKey={encodingKey}'

    response = requests.get(url, params=params)

    if response.status_code == 200:
        json_data = response.json()

        return json_data
    else:
        return {"error": "Failed to fetch data"}


# 한국부동산원 월별 아파트 평균 전세가격 조회
@router.get("/korea-land/rent-cost/{page}")
def get_rent_avg_cost_from_korea_land(page: int):
    params = {
        'page': page,
        'perPage': 10,
    }

    url = f'{koreaLandUrl}/15067573/v1/uddi:d2dae93c-51eb-4873-983e-a71fdf4835f9?serviceKey={encodingKey}'

    response = requests.get(url, params=params)

    if response.status_code == 200:
        json_data = response.json()

        return json_data
    else:
        return {"error": "Failed to fetch data"}
