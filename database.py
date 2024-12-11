import os
import psycopg2
from psycopg2.extras import DictCursor

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            host=os.environ['PGHOST'],
            port=os.environ['PGPORT']
        )
        self._create_tables()

    def _create_tables(self):
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

    def verify_user(self, username, password_hash):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT * FROM users WHERE username = %s AND password_hash = %s",
                (username, password_hash)
            )
            return cur.fetchone()

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
        with self.conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO inventory 
                (yj_code, product_name, quantity, expiry_date, pharmacy_id)
                VALUES (%s, %s, %s, %s, %s)
            """, inventory_data)
            self.conn.commit()

    def get_inventory(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM inventory ORDER BY uploaded_at DESC")
            return cur.fetchall()
