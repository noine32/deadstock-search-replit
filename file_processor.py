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
    def process_data(purchase_df, inventory_df, yj_code_df):
        """
        不良在庫データを処理し、分析結果を含むDataFrameを返す
        
        Parameters:
        -----------
        purchase_df : pandas.DataFrame
            OMEC他院所データ
        inventory_df : pandas.DataFrame
            不良在庫データ
        yj_code_df : pandas.DataFrame
            在庫金額データ（YJコードマスタ）
        
        Returns:
        --------
        pandas.DataFrame
            処理済みの不良在庫データ
        """
        try:
            # データフレームの存在チェック
            if any(df.empty for df in [purchase_df, inventory_df, yj_code_df]):
                raise ValueError("空のデータフレームが含まれています")

            # カラム名の存在チェック
            required_columns = {
                'inventory': ['薬品名', '在庫量', '使用期限', 'ロット番号'],
                'purchase': ['厚労省CD', '法人名', '院所名', '品名・規格', '新薬品ｺｰﾄﾞ'],
                'yj_code': ['薬品名', 'ＹＪコード', '単位']
            }
            
            for df_name, cols in required_columns.items():
                df = {'inventory': inventory_df, 'purchase': purchase_df, 'yj_code': yj_code_df}[df_name]
                missing = [col for col in cols if col not in df.columns]
                if missing:
                    raise ValueError(f"{df_name}データに必要なカラムがありません: {', '.join(missing)}")

            # データの前処理
            inventory_df = inventory_df.copy()
            purchase_df = purchase_df.copy()
            yj_code_df = yj_code_df.copy()

            # 日付データの処理
            inventory_df['使用期限'] = pd.to_datetime(inventory_df['使用期限'], errors='coerce')
            
            # 有効期限切れまでの日数を計算
            inventory_df['有効期限切れまでの日数'] = (inventory_df['使用期限'] - pd.Timestamp.now()).dt.days
            
            # 在庫金額CSVから薬品名とＹＪコードのマッピングを作成
            yj_mapping = dict(zip(yj_code_df['薬品名'], zip(yj_code_df['ＹＪコード'], yj_code_df['単位'])))
            
            # 不良在庫データにＹＪコードと単位を設定
            inventory_df['ＹＪコード'] = inventory_df['薬品名'].map(lambda x: yj_mapping.get(x, (None, None))[0])
            inventory_df['単位'] = inventory_df['薬品名'].map(lambda x: yj_mapping.get(x, (None, None))[1])
            
            # 不良在庫の判定（有効期限が6ヶ月以内）
            inventory_df['不良在庫'] = inventory_df['有効期限切れまでの日数'] <= 180
            
            # データのマージ
            merged_df = pd.merge(
                inventory_df,
                purchase_df[required_columns['purchase']],
                left_on='ＹＪコード',
                right_on='厚労省CD',
                how='left'
            )
            
            # 結果データフレームの作成
            result_columns = [
                '品名・規格',
                '在庫量',
                '単位',
                '新薬品ｺｰﾄﾞ',
                '使用期限',
                'ロット番号',
                '法人名',
                '院所名',
                '有効期限切れまでの日数',
                '不良在庫'
            ]
            
            result_df = merged_df[result_columns].copy()
            
            # 日付フォーマットの設定
            result_df['使用期限'] = result_df['使用期限'].dt.strftime('%Y-%m-%d')
            
            # 数値データの処理
            result_df['在庫量'] = pd.to_numeric(result_df['在庫量'], errors='coerce').fillna(0)
            result_df['有効期限切れまでの日数'] = result_df['有効期限切れまでの日数'].fillna(0).astype(int)
            
            # 欠損値の処理
            result_df = result_df.fillna({
                '品名・規格': '',
                '単位': '',
                '新薬品ｺｰﾄﾞ': '',
                'ロット番号': '',
                '法人名': '',
                '院所名': ''
            })
            
            # データのソート
            result_df = result_df.sort_values(
                ['不良在庫', '有効期限切れまでの日数', '法人名', '院所名'],
                ascending=[False, True, True, True]
            )
            
            return result_df
            
        except Exception as e:
            print(f"データ処理中にエラーが発生しました: {str(e)}")
            raise

    @staticmethod
    def generate_excel(df):
        excel_buffer = io.BytesIO()

        try:
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # 院所名ごとにシートを作成（空の値を除外）
                for name in df['院所名'].unique():
                    if not pd.isna(name) and str(name).strip():
                        sheet_name = str(name)[:31].strip()  # シート名を31文字以内に制限
                        sheet_df = df[df['院所名'] == name].copy()
                        
                        if not sheet_df.empty:
                            try:
                                # 法人名と院所名を取得
                                houjin_name = str(sheet_df['法人名'].iloc[0] or '')
                                insho_name = str(sheet_df['院所名'].iloc[0] or '')
                                
                                # 表示用のカラムから法人名と院所名を除外
                                display_df = sheet_df.drop(['法人名', '院所名'], axis=1)
                                
                                # 「引取り可能数」列を追加
                                display_df.insert(display_df.columns.get_loc('ロット番号') + 1, '引取り可能数', '')
                                
                                # ヘッダーデータの作成
                                header_data = pd.DataFrame([
                                    ['不良在庫引き取り依頼'],
                                    [''],
                                    [f"{houjin_name.strip()} {insho_name.strip()}", '', '御中'],
                                    [''],
                                    ['下記の不良在庫につきまして、引き取りのご検討を賜れますと幸いです。どうぞよろしくお願いいたします。'],
                                    ['']
                                ])
                                
                                # ヘッダーとデータを書き込み
                                header_data.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                                display_df.to_excel(writer, sheet_name=sheet_name, startrow=6, index=False)
                                
                                # シートを取得してフォーマットを設定
                                worksheet = writer.sheets[sheet_name]
                                
                                # 列幅の設定
                                worksheet.column_dimensions['A'].width = 35  # 品名・規格
                                worksheet.column_dimensions['B'].width = 15  # 在庫量
                                worksheet.column_dimensions['C'].width = 10  # 単位
                                worksheet.column_dimensions['D'].width = 15  # 新薬品コード
                                worksheet.column_dimensions['E'].width = 15  # 使用期限
                                worksheet.column_dimensions['F'].width = 15  # ロット番号
                                worksheet.column_dimensions['G'].width = 20  # 引取り可能数
                                
                                # 行の高さを設定（30ピクセル）
                                for row in range(1, worksheet.max_row + 1):
                                    worksheet.row_dimensions[row].height = 30
                                
                                # デフォルトのフォントサイズを14に設定
                                for row in worksheet.rows:
                                    for cell in row:
                                        if cell.font is None:
                                            cell.font = cell.font.copy(size=14)
                                        else:
                                            cell.font = cell.font.copy(size=14)
                                
                                # タイトルのフォント設定（サイズ16）
                                cell_a1 = worksheet['A1']
                                cell_a1.font = cell_a1.font.copy(size=16)
                                
                                # 法人名・院所名と御中のフォント設定（サイズ14、太字）
                                cell_a3 = worksheet['A3']  # 法人名・院所名
                                cell_c3 = worksheet['C3']  # 御中
                                font_style = cell_a3.font.copy(size=14, bold=True)
                                cell_a3.font = font_style
                                cell_c3.font = font_style
                                
                            except Exception as e:
                                print(f"シート '{sheet_name}' の処理中にエラーが発生: {str(e)}")
                                continue
        
        except Exception as e:
            print(f"Excel生成中にエラーが発生: {str(e)}")
            return None

        excel_buffer.seek(0)
        return excel_buffer
