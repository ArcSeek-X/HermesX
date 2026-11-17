"""分析日线字段清洗；不包含选源、缓存或交易指标策略。"""

import pandas as pd


def clean_daily_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    数据清洗

    处理：
    1. 确保日期列格式正确
    2. 数值类型转换
    3. 去除空值行
    4. 按日期排序
    """
    df = df.copy()

    # 确保日期列为 datetime 类型
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])

    # 数值列类型转换
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 去除关键列为空的行
    df = df.dropna(subset=['close', 'volume'])

    # 按日期升序排序
    df = df.sort_values('date', ascending=True).reset_index(drop=True)

    return df

