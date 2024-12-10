import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# YJコードマスターの作成
yj_codes = pd.DataFrame({
    '商品コード': ['P' + str(i).zfill(5) for i in range(1, 11)],
    'YJコード': ['YJ' + str(i).zfill(8) for i in range(1, 11)],
    '商品名': [f'医薬品{i}' for i in range(1, 11)]
})
yj_codes.to_csv('sample_yj_codes.csv', index=False, encoding='utf-8-sig')

# 購入履歴データの作成
purchase_history = pd.DataFrame({
    '商品コード': np.random.choice(yj_codes['商品コード'], size=20),
    '購入日': [datetime.now() - timedelta(days=x) for x in range(20)],
    '購入数量': np.random.randint(1, 10, size=20)
})
purchase_history.to_excel('sample_purchase_history.xlsx', index=False)

# 不良在庫データの作成
inventory = pd.DataFrame({
    'YJコード': np.random.choice(yj_codes['YJコード'], size=15),
    '商品名': [f'医薬品{i}' for i in range(1, 16)],
    '在庫数量': np.random.randint(1, 20, size=15),
    '有効期限': [(datetime.now() + timedelta(days=x*30)).strftime('%Y-%m-%d') for x in range(1, 16)],
    '薬局ID': ['PH' + str(i).zfill(3) for i in range(1, 16)]
})
inventory.to_csv('sample_inventory.csv', index=False, encoding='utf-8-sig')

print("サンプルデータの生成が完了しました。")
