import os
import psycopg2
from psycopg2.extras import DictCursor

class Database:
    def __init__(self):
        self.conn = None
        try:
            self._connect()
            self._create_tables()
        except Exception as e:
            print(f"データベース初期化エラー: {str(e)}")
            import traceback
            traceback.print_exc()

    def _connect(self):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if self.conn is None or (hasattr(self.conn, 'closed') and self.conn.closed):
                    print("\n=== データベース接続情報 ===")
                    print(f"接続試行: {retry_count + 1}/{max_retries}")
                    print(f"Host: {os.environ.get('PGHOST', 'Not set')}")
                    print(f"Port: {os.environ.get('PGPORT', 'Not set')}")
                    print(f"Database: {os.environ.get('PGDATABASE', 'Not set')}")
                    print(f"User: {os.environ.get('PGUSER', 'Not set')}")
                    print("===========================\n")
                    
                    connection_params = {
                        'dbname': os.environ['PGDATABASE'],
                        'user': os.environ['PGUSER'],
                        'password': os.environ['PGPASSWORD'],
                        'host': os.environ['PGHOST'],
                        'port': os.environ['PGPORT'],
                        'connect_timeout': 30,
                        'application_name': 'PharmaInventoryManager'
                    }
                    
                    print("接続パラメータ:", connection_params)
                    self.conn = psycopg2.connect(**connection_params)
                    self.conn.autocommit = True  # 自動コミットを有効化
                    print("データベース接続に成功しました")
                    return
                return
            except Exception as e:
                print(f"データベース接続エラー (試行 {retry_count + 1}/{max_retries}): {str(e)}")
                print(f"エラーの種類: {type(e).__name__}")
                import traceback
                print("スタックトレース:")
                traceback.print_exc()
                self.conn = None
                retry_count += 1
                if retry_count < max_retries:
                    import time
                    time.sleep(5)  # 再試行前に5秒待機
                else:
                    raise

    def _create_tables(self):
        try:
            self._connect()
            if self.conn is None:
                raise Exception("データベース接続に失敗しました")
                
            with self.conn.cursor() as cur:
                # ユーザーテーブル
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(100) UNIQUE NOT NULL,
                        password_hash VARCHAR(200) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 在庫データテーブル
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS inventory (
                        id SERIAL PRIMARY KEY,
                        yj_code VARCHAR(100),
                        product_name VARCHAR(200),
                        quantity INTEGER,
                        expiry_date DATE,
                        pharmacy_id VARCHAR(100),
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.conn.commit()
                print("データベーステーブルの作成が完了しました")
        except Exception as e:
            print(f"テーブル作成エラー: {str(e)}")
            print(f"エラーの種類: {type(e).__name__}")
            import traceback
            print("スタックトレース:")
            traceback.print_exc()
            if self.conn:
                self.conn.rollback()
            raise

    def verify_user(self, username, password_hash):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._connect()  # 接続状態を確認し、必要に応じて再接続
                with self.conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM users WHERE username = %s AND password_hash = %s",
                        (username, password_hash)
                    )
                    return cur.fetchone()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"データベース接続エラー（試行 {attempt + 1}/{max_retries}）: {str(e)}")
                if attempt == max_retries - 1:  # 最後の試行でも失敗した場合
                    raise
                self.conn = None  # 接続をリセット
                continue

    def create_user(self, username, password_hash):
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, password_hash)
                )
                self.conn.commit()
                return True
        except psycopg2.Error:
            self.conn.rollback()
            return False

    def save_inventory(self, inventory_data):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._connect()  # 接続状態を確認し、必要に応じて再接続
                with self.conn.cursor() as cur:
                    cur.executemany("""
                        INSERT INTO inventory 
                        (yj_code, product_name, quantity, expiry_date, pharmacy_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, inventory_data)
                    self.conn.commit()
                break
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"データベース接続エラー（試行 {attempt + 1}/{max_retries}）: {str(e)}")
                if attempt == max_retries - 1:  # 最後の試行でも失敗した場合
                    raise
                self.conn = None  # 接続をリセット
                continue

    def get_inventory(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM inventory ORDER BY uploaded_at DESC")
            return cur.fetchall()
