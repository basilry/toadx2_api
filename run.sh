#!/bin/bash

# FastAPI 서버 실행
function run() {
    uvicorn src.api.main:app --reload
}

# 프로젝트 빌드
function build() {
    docker build -t my_fastapi_app .
}

# 테스트 실행
function test() {
    pytest
}

# 의존성 설치
function install() {
    pip install -r requirements.txt
}

# 스크립트의 첫 번째 인자를 명령으로 처리
case "$1" in
    run) run ;;
    build) build ;;
    test) test ;;
    install) install ;;
    *) echo "Usage: $0 {run|build|test|install}" ;;
esac
