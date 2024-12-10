import pandas as pd
import io
import traceback
from datetime import datetime
import openpyxl
from openpyxl.styles import Font
import chardet
import logging
import sys

# ロギングの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class FileProcessor:
    @staticmethod
    def detect_encoding(file_bytes):
        try:
            result = chardet.detect(file_bytes)
            logger.debug(f"文字コード検出結果: {result}")
            return result['encoding']
        except Exception as e:
            logger.error(f"文字コード検出エラー: {str(e)}")
            return 'utf-8'

    @staticmethod
    def read_excel(file):
        try:
            logger.debug("Excelファイル読み込み開始")
            df = pd.read_excel(file)
            logger.debug(f"読み込まれたデータ形状: {df.shape}")
            logger.debug(f"カラム名: {df.columns.tolist()}")
            logger.debug(f"データ型: {df.dtypes}")
            return df
        except Exception as e:
            logger.error(f"Excelファイル読み込みエラー: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def read_csv(file, file_type=None):
        try:
            logger.debug(f"CSVファイル読み込み開始 (file_type: {file_type})")
            content = file.read()
            encoding = FileProcessor.detect_encoding(content)
            file.seek(0)
            
            logger.debug(f"検出された文字コード: {encoding}")
            
            df = pd.read_csv(io.StringIO(content.decode(encoding)))
            logger.debug(f"読み込まれたデータ形状: {df.shape}")
            logger.debug(f"カラム名: {df.columns.tolist()}")
            logger.debug(f"データ型: {df.dtypes}")
            return df
            
        except Exception as e:
            logger.error(f"CSVファイル読み込みエラー: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def process_data(purchase_history_df, inventory_df, yj_code_df):
        try:
            logger.debug("\n=== データ処理開始 ===")
            logger.debug("入力データフレーム情報:")
            
            # 入力データフレームの検証
            for name, df in {
                "購入履歴": purchase_history_df,
                "在庫データ": inventory_df,
                "YJコード": yj_code_df
            }.items():
                logger.debug(f"\n{name}データフレーム:")
                logger.debug(f"- 型: {type(df)}")
                logger.debug(f"- 行数: {len(df)}")
                logger.debug(f"- カラム: {df.columns.tolist()}")
                logger.debug(f"- データ型: {df.dtypes}")

            # カラムの存在確認
            required_columns = {
                '在庫データ': ['ＹＪコード', '院所名', '法人名'],
                '購入履歴': ['厚労省CD']
            }

            for df_name, columns in required_columns.items():
                df = locals()[f"{df_name}_df"]
                missing_columns = [col for col in columns if col not in df.columns]
                if missing_columns:
                    raise ValueError(f"{df_name}に必要なカラムがありません: {missing_columns}")

            # マージ処理
            merged_df = pd.merge(
                inventory_df,
                purchase_history_df,
                left_on='ＹＪコード',
                right_on='厚労省CD',
                how='left'
            )

            logger.debug("\nマージ後のデータ:")
            logger.debug(f"- 行数: {len(merged_df)}")
            logger.debug(f"- カラム: {merged_df.columns.tolist()}")
            logger.debug(f"- データ型: {merged_df.dtypes}")

            return merged_df

        except Exception as e:
            logger.error(f"データ処理エラー: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def clean_sheet_name(name):
        """シート名をクリーニングし、Excelの制限に適合させる"""
        try:
            logger.debug(f"シート名クリーニング - 入力: '{name}'")
            
            if name is None:
                logger.warning("シート名がNoneです")
                return 'Unknown'
            
            if not isinstance(name, str):
                logger.warning(f"シート名が文字列ではありません: {type(name)}")
                return 'Unknown'
            
            if not name.strip():
                logger.warning("シート名が空です")
                return 'Unknown'
            
            # 無効な文字を置換
            invalid_chars = ['/', '\\', '?', '*', ':', '[', ']']
            cleaned_name = ''.join('_' if c in invalid_chars else c for c in name)
            
            # 長さを制限（Excel制限: 31文字）
            final_name = cleaned_name[:31].strip()
            
            logger.debug(f"クリーニング後のシート名: '{final_name}'")
            return final_name
            
        except Exception as e:
            logger.error(f"シート名クリーニングエラー: {str(e)}")
            logger.error(traceback.format_exc())
            return 'Unknown'

    @staticmethod
    def generate_excel(df):
        """Excelファイルを生成し、バイトストリームとして返す"""
        logger.debug("\n=== Excel生成開始 ===")
        
        if df is None or df.empty:
            logger.error("空のデータフレームが渡されました")
            return None
        
        try:
            logger.debug("入力データフレーム情報:")
            logger.debug(f"行数: {df.shape[0]}")
            logger.debug(f"カラム: {df.columns.tolist()}")
            logger.debug(f"データ型: {df.dtypes}")
            logger.debug(f"データの最初の数行:\n{df.head()}")

            excel_buffer = io.BytesIO()
            required_columns = ['院所名', '法人名', '品名・規格', '在庫量', '単位', '新薬品コード', '使用期限', 'ロット番号', '引取り可能数']
            
            # カラムの存在確認とデータ型の検証
            logger.debug("必要なカラムの確認を開始")
            
            # カラムの存在確認と型チェック
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                error_msg = f"必要なカラムがありません: {missing_columns}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug("データ型の検証を開始")
            for col in df.columns:
                logger.debug(f"カラム '{col}' のデータ型: {df[col].dtype}")
                # null値のチェック
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    logger.warning(f"カラム '{col}' に {null_count} 個のnull値が存在します")

            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                logger.debug("ExcelWriterの初期化完了")
                unique_names = df['院所名'].unique()
                logger.debug(f"\n処理対象院所数: {len(unique_names)}")

                logger.debug(f"処理対象院所数: {len(unique_names)}")
                
                for name in unique_names:
                    try:
                        if pd.isna(name):
                            logger.warning(f"院所名がNaNです: {name}")
                            continue
                            
                        sheet_name = FileProcessor.clean_sheet_name(str(name))
                        logger.debug(f"処理中の院所: {name}")
                        logger.debug(f"クリーニング後のシート名: '{sheet_name}'")
                        
                        # シート名の検証
                        if not sheet_name or len(sheet_name.strip()) == 0:
                            logger.error(f"無効なシート名が生成されました: '{sheet_name}'")
                            continue
                        
                        sheet_df = df[df['院所名'] == name].copy()
                        if sheet_df.empty:
                            logger.warning(f"院所 {name} のデータが空です")
                            continue

                        # ヘッダー情報の準備
                        houjin_name = str(sheet_df['法人名'].iloc[0]) if not pd.isna(sheet_df['法人名'].iloc[0]) else ''
                        insho_name = str(sheet_df['院所名'].iloc[0]) if not pd.isna(sheet_df['院所名'].iloc[0]) else ''
                        
                        header_data = pd.DataFrame([
                            ['不良在庫引き取り依頼', None, None],
                            [None, None, None],
                            [f"{houjin_name} {insho_name}".strip(), None, '御中'],
                            [None, None, None],
                            ['下記の不良在庫につきまして、引き取りのご検討を賜れますと幸いです。', None, None],
                            [None, None, None]
                        ])

                        # 表示用データフレームの準備
                        display_columns = ['品名・規格', '在庫量', '単位', '新薬品コード', '使用期限', 'ロット番号', '引取り可能数']
                        display_df = sheet_df[display_columns].copy()

                        # データの書き込み
                        header_data.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        display_df.to_excel(writer, sheet_name=sheet_name, startrow=len(header_data), index=False)

                        # シートの書式設定
                        worksheet = writer.sheets[sheet_name]
                        
                        # 列幅の設定
                        column_widths = {
                            'A': 35,  # 品名・規格
                            'B': 15,  # 在庫量
                            'C': 10,  # 単位
                            'D': 15,  # 新薬品コード
                            'E': 15,  # 使用期限
                            'F': 15,  # ロット番号
                            'G': 20   # 引取り可能数
                        }
                        
                        for col, width in column_widths.items():
                            worksheet.column_dimensions[col].width = width
                        
                        # 行の高さを設定
                        for row in range(1, worksheet.max_row + 1):
                            worksheet.row_dimensions[row].height = 30

                        # フォントサイズを設定
                        for row in worksheet.rows:
                            for cell in row:
                                if cell.value is not None:
                                    cell.font = Font(size=14)

                    except Exception as e:
                        logger.error(f"シート '{sheet_name}' の処理でエラー: {str(e)}")
                        logger.error(traceback.format_exc())
                        continue

            excel_buffer.seek(0)
            return excel_buffer

        except Exception as e:
            logger.error(f"Excel生成エラー: {str(e)}")
            logger.error(traceback.format_exc())
            return None
