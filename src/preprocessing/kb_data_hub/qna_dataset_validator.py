import json
import random

def verify_dataset(dataset_path, sample_size=10):
    # JSON 파일 로드
    with open(dataset_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 데이터 내의 'data' 리스트 추출
    data_items = data['data']

    # 데이터 크기 확인
    data_length = len(data_items)

    if data_length == 0:
        print("데이터가 비어 있습니다.")
        return

    # 랜덤으로 sample_size개의 인덱스를 선택
    random_indices = random.sample(range(data_length), sample_size)

    # 선택된 인덱스의 inputs와 outputs 출력
    for idx in random_indices:
        print(f"인덱스: {idx}")
        print(f"Input: {data_items[idx]['inputs']}")
        print(f"Output: {data_items[idx]['outputs']}")
        print("-" * 50)

# 메인 함수
def main():
    dataset_path = "datasets/qna_dataset/nlp_parsing_qna_dataset_ver0.2.json"  # 데이터셋 파일 경로
    sample_size = 10  # 검수할 샘플 개수
    verify_dataset(dataset_path, sample_size)

if __name__ == "__main__":
    main()

# import json
# import random
#
#
# def verify_dataset(dataset_path, sample_size=10):
#     # JSON 파일 로드
#     with open(dataset_path, 'r', encoding='utf-8') as file:
#         data = json.load(file)
#
#     # document와 labels 리스트 추출
#     documents = data['documents']
#     labels = data['labels']
#
#     # 데이터 크기 확인
#     data_length = len(documents)
#
#     if data_length == 0:
#         print("데이터가 비어 있습니다.")
#         return
#
#     # 랜덤으로 sample_size개의 인덱스를 선택
#     random_indices = random.sample(range(data_length), sample_size)
#
#     # 선택된 인덱스의 document와 labels 출력
#     for idx in random_indices:
#         print(f"인덱스: {idx}")
#         print(f"Document: {documents[idx]}")
#         print(f"Labels: {labels[idx]}")
#         print("-" * 50)
# # 정합성 검토할 수 있게 출력
#
# # 메인 함수
# def main():
#     dataset_path = "datasets/qna_dataset/nlp_parsing_qna_dataset_ver0.2.json"  # 데이터셋 파일 경로
#     sample_size = 10  # 검수할 샘플 개수
#     verify_dataset(dataset_path, sample_size)
#
#
# if __name__ == "__main__":
#     main()