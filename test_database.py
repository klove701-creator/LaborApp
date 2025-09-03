# test_database.py - 데이터베이스 연결 테스트
import psycopg2
import os
from urllib.parse import urlparse

def test_database_connection(database_url=None):
    """데이터베이스 연결 테스트"""
    
    if not database_url:
        database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return False
    
    # URL 파싱해서 연결 정보 표시 (비밀번호는 마스킹)
    try:
        parsed = urlparse(database_url)
        masked_url = f"{parsed.scheme}://{parsed.username}:{'*' * 8}@{parsed.hostname}:{parsed.port}{parsed.path}"
        print(f"🔗 연결 시도: {masked_url}")
    except:
        print("🔗 연결 문자열 파싱 실패")
    
    try:
        # 연결 테스트
        print("⏳ 데이터베이스 연결 중...")
        conn = psycopg2.connect(
            database_url,
            connect_timeout=10,
            sslmode='prefer'
        )
        
        # 버전 확인
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL 연결 성공!")
        print(f"   버전: {version}")
        
        # 간단한 테스트 쿼리
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print(f"   데이터베이스: {db_info[0]}")
        print(f"   사용자: {db_info[1]}")
        
        # 테이블 목록 확인
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"   테이블 수: {len(tables)}개")
        if tables:
            table_names = [t[0] for t in tables[:5]]  # 처음 5개만
            print(f"   테이블: {', '.join(table_names)}{'...' if len(tables) > 5 else ''}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        error_msg = str(e).strip()
        print(f"❌ 연결 실패: {error_msg}")
        
        # 일반적인 오류별 해결책 제시
        if "password authentication failed" in error_msg:
            print("💡 해결책:")
            print("   1. Supabase에서 데이터베이스 비밀번호 확인")
            print("   2. DATABASE_URL의 비밀번호 부분 확인")
            print("   3. 비밀번호에 특수문자가 있으면 URL 인코딩 필요")
        
        elif "could not connect to server" in error_msg:
            print("💡 해결책:")
            print("   1. 호스트명과 포트 번호 확인")
            print("   2. 네트워크 연결 상태 확인")
            print("   3. Supabase 프로젝트 상태 확인")
        
        elif "does not exist" in error_msg:
            print("💡 해결책:")
            print("   1. 데이터베이스명 확인 (보통 'postgres')")
            print("   2. Supabase 프로젝트 REF 확인")
        
        return False
        
    except Exception as e:
        print(f"❌ 예상하지 못한 오류: {e}")
        return False

def suggest_connection_strings():
    """연결 문자열 예시 제공"""
    print("\n📋 Supabase 연결 문자열 형식:")
    print("="*50)
    print("기본 연결:")
    print("postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
    print("\nConnection Pooling (권장):")
    print("postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres")
    print("\nSSL 모드 포함:")
    print("postgresql://postgres:[PASSWORD]@host:port/postgres?sslmode=require")

if __name__ == '__main__':
    print("🧪 데이터베이스 연결 테스트")
    print("="*50)
    
    # 환경변수에서 DATABASE_URL 확인
    success = test_database_connection()
    
    if not success:
        suggest_connection_strings()
        
        # 사용자 입력으로 다른 연결 문자열 테스트
        print("\n" + "="*50)
        print("💡 다른 연결 문자열을 테스트하려면 입력하세요 (Enter로 건너뛰기):")
        user_url = input("DATABASE_URL: ").strip()
        
        if user_url:
            print("\n🔄 사용자 입력 연결 문자열 테스트:")
            test_database_connection(user_url)
    
    print("\n" + "="*50)
    print("테스트 완료!")