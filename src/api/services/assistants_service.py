import os
from openai import OpenAI

# Assistant ID를 사용해 특정 Assistant와 대화하는 클래스
class AssistantService:
    def __init__(self, client=None, assistant_id=None):
        """
        OpenAI Assistant 서비스 초기화
        
        Args:
            client: OpenAI 클라이언트 객체
            assistant_id: 사용할 OpenAI Assistant의 ID
        """
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_id = assistant_id or os.getenv("OPENAI_ASSISTANT_ID")
        
        if not self.assistant_id:
            raise ValueError("Assistant ID가 설정되지 않았습니다. OPENAI_ASSISTANT_ID 환경 변수를 설정하세요.")
    
    def get_assistant_info(self):
        """
        설정된 Assistant의 정보를 가져옵니다.
        
        Returns:
            assistant 정보 객체
        """
        try:
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            return {
                "id": assistant.id,
                "name": assistant.name,
                "instructions": assistant.instructions,
                "model": assistant.model,
                "tools": [tool.type for tool in assistant.tools] if assistant.tools else []
            }
        except Exception as e:
            print(f"Assistant 정보 조회 중 오류 발생: {e}")
            return None
    
    def create_thread(self):
        """
        새로운 대화 스레드를 생성합니다.
        
        Returns:
            생성된 스레드의 ID
        """
        try:
            thread = self.client.beta.threads.create()
            return thread.id
        except Exception as e:
            print(f"스레드 생성 중 오류 발생: {e}")
            return None
    
    def add_message_to_thread(self, thread_id, message_content, role="user"):
        """
        스레드에 메시지를 추가합니다.
        
        Args:
            thread_id: 메시지를 추가할 스레드 ID
            message_content: 메시지 내용
            role: 메시지 작성자 역할 (기본값: "user")
            
        Returns:
            추가된 메시지 객체
        """
        try:
            message = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role=role,
                content=message_content
            )
            return message
        except Exception as e:
            print(f"메시지 추가 중 오류 발생: {e}")
            return None
    
    def run_assistant(self, thread_id, instructions=None):
        """
        Assistant에게 스레드의 메시지를 분석하고 응답하도록 요청합니다.
        
        Args:
            thread_id: 응답을 요청할 스레드 ID
            instructions: Assistant에게 추가적인 지시사항 (선택 사항)
            
        Returns:
            실행 ID
        """
        try:
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                instructions=instructions
            )
            return run.id
        except Exception as e:
            print(f"Assistant 실행 중 오류 발생: {e}")
            return None
    
    def get_run_status(self, thread_id, run_id):
        """
        실행 상태를 확인합니다.
        
        Args:
            thread_id: 스레드 ID
            run_id: 실행 ID
            
        Returns:
            실행 상태 객체
        """
        try:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            return run
        except Exception as e:
            print(f"실행 상태 확인 중 오류 발생: {e}")
            return None
    
    def get_messages(self, thread_id, limit=10):
        """
        스레드의 메시지를 가져옵니다.
        
        Args:
            thread_id: 메시지를 조회할 스레드 ID
            limit: 가져올 메시지 수 (기본값: 10)
            
        Returns:
            메시지 목록
        """
        try:
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=limit
            )
            return messages.data
        except Exception as e:
            print(f"메시지 조회 중 오류 발생: {e}")
            return []
    
    def wait_for_completion(self, thread_id, run_id, timeout=60, initial_delay=1, max_delay=5):
        """
        Assistant의 응답이 완료될 때까지 대기합니다. 폴링 간격을 점진적으로 늘려 API 호출 횟수를 줄입니다.
        
        Args:
            thread_id: 스레드 ID
            run_id: 실행 ID
            timeout: 최대 대기 시간(초) (기본값: 60초)
            initial_delay: 초기 대기 시간(초) (기본값: 1초)
            max_delay: 최대 대기 시간(초) (기본값: 5초)
            
        Returns:
            완료 여부(Boolean)와 최종 상태
        """
        import time
        
        start_time = time.time()
        delay = initial_delay
        
        # 첫 번째 상태 확인 전에 잠시 대기 (대부분의 간단한 응답은 1-2초 내에 완료됨)
        time.sleep(initial_delay)
        
        while time.time() - start_time < timeout:
            run = self.get_run_status(thread_id, run_id)
            if not run:
                return False, "오류 발생"
                
            # 완료된 경우 즉시 반환
            if run.status in ["completed", "failed", "expired", "cancelled"]:
                return run.status == "completed", run.status
            
            # 진행 상태에 따라 다음 폴링 간격 조정
            if run.status == "queued":
                # 대기열에 있는 경우 더 길게 대기
                delay = min(delay * 1.5, max_delay)
            elif run.status == "in_progress":
                # 진행 중인 경우 약간 더 길게 대기
                delay = min(delay * 1.2, max_delay)
            
            # 다음 확인 전 대기
            time.sleep(delay)
        
        # 타임아웃 도달
        return False, "timeout"
    
    def get_response(self, query, thread_id=None, max_messages_per_thread=20):
        """
        사용자 질문에 대한 Assistant의 응답을 생성합니다.
        
        Args:
            query: 사용자 질문
            thread_id: 기존 스레드 ID (없으면 새로 생성)
            max_messages_per_thread: 스레드당 최대 메시지 수 (초과 시 새 스레드 생성)
            
        Returns:
            응답 텍스트와 스레드 ID
        """
        # 스레드 관리 - 기존 스레드가 없거나 메시지가 너무 많으면 새로 생성
        if thread_id:
            try:
                # 기존 스레드의 메시지 수 확인
                messages = self.get_messages(thread_id, limit=1)
                if not messages:
                    # 스레드가 존재하지 않거나 접근 불가능한 경우 새로 생성
                    print(f"스레드 {thread_id}에 접근할 수 없습니다. 새 스레드를 생성합니다.")
                    thread_id = self.create_thread()
            except Exception as e:
                print(f"스레드 확인 중 오류 발생: {e}, 새 스레드를 생성합니다.")
                thread_id = self.create_thread()
        else:
            # 스레드가 없으면 새로 생성
            thread_id = self.create_thread()
        
        if not thread_id:
            return "스레드 생성에 실패했습니다.", None
        
        try:
            # 메시지 추가
            self.add_message_to_thread(thread_id, query)
            
            # Assistant 실행
            run_id = self.run_assistant(thread_id)
            if not run_id:
                return "Assistant 실행에 실패했습니다.", thread_id
            
            # 완료될 때까지 대기 (최적화된 폴링 방식)
            completed, status = self.wait_for_completion(thread_id, run_id, initial_delay=1.5, max_delay=6)
            if not completed:
                return f"응답 생성 실패: {status}", thread_id
            
            # 응답 가져오기 - 최신 메시지 1개만 조회하여 API 호출 최소화
            messages = self.get_messages(thread_id, limit=1)
            if not messages:
                return "응답 메시지를 가져오는데 실패했습니다.", thread_id
            
            # 가장 최근 메시지가 assistant 응답인지 확인
            latest_message = messages[0]
            if latest_message.role != "assistant":
                return "예상치 못한 응답 형식입니다.", thread_id
            
            # 응답 텍스트 추출 및 캐싱
            response_text = ""
            for content_item in latest_message.content:
                if content_item.type == "text":
                    response_text += content_item.text.value
            
            return response_text, thread_id
            
        except Exception as e:
            print(f"응답 생성 중 오류 발생: {e}")
            return f"오류가 발생했습니다: {str(e)}", thread_id 