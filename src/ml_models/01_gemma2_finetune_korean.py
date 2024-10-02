import os
from huggingface_hub import login
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling, DataCollatorForSeq2Seq, Seq2SeqTrainingArguments, Seq2SeqTrainer
# google colab environment
os.environ['HUGGINGFACE_TOKEN'] = "your_token"
login(os.environ['HUGGINGFACE_TOKEN'])

model_name = "google/gemma-2-2b-it"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Check Tokenizer
print(tokenizer.tokenize("안녕하세요, 오늘 날씨는 어떻습니까?"))

# 1. Dataset Load
dataset = load_dataset("jojo0217/korean_safe_conversation")

# 2. Dataset Divide
dataset = dataset["train"].train_test_split(test_size=0.1)

# 3. Check Dataset's Column
print(dataset["train"].column_names)  # ['input', 'output']

# 4. Define Data PreProcess Function
def preprocess_function(examples):
    inputs = [f"사용자: {q}" for q in examples["input"]]
    targets = [f"AI: {a}" for a in examples["output"]]

    model_inputs = tokenizer(
        inputs,
        max_length=128,
        truncation=True,
        padding='max_length',
    )

    labels = tokenizer(
        targets,
        max_length=128,
        truncation=True,
        padding='max_length',
    ).input_ids

    model_inputs["labels"] = labels
    return model_inputs

# 5. Apply Preprocess Dataset
tokenized_datasets = dataset.map(
    preprocess_function,
    batched=True,
    remove_columns=dataset["train"].column_names,
)

# 6. Define Data Collator
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=model,
    padding=True,
)

# 7. Define Training Arguments
training_args = Seq2SeqTrainingArguments(
    output_dir="./results",
    overwrite_output_dir=True,
    num_train_epochs=1,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    save_steps=5000,
    save_total_limit=2,
    logging_steps=500,
    eval_strategy="steps",
    eval_steps=5000,
    predict_with_generate=True,
    fp16=True,
)

# 8. Trainer Initialize
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["test"],
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# 9. Start Training
trainer.train()

# 10. Save Model
trainer.save_model("./gemma2-2-2b-it-fine-tuned-korean-model")
tokenizer.save_pretrained("./gemma2-2-2b-it-fine-tuned-korean-model")