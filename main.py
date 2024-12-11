import streamlit as st
import pandas as pd
from auth import Auth
from file_processor import FileProcessor
from database import Database

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
                with st.spinner('データを処理中...'):
                    # ファイル読み込み
                    purchase_df = FileProcessor.read_excel(purchase_file)
                    inventory_df = FileProcessor.read_csv(inventory_file, file_type='inventory')
                    yj_code_df = FileProcessor.read_csv(yj_code_file)

                    # データ処理
                    result_df = FileProcessor.process_data(
                        purchase_df,
                        inventory_df,
                        yj_code_df
                    )

                    # 結果の表示
                    st.subheader("処理結果")
                    
                    # 統計情報の表示
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("総在庫アイテム数", len(result_df))
                        st.metric("不良在庫アイテム数", len(result_df[result_df['不良在庫']]))
                    
                    with col2:
                        avg_days = int(result_df['有効期限切れまでの日数'].mean())
                        st.metric("平均有効期限残日数", f"{avg_days}日")
                        urgent_items = len(result_df[result_df['有効期限切れまでの日数'] <= 90])
                        st.metric("緊急対応必要(3ヶ月以内)", urgent_items)
                    
                    with col3:
                        total_quantity = int(result_df['在庫量'].sum())
                        st.metric("総在庫数", total_quantity)
                        dead_stock_qty = int(result_df[result_df['不良在庫']]['在庫量'].sum())
                        st.metric("不良在庫数", dead_stock_qty)
                    
                    # データテーブルの表示
                    st.dataframe(
                        result_df,
                        column_config={
                            "不良在庫": st.column_config.CheckboxColumn("不良在庫"),
                            "有効期限切れまでの日数": st.column_config.NumberColumn(
                                "有効期限切れまでの日数",
                                help="マイナスの値は有効期限切れを示します",
                                format="%d日"
                            ),
                            "在庫量": st.column_config.NumberColumn(
                                "在庫量",
                                format="%d"
                            )
                        },
                        hide_index=True
                    )

                    # Excelダウンロードボタン
                    excel = FileProcessor.generate_excel(result_df)
                    st.download_button(
                        label="Excel形式でダウンロード",
                        data=excel,
                        file_name="processed_inventory.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    

                    # データベースへの保存
                    db = Database()
                    inventory_data = result_df.values.tolist()
                    db.save_inventory(inventory_data)
                    st.success("データベースに保存しました")

            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()
