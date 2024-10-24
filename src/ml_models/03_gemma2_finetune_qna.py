import os
import torch
from huggingface_hub import login
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments, Trainer
from peft import prepare_model_for_kbit_training, LoraConfig, get_peft_model
from datasets import load_dataset, DatasetDict

# 1. BitsAndBytesConfig 설정
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

# 2. 모델과 토크나이저 불러오기
model_name = "basilry/gemma2-2-2b-it-fine-tuned-korean-real-estate-model"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto"
)

# 3. 모델을 QLoRA에 맞게 준비
model = prepare_model_for_kbit_training(model)

# 4. LoRA 설정
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# 5. PEFT를 사용하여 모델을 LoRA로 래핑
model = get_peft_model(model, lora_config)

# 6. 데이터셋 로드 (JSON 파일 경로)
dataset = load_dataset('json', data_files="/content/drive/MyDrive/qna_dataset/generated_real_estate_dataset_30000.json")

# 7. 데이터셋을 train, validation, test로 분할
def split_dataset(dataset):
    train_dataset, temp_dataset = dataset['train'].train_test_split(test_size=0.2, seed=42).values()
    validation_dataset, test_dataset = temp_dataset.train_test_split(test_size=0.5, seed=42).values()
    return DatasetDict({
        'train': train_dataset,
        'validation': validation_dataset,
        'test': test_dataset
    })

dataset = split_dataset(dataset)

# 8. 프롬프트 생성 함수 정의
def generate_prompts(example):
    output_texts = []
    for i in range(len(example['document'])):
        user_prompt = "질문: {}\n".format(example['document'][i])
        assistant_prompt = "파싱 결과:\n지역: {}\n매매/전세 여부: {}\n시간 정보: {}\n".format(
            example['labels'][i]['지역'],
            example['labels'][i]['매매/전세 여부'],
            example['labels'][i]['시간 정보']
        )
        # 두 프롬프트를 하나의 문자열로 결합하여 사용
        prompt = user_prompt + assistant_prompt
        output_texts.append(prompt)

    return {"prompt": output_texts}

# 9. 프롬프트 생성
prompts_dataset = dataset.map(generate_prompts, batched=True)

# 10. 토크나이즈 함수 정의
def tokenize_function(examples):
    # 'document'를 프롬프트로 처리
    model_inputs = tokenizer(examples['prompt'], truncation=True, padding='max_length', max_length=512)

    # 'labels'가 리스트가 아닌 경우 처리
    if isinstance(examples['labels'], dict):
        labels = [str(examples['labels'])]
    else:
        labels = [str(label) for label in examples['labels']]

    tokenized_labels = tokenizer(labels, truncation=True, padding='max_length', max_length=512)
    model_inputs["labels"] = tokenized_labels["input_ids"]

    return model_inputs

# 11. 토크나이징된 데이터셋 생성
tokenized_dataset = prompts_dataset.map(tokenize_function, batched=True)

# 12. 학습 인자 설정
training_args = TrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=10,
    per_device_eval_batch_size=10,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    evaluation_strategy="steps",
    logging_steps=100,
    save_steps=1000,
    eval_steps=500,
    save_total_limit=2,
    learning_rate=1e-4,
    fp16=True,
    report_to="none"
)

# 13. Trainer 설정
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"],
    tokenizer=tokenizer
)

# 14. 학습 시작
trainer.train()

# 15. 학습된 모델 저장
model.save_pretrained("/content/drive/MyDrive/gemma2-2b-it-fine-tuned-korean-real-estate-qna")
tokenizer.save_pretrained("/content/drive/MyDrive/gemma2-2b-it-fine-tuned-korean-real-estate-qna")