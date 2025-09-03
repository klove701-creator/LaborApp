# api_app.py - Railway 배포용 Flask API application
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import os
import logging

# 환경 설정
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Railway HTTPS 프록시 처리
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# CORS 설정 (React 앱에서 접근 허용)
cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
CORS(app, origins=cors_origins)

# JWT 설정
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change_me_in_production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

# JSON 한글 지원
app.config['JSON_AS_ASCII'] = False

# 프로덕션에서 보안 쿠키 설정
if os.environ.get('FLASK_ENV') == 'production':
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_HTTPONLY=True,
    )

# 로깅 설정 (Railway 로그용)
if not app.debug:
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.info('LaborApp API 서버 시작')

# 데이터베이스 매니저 초기화
try:
    from database import DatabaseManager
    dm = DatabaseManager()
    app.logger.info("✅ PostgreSQL 데이터베이스 연결 성공")
except Exception as e:
    app.logger.error(f"❌ 데이터베이스 연결 실패: {e}")
    if os.environ.get('FLASK_ENV') == 'production':
        exit(1)
    else:
        print(f"개발 모드: 데이터베이스 오류 무시 - {e}")
        dm = None

# 인증 매니저 초기화
try:
    from auth import AuthManager
    auth_manager = AuthManager(dm) if dm else None
except ImportError as e:
    app.logger.warning(f"AuthManager 임포트 실패: {e}")
    auth_manager = None

# 계산 함수들 임포트
try:
    from calculations import calculate_dashboard_data, calculate_project_summary, determine_health
    from utils import parse_int, parse_float
except ImportError as e:
    app.logger.warning(f"계산 모듈 임포트 실패: {e}")
    # Fallback 함수들
    def calculate_dashboard_data():
        return {'message': '계산 모듈이 없습니다.'}
    def calculate_project_summary(*args):
        return {}, {}
    def determine_health(*args):
        return 'unknown', 'gray', {}
    def parse_int(value, default=0):
        try: return int(value)
        except: return default
    def parse_float(value, default=0.0):
        try: return float(value)
        except: return default

# ===== 헬스 체크 =====
@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    try:
        database_status = 'connected' if dm else 'disconnected'
        if dm:
            users = dm.get_users()
            user_count = len(users)
        else:
            user_count = 0
        
        return jsonify({
            'status': 'healthy',
            'service': 'LaborApp API',
            'version': '1.0.0',
            'database': database_status,
            'users': user_count,
            'environment': os.environ.get('FLASK_ENV', 'development')
        }), 200
    except Exception as e:
        app.logger.error(f"헬스체크 실패: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ===== 인증 API =====
@app.route('/api/auth/login', methods=['POST'])
def login():
    """사용자 로그인"""
    if not dm or not auth_manager:
        return jsonify({'error': '데이터베이스 연결 문제입니다.'}), 500
        
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': '사용자명과 비밀번호를 입력해주세요.'}), 400

        user = auth_manager.authenticate_user(username, password)
        if not user:
            return jsonify({'error': '아이디 또는 비밀번호가 틀렸습니다.'}), 401

        if user.get('status') == 'inactive':
            return jsonify({'error': '계정이 비활성화되었습니다.'}), 401

        # JWT 토큰 생성
        access_token = create_access_token(
            identity=username,
            additional_claims={'role': user['role']}
        )

        app.logger.info(f"사용자 로그인 성공: {username}")
        
        return jsonify({
            'access_token': access_token,
            'user': {
                'username': username,
                'role': user['role'],
                'projects': user.get('projects', [])
            }
        }), 200

    except Exception as e:
        app.logger.error(f"로그인 처리 오류: {e}")
        return jsonify({'error': f'로그인 처리 중 오류: {str(e)}'}), 500

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """현재 사용자 정보 조회"""
    if not dm:
        return jsonify({'error': '데이터베이스 연결 문제입니다.'}), 500
        
    try:
        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)
        
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404

        return jsonify({
            'username': username,
            'role': user['role'],
            'projects': user.get('projects', []),
            'status': user.get('status', 'active')
        }), 200

    except Exception as e:
        app.logger.error(f"사용자 정보 조회 실패: {e}")
        return jsonify({'error': f'사용자 정보 조회 실패: {str(e)}'}), 500

# ===== 프로젝트 API =====
@app.route('/api/projects', methods=['GET'])
@jwt_required()
def get_projects():
    """프로젝트 목록 조회 (역할별 필터링)"""
    if not dm:
        return jsonify({'error': '데이터베이스 연결 문제입니다.'}), 500
        
    try:
        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)
        
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404

        projects_data = dm.get_projects()
        
        # 관리자는 모든 프로젝트, 사용자는 할당된 프로젝트만
        if user['role'] == 'admin':
            return jsonify({'projects': projects_data}), 200
        else:
            user_projects = user.get('projects', [])
            filtered_projects = {
                name: data for name, data in projects_data.items()
                if name in user_projects
            }
            return jsonify({'projects': filtered_projects}), 200

    except Exception as e:
        app.logger.error(f"프로젝트 조회 실패: {e}")
        return jsonify({'error': f'프로젝트 조회 실패: {str(e)}'}), 500

# ===== 간단한 테스트 라우트 =====
@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """API 테스트용 엔드포인트"""
    return jsonify({
        'message': 'API가 정상 작동합니다! 🎉',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected' if dm else 'disconnected',
        'auth_manager': 'loaded' if auth_manager else 'not loaded'
    }), 200

# ===== 에러 핸들러 =====
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'API 엔드포인트를 찾을 수 없습니다.'}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"서버 내부 오류: {error}")
    return jsonify({'error': '서버 내부 오류가 발생했습니다.'}), 500

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': '토큰이 만료되었습니다. 다시 로그인해주세요.'}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'error': '유효하지 않은 토큰입니다.'}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'error': '인증 토큰이 필요합니다.'}), 401

# ===== 추가 라우트 등록 (안전하게) =====
try:
    from api_routes import register_additional_routes
    register_additional_routes(app, dm)
    app.logger.info("추가 라우트 등록 완료")
except ImportError as e:
    app.logger.warning(f"추가 라우트 파일 없음: {e}")

if __name__ == '__main__':
    print("🚀 LaborApp API 서버 시작...")
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    print(f"🌐 서버 실행: 0.0.0.0:{port} (디버그: {debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)