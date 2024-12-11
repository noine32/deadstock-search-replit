import os
import sys
import logging
import streamlit as st
import pandas as pd
from auth import Auth
from file_processor import FileProcessor
from database import Database

# ロギングの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# 起動時のデバッグ情報
logger.info("アプリケーション起動")
logger.debug(f"環境変数: PGHOST={os.environ.get('PGHOST', 'Not set')}")
logger.debug(f"環境変数: PGPORT={os.environ.get('PGPORT', 'Not set')}")
logger.debug(f"環境変数: PGDATABASE={os.environ.get('PGDATABASE', 'Not set')}")
logger.debug(f"環境変数: PGUSER={os.environ.get('PGUSER', 'Not set')}")

# Streamlit設定
st.set_page_config(
    page_title="医薬品不良在庫管理システム",
    page_icon="💊",
    layout="wide"
)

# 起動時のデバッグ情報
logger.info("アプリケーション起動")

def main():
    st.set_page_config(
        page_title="医薬品不良在庫管理システム",
        page_icon="💊",
        layout="wide"
    )

    # 初期化
    if 'auth' not in st.session_state:
        st.session_state['auth'] = Auth()

    auth = st.session_state['auth']

    # サイドバーにログイン/ログアウト機能を配置
    with st.sidebar:
        st.title("💊 医薬品在庫管理")
        if not auth.is_logged_in():
            tab1, tab2 = st.tabs(["ログイン", "新規登録"])
            
            with tab1:
                with st.form("login_form"):
                    username = st.text_input("ユーザー名")
                    password = st.text_input("パスワード", type="password")
                    if st.form_submit_button("ログイン"):
                        if auth.login(username, password):
                            st.success("ログインしました")
                            st.rerun()
                        else:
                            st.error("ログインに失敗しました")

            with tab2:
                with st.form("register_form"):
                    new_username = st.text_input("新規ユーザー名")
                    new_password = st.text_input("新規パスワード", type="password")
                    if st.form_submit_button("登録"):
                        if auth.register(new_username, new_password):
                            st.success("ユーザー登録が完了しました")
                        else:
                            st.error("ユーザー登録に失敗しました")
        else:
            st.write(f"ログインユーザー: {st.session_state['username']}")
            if st.button("ログアウト"):
                auth.logout()
                st.rerun()

    # メインコンテンツ
    if auth.is_logged_in():
        st.title("医薬品不良在庫管理システム")

        # ファイルアップロードセクション
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("OMEC他院所 (XLSX)")
            purchase_file = st.file_uploader(
                "OMEC他院所ファイルを選択",
                type=['xlsx'],
                key="purchase_history"
            )

        with col2:
            st.subheader("不良在庫データ (CSV)")
            inventory_file = st.file_uploader(
                "不良在庫ファイルを選択",
                type=['csv'],
                key="inventory"
            )

        with col3:
            st.subheader("在庫金額 (CSV)")
            yj_code_file = st.file_uploader(
                "在庫金額ファイルを選択",
                type=['csv'],
                key="yj_code"
            )

        if purchase_file and inventory_file and yj_code_file:
            try:
                logger.info("\n=== データ処理開始 ===")
                logger.info("ファイル情報:")
                logger.info(f"購入履歴ファイル: {purchase_file.name if purchase_file else 'None'}")
                logger.info(f"在庫データファイル: {inventory_file.name if inventory_file else 'None'}")
                logger.info(f"YJコードファイル: {yj_code_file.name if yj_code_file else 'None'}")
                
                with st.spinner('データを処理中...'):
                    logger.info("\nファイル処理を開始します")
                    
                    try:
                        # 購入履歴ファイルの読み込み
                        logger.info("\n1. 購入履歴ファイルを読み込みます")
                        purchase_df = FileProcessor.read_excel(purchase_file)
                        logger.info(f"購入履歴データ情報:")
                        logger.info(f"- 行数: {purchase_df.shape[0]}")
                        logger.info(f"- カラム: {purchase_df.columns.tolist()}")
                        logger.info(f"- データ型:\n{purchase_df.dtypes}")
                        logger.info(f"- 最初の数行:\n{purchase_df.head()}")
                    except Exception as e:
                        logger.error("購入履歴ファイルの読み込みでエラーが発生しました")
                        logger.error(f"エラー種類: {type(e).__name__}")
                        logger.error(f"エラー内容: {str(e)}")
                        raise

                    try:
                        # 在庫データファイルの読み込み
                        logger.info("\n2. 在庫データファイルを読み込みます")
                        inventory_df = FileProcessor.read_csv(inventory_file, file_type='inventory')
                        logger.info(f"在庫データ情報:")
                        logger.info(f"- 行数: {inventory_df.shape[0]}")
                        logger.info(f"- カラム: {inventory_df.columns.tolist()}")
                        logger.info(f"- データ型:\n{inventory_df.dtypes}")
                        logger.info(f"- 最初の数行:\n{inventory_df.head()}")
                    except Exception as e:
                        logger.error("在庫データファイルの読み込みでエラーが発生しました")
                        logger.error(f"エラー種類: {type(e).__name__}")
                        logger.error(f"エラー内容: {str(e)}")
                        raise

                    try:
                        # YJコードファイルの読み込み
                        logger.info("\n3. YJコードファイルを読み込みます")
                        yj_code_df = FileProcessor.read_csv(yj_code_file)
                        logger.info(f"YJコードデータ情報:")
                        logger.info(f"- 行数: {yj_code_df.shape[0]}")
                        logger.info(f"- カラム: {yj_code_df.columns.tolist()}")
                        logger.info(f"- データ型:\n{yj_code_df.dtypes}")
                        logger.info(f"- 最初の数行:\n{yj_code_df.head()}")
                    except Exception as e:
                        logger.error("YJコードファイルの読み込みでエラーが発生しました")
                        logger.error(f"エラー種類: {type(e).__name__}")
                        logger.error(f"エラー内容: {str(e)}")
                        raise

                    # データ処理
                    logger.info("\n4. データ処理を開始します")
                    try:
                        result_df = FileProcessor.process_data(
                            purchase_df,
                            inventory_df,
                            yj_code_df
                        )
                        logger.info("データ処理が完了しました")
                        logger.info(f"処理結果情報:")
                        logger.info(f"- 行数: {result_df.shape[0]}")
                        logger.info(f"- カラム: {result_df.columns.tolist()}")
                        logger.info(f"- データ型:\n{result_df.dtypes}")
                        logger.info(f"- 最初の数行:\n{result_df.head()}")
                    except Exception as e:
                        logger.error("データ処理でエラーが発生しました")
                        logger.error(f"エラー種類: {type(e).__name__}")
                        logger.error(f"エラー内容: {str(e)}")
                        raise

                    # 結果の表示
                    st.subheader("処理結果")
                    st.dataframe(result_df)

                    # Excelファイル生成
                    logger.info("\n5. Excelファイルを生成します")
                    try:
                        excel = FileProcessor.generate_excel(result_df)
                        
                        if excel is not None:
                            logger.info("Excelファイルの生成が完了しました")
                            st.download_button(
                                label="Excel形式でダウンロード",
                                data=excel,
                                file_name="processed_inventory.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            error_msg = "Excelファイルの生成に失敗しました"
                            logger.error(error_msg)
                            st.error(error_msg)
                    except Exception as e:
                        logger.error("Excelファイル生成でエラーが発生しました")
                        logger.error(f"エラー種類: {type(e).__name__}")
                        logger.error(f"エラー内容: {str(e)}")
                        st.error(f"Excelファイルの生成中にエラーが発生しました: {str(e)}")

                    

                    # データベースへの保存
                    db = Database()
                    inventory_data = result_df.values.tolist()
                    db.save_inventory(inventory_data)
                    st.success("データベースに保存しました")

            except Exception as e:
                logger.error("=== エラー発生 ===")
                logger.error(f"エラー種類: {type(e).__name__}")
                logger.error(f"エラー内容: {str(e)}")
                logger.error("スタックトレース:", exc_info=True)
                st.error(f"エラーが発生しました: {str(e)}")
                st.error("詳細はログファイル（app.log）を確認してください。")

if __name__ == "__main__":
    main()
