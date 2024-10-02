import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import Dataset
import torch
import os
from dotenv import load_dotenv

load_dotenv()
huggingfaceToken = os.getenv('HUGGINGFACE_TOKEN')

#/Users/basilry/Projects/0092_toadx2_api/toadx2_api/src/ml_models
base_path = os.path.dirname(os.path.abspath(__file__))
print(base_path)



# 1. Load Korean gemma2 model and Tokenizer Load
model_name = os.path.join(base_path, "gemma2-2-2b-it-fine-tuned-korean-model")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# 2. CSV File Load
prediction_data = pd.read_csv('../../datasets/kb_real_estate_data/kb_prediction_data.csv')
property_price_data = pd.read_csv('../../datasets/kb_real_estate_data/kb_property_price_data.csv')

# 3. Convert Data to Text
def convert_prediction_row_to_text(row):
    return (f"날짜: {row['date']}, 지역 코드: {row['region_code']}, "
            f"구분: {row['price_type']}, 예측 지수: {row['predicted_index']}, "
            f"예측 가격: {row['predicted_price']}")

def convert_property_row_to_text(row):
    return (f"날짜: {row['date']}, 지역 코드: {row['region_code']}, "
            f"구분: {row['price_type']}, 기록 지수: {row['index_value']}, "
            f"평균 가격: {row['avg_price']}, 보간 여부: {row['is_interpolated']}")

# 4. Convert Prediciton & Historical Datas to Text
prediction_data['text'] = prediction_data.apply(convert_prediction_row_to_text, axis=1)
property_price_data['text'] = property_price_data.apply(convert_property_row_to_text, axis=1)

# 5. Combine Datas
combined_data = pd.concat([prediction_data[['text']], property_price_data[['text']]])

# 6. Convert Hugging Face Datasets
dataset = Dataset.from_pandas(combined_data)

# 7. Define Preprocess Function
def tokenize_function(examples):
    model_inputs = tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)

    # labels를 input_ids의 복사본으로 설정하고, 패딩된 토큰을 -100으로 설정하여 무시하도록 만듦
    labels = model_inputs["input_ids"].copy()
    labels = [[-100 if token == tokenizer.pad_token_id else token for token in label] for label in labels]

    model_inputs["labels"] = labels
    return model_inputs

# 8. Tokenized Datasets
tokenized_datasets = dataset.map(tokenize_function, batched=True)

# 9. Divide Train & Test datasets
train_test_split = tokenized_datasets.train_test_split(test_size=0.1)
train_dataset = train_test_split['train']
eval_dataset = train_test_split['test']

from transformers import DataCollatorForSeq2Seq, Seq2SeqTrainer, Seq2SeqTrainingArguments

# 10. Difine Data Collator
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=model,
    padding=True,
)

# 11. Define Training Arguments
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

# 12. Trainer Initiailize
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# 12. Start Training
trainer.train()

# 13. Save Model
model.save_pretrained("./fine-tuned-real-estate-model")
tokenizer.save_pretrained("./fine-tuned-real-estate-model")