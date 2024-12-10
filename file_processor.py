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
    def read_csv(file, file_type='default'):
        try:
            file_bytes = file.getvalue()
            encoding = FileProcessor.detect_encoding(file_bytes)
            
            if file_type == 'inventory':
                # 不良在庫データの場合、最初の7行をスキップ
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding, skiprows=7)
            else:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
            
            return df
        except Exception as e:
            raise Exception(f"CSVファイルの読み込みエラー: {str(e)}")

    @staticmethod
    def process_data(purchase_history_df, inventory_df, yj_code_df):
        # 在庫金額CSVから薬品名とＹＪコードのマッピングを作成
        yj_mapping = dict(zip(yj_code_df['薬品名'], zip(yj_code_df['ＹＪコード'], yj_code_df['単位'])))
        
        # 不良在庫データに対してＹＪコードと単位を設定
        inventory_df['ＹＪコード'] = inventory_df['薬品名'].map(lambda x: yj_mapping.get(x, (None, None))[0])
        inventory_df['単位'] = inventory_df['薬品名'].map(lambda x: yj_mapping.get(x, (None, None))[1])
        
        # OMEC他院所データ（購入履歴）との結合
        # ＹＪコードと厚労省CDで紐付け
        merged_df = pd.merge(
            inventory_df,
            purchase_history_df[['厚労省CD', '院所名', '品名・規格', '新薬品ｺｰﾄﾞ']],
            left_on='ＹＪコード',
            right_on='厚労省CD',
            how='left'
        )
        
        # 院所名別にデータを整理
        # 必要なカラムのみを選択
        result_df = merged_df[[
            '品名・規格',
            '在庫量',
            '単位',
            '新薬品ｺｰﾄﾞ',
            '使用期限',
            'ロット番号',
            '院所名'
        ]].copy()
        
        # 院所名でソート
        result_df = result_df.sort_values('院所名')
        
        return result_df

    @staticmethod
    def generate_csv(df):
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        # BOMを追加
        return '\ufeff' + csv_buffer.getvalue()

    @staticmethod
    def generate_pdf(df):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        import io

        # 日本語フォントの設定
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))

        # PDFバッファの作成
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        # テーブルデータの準備
        data = [df.columns.tolist()] + df.values.tolist()
        table = Table(data)
        
        # テーブルスタイルの設定
        style = TableStyle([
            ('FONT', (0, 0), (-1, -1), 'HeiseiKakuGo-W5'),
            ('FONT', (0, 0), (-1, 0), 'HeiseiKakuGo-W5'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ])
        table.setStyle(style)

        # PDFの生成
        elements = []
        elements.append(table)
        doc.build(elements)

        buffer.seek(0)
        return buffer
