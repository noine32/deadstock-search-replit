import pandas as pd
import chardet
import io
from datetime import datetime

class FileProcessor:
    @staticmethod
    def detect_encoding(file_bytes):
        result = chardet.detect(file_bytes)
        return result['encoding']

    @staticmethod
    def read_excel(file):
        try:
            df = pd.read_excel(file, engine='openpyxl')
            return df
        except Exception as e:
            raise Exception(f"Excelファイルの読み込みエラー: {str(e)}")

    @staticmethod
    def read_csv(file):
        try:
            file_bytes = file.getvalue()
            encoding = FileProcessor.detect_encoding(file_bytes)
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
            return df
        except Exception as e:
            raise Exception(f"CSVファイルの読み込みエラー: {str(e)}")

    @staticmethod
    def process_data(purchase_history_df, inventory_df, yj_code_df):
        # YJコードマスターデータの準備
        yj_master = yj_code_df.set_index('商品コード')['YJコード'].to_dict()
        
        # 購入履歴データの処理
        purchase_history_df['YJコード'] = purchase_history_df['商品コード'].map(yj_master)
        
        # 不良在庫データとの結合
        merged_df = pd.merge(
            inventory_df,
            purchase_history_df,
            on='YJコード',
            how='left'
        )
        
        # 必要なカラムの選択と名前の変更
        result_df = merged_df[[
            'YJコード',
            '商品名',
            '在庫数量',
            '有効期限',
            '薬局ID'
        ]].copy()
        
        return result_df

    @staticmethod
    def generate_csv(df):
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        # BOMを追加
        return '\ufeff' + csv_buffer.getvalue()
