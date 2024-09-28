from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline


# GEMMA2 모델을 로드하는 함수
def load_gemma2_model():
    tokenizer = AutoTokenizer.from_pretrained("google/gemma-2-9b-it")
    model = AutoModelForCausalLM.from_pretrained("google/gemma-2-9b-it")
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
    return pipe


# GEMMA2 모델을 사용해 텍스트 예측을 수행하는 함수
def generate_response(messages):
    pipe = load_gemma2_model()
    response = pipe(messages)
    return response
