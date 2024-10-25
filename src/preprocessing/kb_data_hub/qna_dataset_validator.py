import pandas as pd
import random

def verify_dataset(dataset_path, sample_size=10):
    # CSV 파일 로드
    data = pd.read_csv(dataset_path)

    # 데이터 크기 확인
    data_length = len(data)

    if data_length == 0:
        print("데이터가 비어 있습니다.")
        return

    # 랜덤으로 sample_size개의 인덱스를 선택
    random_indices = random.sample(range(data_length), sample_size)

    # 선택된 인덱스의 input과 output 출력
    for idx in random_indices:
        print(f"인덱스: {idx}")
        print(f"Input: {data.iloc[idx]['input']}")
        print(f"Output: {data.iloc[idx]['output']}")
        print("-" * 50)

# 메인 함수
def main():
    dataset_path = "datasets/qna_dataset/nlp_parsing_qna_dataset_ver0.5.csv"  # 데이터셋 파일 경로
    sample_size = 10  # 검수할 샘플 개수
    verify_dataset(dataset_path, sample_size)

if __name__ == "__main__":
    main()