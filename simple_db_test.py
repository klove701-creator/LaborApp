import psycopg2
import os
from urllib.parse import urlparse

def test_connection():
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("DATABASE_URL not found in environment variables")
        return False
    
    try:
        parsed = urlparse(database_url)
        masked_url = f"{parsed.scheme}://{parsed.username}:****@{parsed.hostname}:{parsed.port}{parsed.path}"
        print(f"Testing connection: {masked_url}")
    except:
        print("Failed to parse DATABASE_URL")
    
    try:
        conn = psycopg2.connect(database_url, connect_timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"SUCCESS: Connected to PostgreSQL")
        print(f"Version: {version}")
        
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print(f"Database: {db_info[0]}")
        print(f"User: {db_info[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False

if __name__ == '__main__':
    print("Database Connection Test")
    print("=" * 50)
    success = test_connection()
    if not success:
        print("\nPossible solutions:")
        print("1. Check Supabase password in dashboard")
        print("2. Reset database password")  
        print("3. Update Railway environment variable")