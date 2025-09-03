# debug_app.py - 문제 진단용 최소 앱
from flask import Flask, jsonify
import os
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>🚀 Railway 연결 테스트</h1>
    <p><a href="/debug">디버그 정보 확인</a></p>
    <p><a href="/health">헬스 체크</a></p>
    <p><a href="/env">환경변수 확인</a></p>
    '''

@app.route('/debug')
def debug_info():
    return jsonify({
        'status': 'Railway 연결 성공! 🎉',
        'python_version': sys.version,
        'current_directory': os.getcwd(),
        'files_in_directory': os.listdir('.'),
        'port': os.environ.get('PORT', '없음'),
        'database_url_exists': bool(os.environ.get('DATABASE_URL')),
        'secret_key_exists': bool(os.environ.get('SECRET_KEY')),
        'flask_env': os.environ.get('FLASK_ENV', '없음')
    })

@app.route('/env')
def env_check():
    # 민감한 정보는 존재 여부만 확인
    env_vars = {}
    check_vars = ['PORT', 'DATABASE_URL', 'SECRET_KEY', 'FLASK_ENV', 'PGUSER', 'PGPASSWORD', 'PGHOST', 'PGPORT', 'PGDATABASE']
    
    for var in check_vars:
        value = os.environ.get(var)
        if value:
            if var in ['DATABASE_URL', 'SECRET_KEY', 'PGPASSWORD']:
                env_vars[var] = f"설정됨 ({len(value)}자)"
            else:
                env_vars[var] = value
        else:
            env_vars[var] = "❌ 없음"
    
    return jsonify(env_vars)

@app.route('/health')
def health():
    try:
        # PostgreSQL 연결 테스트
        import psycopg2
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            conn = psycopg2.connect(database_url)
            conn.close()
            db_status = "✅ PostgreSQL 연결 성공"
        else:
            db_status = "❌ DATABASE_URL 없음"
    except Exception as e:
        db_status = f"❌ PostgreSQL 연결 실패: {str(e)}"
    
    return jsonify({
        'app_status': '✅ 앱 실행 중',
        'database_status': db_status,
        'port': os.environ.get('PORT', 'unknown')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)