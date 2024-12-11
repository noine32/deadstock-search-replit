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
                
                # デバッグ用：元のデータ行数を記録
                print(f"読み込み直後の行数: {len(df)}")
                
                # 薬品名が空白の行を削除（より厳密なチェック）
                # NaN, None, 空文字、空白文字をすべて除外
                df['薬品名'] = df['薬品名'].astype(str).apply(lambda x: x.strip())
                df = df[df['薬品名'].apply(lambda x: x not in ['', 'nan', 'None'])]
                
                # デバッグ用：薬品名フィルタリング後の行数を記録
                print(f"薬品名フィルタリング後の行数: {len(df)}")
                
                # 在庫量を数値に変換し、0以下の行を削除
                df['在庫量'] = pd.to_numeric(df['在庫量'], errors='coerce')
                df = df[df['在庫量'] > 0]
                
                # デバッグ用：在庫量フィルタリング後の行数を記録
                print(f"在庫量フィルタリング後の行数: {len(df)}")
                
                # 在庫量を整数に変換
                df['在庫量'] = df['在庫量'].astype(int)
            else:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
            
            return df
        except Exception as e:
            raise Exception(f"CSVファイルの読み込みエラー: {str(e)}")

    @staticmethod
    def process_data(purchase_history_df, inventory_df, yj_code_df):
        # 空の薬品名を持つ行を削除
        inventory_df = inventory_df[inventory_df['薬品名'].notna() & (inventory_df['薬品名'] != '')]
        
        # 数値データを文字列に変換し、NaN値を処理
        for df in [inventory_df, purchase_history_df, yj_code_df]:
            for col in df.columns:
                df[col] = df[col].fillna('').astype(str)
        
        # 在庫金額CSVから薬品名とＹＪコードのマッピングを作成
        yj_mapping = dict(zip(yj_code_df['薬品名'], zip(yj_code_df['ＹＪコード'], yj_code_df['単位'])))
        
        # 不良在庫データに対してＹＪコードと単位を設定
        inventory_df['ＹＪコード'] = inventory_df['薬品名'].map(lambda x: yj_mapping.get(x, (None, None))[0])
        inventory_df['単位'] = inventory_df['薬品名'].map(lambda x: yj_mapping.get(x, (None, None))[1])
        
        # ＹＪコードと厚労省CDで紐付け
        merged_df = pd.merge(
            inventory_df,
            purchase_history_df[['厚労省CD', '法人名', '院所名', '品名・規格', '新薬品ｺｰﾄﾞ']],
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
            '法人名',
            '院所名'
        ]].copy()
        
        # 空の値を空文字列に変換
        result_df = result_df.fillna('')
        
        # 院所名でソート
        result_df = result_df.sort_values(['法人名', '院所名'])
        
        return result_df

    @staticmethod
    def generate_excel(df):
        excel_buffer = io.BytesIO()
        
        # シート名として無効な文字を置換する関数
        def clean_sheet_name(name):
            if not isinstance(name, str) or not name.strip():
                return 'Unknown'
            # 特殊文字を置換
            invalid_chars = ['/', '\\', '?', '*', ':', '[', ']']
            cleaned_name = ''.join('_' if c in invalid_chars else c for c in name)
            # 最大31文字に制限（Excelの制限）
            return cleaned_name[:31].strip()

        # ExcelWriterを使用して、院所名ごとにシートを作成
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            # 院所名ごとにシートを作成（空の値を除外）
            for name in df['院所名'].unique():
                if pd.notna(name) and str(name).strip():  # 空の値をスキップ
                    sheet_name = clean_sheet_name(str(name))
                    # 該当する院所のデータを抽出
                    sheet_df = df[df['院所名'] == name].copy()
                    if not sheet_df.empty:
                        # 法人名と院所名を取得（ヘッダー用）
                        houjin_name = sheet_df['法人名'].iloc[0]
                        insho_name = sheet_df['院所名'].iloc[0]
                        
                        # 表示用のカラムから法人名と院所名を除外
                        display_df = sheet_df.drop(['法人名', '院所名'], axis=1)
                        
                        # 「引取り可能数」列を追加
                        display_df.insert(display_df.columns.get_loc('ロット番号') + 1, '引取り可能数', '')
                        
                        # ヘッダー情報を作成
                        header_data = [
                            ['不良在庫引き取り依頼'],
                            [''],
                            ['{} {} 御中'.format(str(houjin_name).strip(), str(insho_name).strip())],
                            [''],
                            ['下記の不良在庫につきまして、引き取りのご検討を賜れますと幸いです。どうぞよろしくお願いいたします。'],
                            ['']
                        ]
                        
                        # ヘッダー情報をDataFrameに変換
                        header_df = pd.DataFrame(header_data)
                        
                        # ヘッダーとデータを書き込み
                        header_df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        display_df.to_excel(writer, sheet_name=sheet_name, startrow=6, index=False)
                        
                        # シートを取得してフォーマットを設定
                        worksheet = writer.sheets[sheet_name]
                        
                        # 列幅の設定
                        worksheet.column_dimensions['A'].width = 35  # 255ピクセルは約35文字幅
                        for col in ['B', 'C', 'D', 'E', 'F', 'G']:  # 追加した引取り可能数列も含む
                            worksheet.column_dimensions[col].auto_fit = True
                        
                        # 行の高さを設定（30ピクセル）
                        for row in range(1, worksheet.max_row + 1):
                            worksheet.row_dimensions[row].height = 30
                        
                        # フォントサイズと太字の設定
                        cell_a1 = worksheet['A1']
                        cell_a1.font = cell_a1.font.copy(size=16)
                        
                        cell_a3 = worksheet['A3']
                        cell_a3.font = cell_a3.font.copy(size=14, bold=True)
        
        excel_buffer.seek(0)
        return excel_buffer

    
