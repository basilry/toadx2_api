#!/bin/bash

# .env 파일 로드
if [ -f .env ]; then
    export $(cat .env | xargs)
fi


# FastAPI 서버 실행
function run() {
    uvicorn src.api.main:app --reload
}

# 프로젝트 종료
function stop() {
    exit 0
}

# 프로젝트 빌드
#function build() {
#    docker build -t my_fastapi_app .
#}

# 테스트 실행
function test() {
    pytest
}

# 의존성 설치
function install() {
    pip install -r requirements.txt
}

# Alembic 리비전 생성 (자동 생성) 및 데이터베이스 업데이트
function update_db_schema() {
    alembic revision --autogenerate -m "Auto-generated migration"
    alembic upgrade head
}

#=============kb 데이터 관련 스크립트================

# kb 데이터 크롤링 및 db 데이터 업데이트, 그리고 NaN 값 채우기
function update_db_data() {
    python3 -m src.preprocessing.kb_data_hub.data_pipeline
}

# 데이터베이스의 kb 데이터를 기반으로 예측
function predict() {
    python3 -m src.ml_models.prophet.prediction_pipeline
}

# db의 csv를 기반으로 qa 데이터셋 생성
function create_qa_dataset() {
    python3 -m src.preprocessing.kor_conversation_based_db.real_estate_qa_pipeline
}

# qa 데이터셋을 한국어 llm을 통해 보다 부드러운 형태로 변환
function create_qa_dataset() {
    python3 -m src.preprocessing.kor_conversation_based_db.real_estate_qa_pipeline
}

# 자연어 파싱 하는 qna 데이터셋 생성
function nlp_parsing_qna_dataset() {
    python3 -m src.preprocessing.kb_data_hub.qna_dataset_maker
}

# 자연어 파싱 qna 데이터셋 검수
function nlp_parsing_qna_dataset_validate() {
    python3 -m src.preprocessing.kb_data_hub.qna_dataset_validator
}

#======================================================

# 국토교통부 데이터 업데이트
function update_db_legal_dong() {
     python3 -m src.preprocessing.ministry_of_land.ministry_legal_dong_pipeline
}

# 네이버 부동산 뉴스 크롤링
function crawl_naver_news() {
    python3 -m src.preprocessing.naver_real_estate_news.crawler
}

# 크롤링한 데이터 전처리
function preprocess_crawled_data() {
    python3 -m src.preprocessing.naver_real_estate_news.data_preprocessing
}

#=======================================================



# 메뉴 출력 및 선택
function main_menu() {
    echo "1) 프로젝트 관리"
    echo "2) KB 데이터 관련"
    echo "3) 크롤링 관련"
    echo "4) 종료"
    read -p "번호를 선택하세요: " choice

    case $choice in
        1)
            project_menu
            ;;
        2)
            kb_data_menu
            ;;
        3)
            crawl_menu
            ;;
        4)
            stop
            ;;
        *)
            echo "잘못된 선택입니다."
            main_menu
            ;;
    esac
}

# 프로젝트 관리 메뉴
function project_menu() {
    echo "1) 서버 실행"
    echo "2) 의존성 설치"
    echo "3) 데이터베이스 스키마 업데이트"
    echo "4) 테스트 실행"
    read -p "번호를 선택하세요: " choice

    case $choice in
        1) run ;;
        2) install ;;
        3) update_db_schema ;;
        4) test ;;
        *) echo "잘못된 선택입니다."; project_menu ;;
    esac
}

# KB 데이터 관련 메뉴
function kb_data_menu() {
    echo "1) KB 데이터 업데이트"
    echo "2) KB 데이터 예측"
    echo "3) QA 데이터셋 생성"
    echo "4) NLP 파싱 QA 데이터셋 생성"
    echo "5) NLP 파싱 QA 데이터셋 검수"
    read -p "번호를 선택하세요: " choice

    case $choice in
        1) update_db_data ;;
        2) predict ;;
        3) create_qa_dataset ;;
        4) nlp_parsing_qna_dataset ;;
        5) nlp_parsing_qna_dataset_validate ;;
        *) echo "잘못된 선택입니다."; kb_data_menu ;;
    esac
}

# 크롤링 관련 메뉴
function crawl_menu() {
    echo "1) 네이버 부동산 뉴스 크롤링"
    echo "2) 국토교통부 데이터 업데이트"
    echo "3) 크롤링한 데이터 전처리"
    read -p "번호를 선택하세요: " choice

    case $choice in
        1) crawl_naver_news ;;
        2) update_db_legal_dong ;;
        3) preprocess_crawled_data ;;
        *) echo "잘못된 선택입니다."; crawl_menu ;;
    esac
}

# 스크립트 시작
main_menu