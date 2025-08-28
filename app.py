# app.py - 메인 애플리케이션 (PostgreSQL 버전)
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import date, datetime
import os

# PostgreSQL 데이터베이스 매니저 사용
from database import DatabaseManager
from calculations import calculate_project_work_summary
from admin_routes import register_admin_routes
from user_routes import register_user_routes

app = Flask(__name__)
# 세션 키는 환경변수 우선
app.secret_key = os.environ.get('SECRET_KEY', 'change_me_in_env')
app.config['JSON_AS_ASCII'] = False

# PostgreSQL 데이터 매니저 초기화
try:
    dm = DatabaseManager()
    print("✅ PostgreSQL 데이터베이스 연결 성공")
except Exception as e:
    print(f"❌ 데이터베이스 연결 실패: {e}")
    exit(1)

# 데이터 새로고침 제거 (PostgreSQL은 실시간 연결)
# @app.before_request 제거

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

# ===== 기본 인증 라우트 =====
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']

    try:
        users = dm.get_users()
        if username in users and users[username]['password'] == password:
            if users[username].get('status') == 'inactive':
                return render_template('login.html', error='계정이 비활성화되었습니다.')
            
            session['username'] = username
            session['role'] = users[username]['role']
            
            if users[username]['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_projects'))
        else:
            return render_template('login.html', error='아이디 또는 비밀번호가 틀렸습니다.')
    except Exception as e:
        print(f"로그인 에러: {e}")
        return render_template('login.html', error='데이터베이스 연결 문제가 발생했습니다.')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== 공통 유틸리티 라우트 =====
@app.route('/check-work-type-similarity', methods=['POST'])
def check_work_type_similarity():
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
    labor_costs = dm.get_labor_costs()
    return jsonify({'work_types': list(labor_costs.keys())})

@app.route('/admin/update-work-type-name', methods=['POST'])
def update_work_type_name():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
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
        # 실제로는 database.py에 메서드 추가 필요
        return jsonify({'success': False, 'message': '공종명 변경은 관리자에게 문의하세요.'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

# ===== 시스템 초기화 제거 =====
# reset-all-data 라우트 제거 (PostgreSQL에서는 필요없음)

# ===== 라우트 등록 =====
register_admin_routes(app, dm)
register_user_routes(app, dm)

# ===== 실행 =====
if __name__ == '__main__':
    print("🚀 노무비 관리 시스템 시작...")
    try:
        users = dm.get_users()
        projects = dm.get_projects()
        labor_costs = dm.get_labor_costs()
        print(f"📊 데이터 로드: 프로젝트 {len(projects)}개, 사용자 {len(users)}개, 노무단가 {len(labor_costs)}개")
    except Exception as e:
        print(f"❌ 데이터 확인 실패: {e}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)