# app.py - Railway 배포용 메인 애플리케이션
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import date, datetime
import os
import logging

# 환경 설정
from dotenv import load_dotenv
load_dotenv()  # 로컬 개발시에만 .env 파일 로드

# PostgreSQL 데이터베이스 매니저 사용
from database import DatabaseManager
from calculations import calculate_project_work_summary
from admin_routes import register_admin_routes
from user_routes import register_user_routes

# Flask 앱 초기화
app = Flask(__name__)

# ===== Railway 배포용 설정 =====
# HTTPS 프록시 처리 (Railway는 HTTPS 프록시 사용)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# 환경변수에서 보안 설정 가져오기
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-please-change-in-production')
app.config['JSON_AS_ASCII'] = False

# 프로덕션 환경에서 보안 쿠키 설정
if os.environ.get('FLASK_ENV') == 'production':
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_HTTPONLY=True,
    )

# 로깅 설정 (Railway에서 로그 확인용)
if not app.debug:
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.info('노무비 관리 시스템 시작')

# ===== 데이터베이스 연결 =====
try:
    # DATABASE_URL 환경변수 확인 (Railway에서 자동 주입)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        app.logger.info('PostgreSQL 데이터베이스 URL 감지됨')
        dm = DatabaseManager()  # PostgreSQL 사용
        app.logger.info("✅ PostgreSQL 데이터베이스 연결 성공")
    else:
        app.logger.warning('DATABASE_URL이 없습니다. 로컬 개발 모드로 실행합니다.')
        # 로컬 개발용 fallback (필요시 파일 기반 DB 등)
        dm = DatabaseManager()  # 기본 설정 사용
        
except Exception as e:
    app.logger.error(f"❌ 데이터베이스 연결 실패: {e}")
    # 개발 환경에서는 계속 진행, 프로덕션에서는 종료
    if os.environ.get('FLASK_ENV') == 'production':
        exit(1)
    else:
        print(f"개발 모드: 데이터베이스 오류 무시 - {e}")
        dm = None

# utils에서 데이터 매니저 전역 설정
from utils import set_data_manager
if dm:
    set_data_manager(dm)

# ===== 템플릿 필터 및 컨텍스트 =====
@app.template_filter('format_currency')
def format_currency(value):
    """숫자를 천 단위 콤마가 포함된 문자열로 변환"""
    if value is None:
        return "0"
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return str(value)

@app.context_processor
def utility_processor():
    return dict(
        calculate_project_work_summary=calculate_project_work_summary,
        sum=sum
    )

# ===== 헬스체크 라우트 (Railway 모니터링용) =====
@app.route('/health')
def health_check():
    """Railway 헬스체크용 엔드포인트"""
    try:
        if dm:
            # 간단한 DB 연결 테스트
            users = dm.get_users()
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'users_count': len(users)
            }), 200
        else:
            return jsonify({
                'status': 'partial',
                'database': 'disconnected'
            }), 200
    except Exception as e:
        app.logger.error(f"헬스체크 실패: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ===== 기본 인증 라우트 =====
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    if not dm:
        return render_template('login.html', error='데이터베이스 연결 문제가 발생했습니다.')
    
    username = request.form['username']
    password = request.form['password']

    try:
        users = dm.get_users()
        if username in users and users[username]['password'] == password:
            if users[username].get('status') == 'inactive':
                return render_template('login.html', error='계정이 비활성화되었습니다.')
            
            session['username'] = username
            session['role'] = users[username]['role']
            
            app.logger.info(f'사용자 로그인: {username} ({users[username]["role"]})')
            
            if users[username]['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_projects'))
        else:
            app.logger.warning(f'로그인 실패: {username}')
            return render_template('login.html', error='아이디 또는 비밀번호가 틀렸습니다.')
    except Exception as e:
        app.logger.error(f"로그인 에러: {e}")
        return render_template('login.html', error='시스템 오류가 발생했습니다.')

@app.route('/logout')
def logout():
    username = session.get('username', '알 수 없음')
    session.clear()
    app.logger.info(f'사용자 로그아웃: {username}')
    return redirect(url_for('login'))

# ===== 공통 유틸리티 라우트 =====
@app.route('/check-work-type-similarity', methods=['POST'])
def check_work_type_similarity():
    if not dm:
        return jsonify({'error': '데이터베이스 연결 없음'}), 500
        
    data = request.get_json()
    new_type = (data.get('work_type', '') or '').strip()
    labor_costs = dm.get_labor_costs()
    existing_types = list(labor_costs.keys())
    similar_types = []
    for existing in existing_types:
        if new_type in existing or existing in new_type:
            if new_type.lower() != existing.lower():
                similar_types.append(existing)
    return jsonify({'similar_types': similar_types, 'has_similarity': len(similar_types) > 0})

@app.route('/get-available-work-types')
def get_available_work_types():
    if not dm:
        return jsonify({'error': '데이터베이스 연결 없음'}), 500
    
    labor_costs = dm.get_labor_costs()
    return jsonify({'work_types': list(labor_costs.keys())})

@app.route('/admin/update-work-type-name', methods=['POST'])
def update_work_type_name():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    if not dm:
        return jsonify({'success': False, 'message': '데이터베이스 연결 없음'})
    
    try:
        data = request.get_json()
        old_name = (data.get('old_name', '') or '').strip()
        new_name = (data.get('new_name', '') or '').strip()
        if not old_name or not new_name:
            return jsonify({'success': False, 'message': '공종명을 입력해주세요.'})
        if old_name == new_name:
            return jsonify({'success': True, 'message': '변경사항이 없습니다.'})
        
        labor_costs = dm.get_labor_costs()
        if new_name in labor_costs and new_name != old_name:
            return jsonify({'success': False, 'message': '이미 존재하는 공종명입니다.'})
        
        # PostgreSQL에서 공종명 변경 (복잡한 작업이므로 여기서는 간단히 처리)
        return jsonify({'success': False, 'message': '공종명 변경은 데이터베이스 관리자에게 문의하세요.'})
        
    except Exception as e:
        app.logger.error(f'공종명 변경 오류: {e}')
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

# ===== 라우트 등록 =====
if dm:
    register_admin_routes(app, dm)
    register_user_routes(app, dm)

# ===== 에러 핸들러 =====
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message='페이지를 찾을 수 없습니다.'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'서버 오류: {error}')
    return render_template('error.html', 
                         error_code=500, 
                         error_message='내부 서버 오류가 발생했습니다.'), 500

# ===== 실행 =====
if __name__ == '__main__':
    print("🚀 노무비 관리 시스템 시작...")
    
    # 데이터 상태 확인
    if dm:
        try:
            users = dm.get_users()
            projects = dm.get_projects()
            labor_costs = dm.get_labor_costs()
            print(f"📊 데이터 로드: 프로젝트 {len(projects)}개, 사용자 {len(users)}개, 노무단가 {len(labor_costs)}개")
        except Exception as e:
            print(f"❌ 데이터 확인 실패: {e}")
    else:
        print("⚠️  데이터베이스 연결 없이 실행 중")
    
    # Railway는 PORT 환경변수 제공
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    print(f"🌐 서버 실행: 0.0.0.0:{port} (디버그: {debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)