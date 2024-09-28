import pandas as pd
from sqlalchemy.orm import Session


def clean_date_column(df: pd.DataFrame, column_name: str):
    """
    날짜 컬럼의 값을 datetime 형식으로 변환하고, 시간 제거.
    """
    df[column_name] = pd.to_datetime(df[column_name], errors='coerce').dt.date
    return df


def clean_region_name(df: pd.DataFrame):
    """
    지역명에서 불필요한 공백 제거.
    """
    df['지역명'] = df['지역명'].str.strip()
    return df


def remove_time(df: pd.DataFrame, date_col: str):
    """
    날짜 컬럼에서 시간 부분 제거.
    """
    df[date_col] = df[date_col].dt.normalize()
    return df
