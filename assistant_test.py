import os
import requests
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 기본 URL (로컬 서버)
BASE_URL = "http://localhost:8000"

def test_assistant_info():
    """
    Assistant 정보 가져오기 테스트
    """
    response = requests.get(f"{BASE_URL}/assistant/info")
    
    if response.status_code == 200:
        print("=== Assistant 정보 ===")
        info = response.json()
        print(f"이름: {info['name']}")
        print(f"ID: {info['id']}")
        print(f"모델: {info['model']}")
        print(f"사용 가능한 도구: {', '.join(info['tools']) if info['tools'] else '없음'}")
        return True
    else:
        print(f"오류: {response.status_code} - {response.text}")
        return False

def test_assistant_chat(message, thread_id=None):
    """
    Assistant 채팅 테스트
    """
    data = {
        "message": message,
    }
    
    if thread_id:
        data["thread_id"] = thread_id
    
    response = requests.post(f"{BASE_URL}/assistant/chat", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("\n=== Assistant 응답 ===")
        print(f"유저: {message}")
        print(f"Assistant: {result['response']}")
        print(f"스레드 ID: {result['thread_id']}")
        return result['thread_id']
    else:
        print(f"오류: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    # Assistant 정보 확인
    if not test_assistant_info():
        print("Assistant 정보를 가져오는데 실패했습니다. .env 파일의 OPENAI_ASSISTANT_ID를 확인하세요.")
        exit(1)
    
    # 대화 시작
    print("\n대화를 시작합니다. 종료하려면 'exit' 또는 'quit'를 입력하세요.")
    
    thread_id = None
    while True:
        user_input = input("\n질문을 입력하세요: ")
        
        if user_input.lower() in ["exit", "quit", "종료"]:
            print("대화를 종료합니다.")
            break
        
        thread_id = test_assistant_chat(user_input, thread_id)
        if not thread_id:
            print("대화에 실패했습니다.")
            break 