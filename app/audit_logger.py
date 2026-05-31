import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'opsassist_db'),
        cursorclass=pymysql.cursors.DictCursor
    )

def log_action(user_name, action_type, query_text, result_summary, sector='All'):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs 
            (user_name, action_type, query_text, result_summary, sector)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_name, action_type, query_text, str(result_summary)[:500], sector))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")