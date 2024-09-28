from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, \
    DataCollatorForLanguageModeling
from datasets import load_dataset

# 데이터셋 로드
dataset = load_dataset("kms7530/gemma-korean")

# 모델과 토크나이저 로드
model = AutoModelForCausalLM.from_pretrained("google/gemma-2-9b-it")
tokenizer = AutoTokenizer.from_pretrained("google/gemma-2-9b-it")


# 데이터 전처리 (토크나이저 적용)
def tokenize_function(examples):
    return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)


tokenized_datasets = dataset.map(tokenize_function, batched=True)

# 학습 데이터로 사용할 데이터셋 설정
train_dataset = tokenized_datasets["train"]

# 학습 설정
training_args = TrainingArguments(
    output_dir="./results",
    overwrite_output_dir=True,
    num_train_epochs=1,
    per_device_train_batch_size=4,
    save_steps=10_000,
    save_total_limit=2,
)

# Data Collator 설정
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# Trainer 설정 및 학습 수행
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    data_collator=data_collator,
)

# 모델 학습
trainer.train()

# 모델 저장
model.save_pretrained("./models/gemma2-finetuned")
tokenizer.save_pretrained("./models/gemma2-finetuned")
