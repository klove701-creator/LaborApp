# app.py - 메인 애플리케이션 (분할 버전)
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import date, datetime
import os

# 분할된 모듈들 import
from models import DataManager
from calculations import calculate_project_work_summary
from admin_routes import register_admin_routes
from user_routes import register_user_routes

app = Flask(__name__)
# 세션 키는 환경변수 우선
app.secret_key = os.environ.get('SECRET_KEY', 'change_me_in_env')
app.config['JSON_AS_ASCII'] = False

# 데이터 매니저 초기화
dm = DataManager()

# 데이터 새로고침 (개발/디버깅용)
@app.before_request
def refresh_data():
    if not hasattr(app, '_data_last_check') or (datetime.now() - app._data_last_check).seconds > 5:
        dm.load_data()  # 5초마다 데이터 다시 로드
        app._data_last_check = datetime.now()

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

    if username in dm.users and dm.users[username]['password'] == password:
        session['username'] = username
        session['role'] = dm.users[username]['role']
        if dm.users[username]['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_projects'))
    else:
        return render_template('login.html', error='아이디 또는 비밀번호가 틀렸습니다.')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== 공통 유틸리티 라우트 =====
@app.route('/check-work-type-similarity', methods=['POST'])
def check_work_type_similarity():
    data = request.get_json()
    new_type = (data.get('work_type', '') or '').strip()
    existing_types = list(dm.labor_costs.keys())
    similar_types = []
    for existing in existing_types:
        if new_type in existing or existing in new_type:
            if new_type.lower() != existing.lower():
                similar_types.append(existing)
    return jsonify({'similar_types': similar_types, 'has_similarity': len(similar_types) > 0})

@app.route('/get-available-work-types')
def get_available_work_types():
    return jsonify({'work_types': list(dm.labor_costs.keys())})

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
        if new_name in dm.labor_costs and new_name != old_name:
            return jsonify({'success': False, 'message': '이미 존재하는 공종명입니다.'})
        
        # 노무단가에서 공종명 변경
        if old_name in dm.labor_costs:
            dm.labor_costs[new_name] = dm.labor_costs.pop(old_name)
        
        # 모든 프로젝트/일일 데이터에서 공종명 변경
        for project_data in dm.projects_data.values():
            if 'work_types' in project_data and old_name in project_data['work_types']:
                idx = project_data['work_types'].index(old_name)
                project_data['work_types'][idx] = new_name
            for daily_data in project_data.get('daily_data', {}).values():
                if old_name in daily_data:
                    daily_data[new_name] = daily_data.pop(old_name)
        
        dm.save_data()
        return jsonify({'success': True, 'message': '공종명이 변경되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

# ===== 시스템 초기화 (개발용 - 운영환경에서는 비활성화) =====
@app.route('/reset-all-data', methods=['POST'])
def reset_all_data():
    # 운영환경에서는 초기화 기능 완전 차단
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PORT'):
        return """
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .error { background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; color: #721c24; }
            .button { display: inline-block; background: #007bff; color: white; padding: 10px 20px;
                      text-decoration: none; border-radius: 5px; margin: 5px; }
        </style>
        <div class="error">
            <h2>❌ 기능 비활성화</h2>
            <p>운영 환경에서는 데이터 초기화가 차단됩니다.</p>
            <p>실제 사용 중인 데이터 보호를 위해 이 기능은 개발 환경에서만 사용 가능합니다.</p>
        </div>
        <div style="margin-top: 30px;">
            <a href="/admin" class="button">관리자 대시보드로</a>
        </div>
        """
    
    # 개발환경에서만 초기화 허용
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    try:
        dm._create_default_data()
        dm.save_data()
        return """
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .success { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; }
            .button { display: inline-block; background: #007bff; color: white; padding: 10px 20px;
                      text-decoration: none; border-radius: 5px; margin: 5px; }
        </style>
        <div class="success"><h2>개발환경 초기화 완료</h2></div>
        <div style="margin-top: 30px;">
            <a href="/" class="button">홈으로</a>
        </div>
        """
    except Exception as e:
        return f"초기화 실패: {str(e)}"

# ===== 라우트 등록 =====
register_admin_routes(app, dm)
register_user_routes(app, dm)

# ===== 실행 =====
if __name__ == '__main__':
    print("🚀 노무비 관리 시스템 시작...")
    print(f"📊 데이터 로드: 프로젝트 {len(dm.projects_data)}개, 노무단가 {len(dm.labor_costs)}개")
    print(f"💾 데이터 파일: {dm.DATA_FILE}")
    print("🌐 브라우저에서 http://localhost:5000 접속")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)