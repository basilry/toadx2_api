import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# 크롬 드라이버 경로 설정 (본인의 경로로 설정)
CHROME_DRIVER_PATH = "path/to/chromedriver"

# 다운로드 폴더 설정
download_dir = "data/raw"
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

# 크롬 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless")  # 브라우저 창을 표시하지 않음
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,  # 파일 다운로드 경로 설정
    "download.prompt_for_download": False,  # 다운로드 확인창 생략
    "directory_upgrade": True,
    "safebrowsing.enabled": True
})

# 웹드라이버 실행
service = Service(CHROME_DRIVER_PATH)
driver = webdriver.Chrome(service=service, options=chrome_options)

# KB 부동산 데이터 허브의 주간 아파트 매매가격 지수 페이지로 이동
url = "https://data.kbland.kr/kbstats/wmh?tIdx=HT01&tsIdx=weekAptSalePriceInx"
driver.get(url)

# 페이지 로드 대기
time.sleep(5)

# BeautifulSoup으로 페이지 소스 분석
soup = BeautifulSoup(driver.page_source, 'html.parser')

# 우측 상단 3점 아이콘 클릭
three_dot_icon = driver.find_element(By.CSS_SELECTOR, ".btn-dotmore black iconbtn")
three_dot_icon.click()

# 데이터 다운로드 버튼 클릭


download_button = driver.find_element(By.CSS_SELECTOR, ".btn-dotmore black iconbtn")

# 다운로드 대기 (필요에 따라 다운로드 시간이 다를 수 있음)
time.sleep(10)

# 웹드라이버 종료
driver.quit()

print(f"데이터가 {download_dir}에 다운로드 되었습니다.")
