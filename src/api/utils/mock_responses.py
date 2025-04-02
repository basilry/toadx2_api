import os
import re
from datetime import datetime
from openai.types.chat import ChatCompletionMessage

# 패턴 매칭을 통한 메시지 유형 확인 (API 호출 실패 시 대체 함수)
def check_using_patterns(text):
    greeting_patterns = ["안녕", "반가", "hi", "hello", "hey", "하이", "ㅎㅇ", "방가"]
    service_inquiry_patterns = ["뭐하는", "어떤 일", "서비스", "무엇을", "기능", "할 수 있"]
    other_topics = ["주식", "날씨", "게임", "음식", "영화", "취미", "스포츠"]
    daily_conversation = ["고마", "감사", "thank", "땡큐", "반가", "잘 지냈"]
    
    # 인사말이나 일상 대화인 경우 N 반환
    if any(pattern in text for pattern in greeting_patterns) or \
       any(pattern in text for pattern in service_inquiry_patterns) or \
       any(topic in text for topic in other_topics) or \
       any(expr in text for expr in daily_conversation):
        return "N"
    
    # 기본적으로 Y 반환 (부동산 관련 질문으로 판단)
    return "Y"

# 대화형 응답 생성 (API 호출 실패 시 대체 함수)
def get_conversation_response(text):
    # 인사말 패턴 체크
    if any(pattern in text for pattern in ["안녕", "반가", "hi", "hello", "ㅎㅇ", "하이"]):
        return "안녕하세요! 저는 두껍이입니다. 한국의 아파트 매매가와 전세가에 대한 정보를 알려드릴 수 있어요~두껍!"
    # 서비스 문의 체크
    elif any(pattern in text for pattern in ["뭐하는", "어떤 일", "서비스", "무엇을", "기능"]):
        return "저는 한국의 아파트 매매가와 전세가 정보를 알려드리는 두껍이입니다. 지역명과 함께 물어보시면 최신 부동산 가격 정보를 알려드릴게요~두껍!"
    # 다른 주제 문의 체크
    elif any(topic in text for topic in ["주식", "날씨", "게임", "음식", "영화"]):
        return "죄송해요, 저는 부동산 정보만 알려드릴 수 있어요. 아파트 매매가나 전세가에 대해 물어봐주세요~두껍!"
    # 감사 표현에 대한 응답
    elif any(thanks in text for thanks in ["고마", "감사", "thank", "땡큐"]):
        return "도움이 되어 기쁩니다! 또 궁금한 것이 있으시면 언제든지 물어보세요~두껍!"
    # 부동산에 대한 일반적인 질문
    elif any(estate_term in text for estate_term in ["부동산", "집값", "아파트", "전세", "매매"]):
        return "부동산에 관심이 있으시군요! 특정 지역의 아파트 매매가나 전세가에 대해 물어보시면 자세히 알려드릴게요~두껍!"
    # 봇의 능력에 관한 질문
    elif any(ability in text for ability in ["할 수 있", "알려줄 수 있", "뭘 알고", "뭘 알려"]):
        return "저는 한국의 아파트 매매가와 전세가 정보를 알려드릴 수 있어요. KB 부동산 데이터 허브의 데이터를 기반으로 정보를 제공하고 있습니다~두껍!"
    # 기타 일상 대화
    else:
        return "안녕하세요! 한국의 아파트 매매가나 전세가에 대해 궁금한 점이 있으신가요? 지역명을 말씀해주시면 도와드릴게요~두껍!"

# 모의 응답 생성 함수 (테스트용)
def get_mock_response(messages, model="gpt-3.5-turbo"):
    system_msg = next((m for m in messages if m.get("role") == "system"), None)
    user_msg = next((m for m in messages if m.get("role") == "user"), None)
    
    # 부동산 관련 질문 여부 확인
    if system_msg and "부동산 관련 질문이면 Y" in system_msg.get("content", ""):
        content = check_using_patterns(user_msg.get("content", "").lower())
                
    elif system_msg and "정형적 가격" in system_msg.get("content", ""):
        content = "PRICE"
    elif system_msg and "파싱" in system_msg.get("content", ""):
        content = "지역: 서울, \n매매/전세 여부: 매매, \n시간 정보: 현재"
    # 인사나 잡담 응답 처리
    elif system_msg and "부동산 중에서도" in system_msg.get("content", "") and user_msg:
        content = get_conversation_response(user_msg.get("content", "").lower())
            
    # 최종 응답일 경우 (가격 데이터가 포함된 경우)
    elif user_msg and "가격 데이터" in user_msg.get("content", ""):
        # 사용자 메시지에서 지역과 가격 데이터 추출
        user_content = user_msg.get("content", "")
        region_match = re.search(r"지역:\s*([^가-힣\s]+)", user_content)
        region = region_match.group(1) if region_match else "서울"
        
        # 가격 데이터 정보가 포함된 응답 생성
        content = f"지역 {region}에 대한 분석 결과입니다~두껍!\n"
        content += "데이터에 따르면, 해당 지역의 최근 부동산 가격 추이는 다음과 같습니다:\n"
        
        # 가격 데이터가 있는 경우 해당 데이터 포함
        price_data_match = re.search(r"가격 데이터:\s*\n(.*?)(?:\n\n|$)", user_content, re.DOTALL)
        if price_data_match:
            formatted_price_data = price_data_match.group(1)
            content += f"{formatted_price_data}\n\n"
        
        # 분석 요약 정보 추가
        content += "이 데이터를 기반으로 한 유의미한 통찰:\n"
        content += "최근 평균 가격은 약 12억 7천만원이며, 가격 추이는 하락세를 보이고 있습니다~두껍!"
    else:
        content = "안녕하세요! 저는 두껍이입니다. 부동산 정보에 대해 물어보세요~두껍!"
    
    # ChatCompletion 객체 모의 생성
    mock_message = ChatCompletionMessage(role="assistant", content=content)
    
    class MockChoice:
        def __init__(self, message):
            self.message = message
            self.index = 0
            self.finish_reason = "stop"
        
    mock_choice = MockChoice(message=mock_message)
    
    class MockResponse:
        def __init__(self, choices):
            self.choices = choices
            self.id = "mock-response-id"
            self.model = model
            self.created = int(datetime.now().timestamp())
    
    return MockResponse(choices=[mock_choice]) 