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
    python -m src.preprocessing.kb_data_hub.data_pipeline
}

# 데이터베이스의 kb 데이터를 기반으로 예측
function predict() {
    python -m src.ml_models.prophet.prediction_pipeline
}

# db의 csv를 기반으로 qa 데이터셋 생성
function create_qa_dataset() {
    python -m src.preprocessing.kor_conversation_based_db.real_estate_qa_pipeline
}

# qa 데이터셋을 한국어 llm을 통해 보다 부드러운 형태로 변환
function create_qa_dataset() {
    python -m src.preprocessing.kor_conversation_based_db.real_estate_qa_pipeline
}

#======================================================

# 국토교통부 데이터 업데이트
function update_db_legal_dong() {
     python -m src.preprocessing.ministry_of_land.ministry_legal_dong_pipeline
}

# 스크립트의 첫 번째 인자를 명령으로 처리
case "$1" in
    run) run ;;
    build) build ;;
    test) test ;;
    install) install ;;
    updatedb) updatedb ;;
    *) echo "Usage: $0 {run|build|test|install|updatedb}" ;;
esac
