# api_app.py - Flask API-only application
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import os

from database import DatabaseManager
from calculations import (
    calculate_dashboard_data,
    calculate_project_summary,
    calculate_project_work_summary,
    determine_health,
    _avg_progress,
    _today_vs_recent_workers,
)
from utils import parse_int, parse_float
from auth import AuthManager
from api_routes import register_additional_routes

app = Flask(__name__)

# CORS 설정 (React 앱에서 접근 허용)
CORS(app, origins=["http://localhost:3000", "http://localhost:5173"])

# JWT 설정
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change_me_in_production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

# JSON 한글 지원
app.config['JSON_AS_ASCII'] = False

# 데이터베이스 매니저 초기화
try:
    dm = DatabaseManager()
    auth_manager = AuthManager(dm)
    print("✅ PostgreSQL 데이터베이스 연결 성공")
except Exception as e:
    print(f"❌ 데이터베이스 연결 실패: {e}")
    exit(1)

# ===== 인증 API =====
@app.route('/api/auth/login', methods=['POST'])
def login():
    """사용자 로그인"""
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

        return jsonify({
            'access_token': access_token,
            'user': {
                'username': username,
                'role': user['role'],
                'projects': user.get('projects', [])
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'로그인 처리 중 오류: {str(e)}'}), 500

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """현재 사용자 정보 조회"""
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
        return jsonify({'error': f'사용자 정보 조회 실패: {str(e)}'}), 500

# ===== 프로젝트 API =====
@app.route('/api/projects', methods=['GET'])
@jwt_required()
def get_projects():
    """프로젝트 목록 조회"""
    try:
        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)

        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404

        projects_data = dm.get_projects()
        labor_costs = dm.get_labor_costs()

        # 접근 가능한 프로젝트 선별
        if user['role'] == 'admin':
            project_items = projects_data.items()
        else:
            allowed = set(user.get('projects', []))
            project_items = [
                (name, data) for name, data in projects_data.items() if name in allowed
            ]

        project_list = []
        for name, data in project_items:
            avg_progress = _avg_progress(data)
            status, _, _ = determine_health(data, labor_costs)
            project_list.append({
                'id': name,
                'name': name,
                'progress': round(avg_progress, 1),
                'health': status
            })

        # 프로젝트 목록은 리스트 형태로 반환
        return jsonify(project_list), 200

    except Exception as e:
        return jsonify({'error': f'프로젝트 조회 실패: {str(e)}'}), 500

@app.route('/api/projects/<project_id>', methods=['GET'])
@jwt_required()
def get_project_detail(project_id):
    """프로젝트 상세 정보 조회"""
    try:
        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)

        # 권한 확인
        if user['role'] != 'admin' and project_id not in user.get('projects', []):
            return jsonify({'error': '프로젝트 접근 권한이 없습니다.'}), 403

        projects_data = dm.get_projects()
        project_data = projects_data.get(project_id)

        if not project_data:
            return jsonify({'error': '프로젝트를 찾을 수 없습니다.'}), 404

        project_detail = dict(project_data)
        project_detail['id'] = project_id
        project_detail['name'] = project_id

        # 프로젝트 상세 정보는 직접 반환
        return jsonify(project_detail), 200

    except Exception as e:
        return jsonify({'error': f'프로젝트 상세 조회 실패: {str(e)}'}), 500

@app.route('/api/projects/<project_id>/summary', methods=['GET'])
@jwt_required()
def get_project_summary(project_id):
    """프로젝트 요약 (평균 진행률, 인원 변동, 비용, 상태)"""
    try:
        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)

        # 권한 확인
        if user['role'] != 'admin' and project_id not in user.get('projects', []):
            return jsonify({'error': '프로젝트 접근 권한이 없습니다.'}), 403

        projects_data = dm.get_projects()
        project_data = projects_data.get(project_id)
        labor_costs = dm.get_labor_costs()

        if not project_data:
            return jsonify({'error': '프로젝트를 찾을 수 없습니다.'}), 404

        # 평균 진행률
        avg_progress = _avg_progress(project_data)

        # 오늘 vs 최근 인원 비교
        delta_ratio, today_total, recent_avg = _today_vs_recent_workers(project_data)

        # 계약금액 vs 실제 노무비
        work_summary = calculate_project_work_summary(project_id)
        total_contract = sum(item['contract_amount'] for item in work_summary)
        total_labor = sum(item['total_labor_cost'] for item in work_summary)

        # 건강 상태
        status, _, _ = determine_health(project_data, labor_costs)

        return jsonify({
            'progress_avg': round(avg_progress, 1),
            'today_vs_recent': {
                'delta_ratio': round(delta_ratio, 2),
                'today_total': today_total,
                'recent_avg': round(recent_avg, 1),
            },
            'total_contract': total_contract,
            'total_labor_cost': total_labor,
            'health': status,
        }), 200

    except Exception as e:
        return jsonify({'error': f'프로젝트 요약 조회 실패: {str(e)}'}), 500

# ===== 일일 데이터 API =====
@app.route('/api/daily-report', methods=['POST'])
@jwt_required()
def create_daily_report():
    """작업일지 등록"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        work_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        work_type = data.get('work_type')
        workers = parse_int(data.get('workers', 0), 0)
        progress = parse_float(data.get('progress', 0), 0.0)

        if not project_id or not work_type:
            return jsonify({'error': 'project_id와 work_type은 필수입니다.'}), 400

        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)

        if user['role'] != 'admin' and project_id not in user.get('projects', []):
            return jsonify({'error': '프로젝트 접근 권한이 없습니다.'}), 403

        dm.save_daily_data(project_id, work_date, work_type, workers, 0, 0, progress)
        return jsonify({'success': True, 'message': '작업일지가 저장되었습니다.'}), 201

    except Exception as e:
        return jsonify({'error': f'작업일지 저장 실패: {str(e)}'}), 500

@app.route('/api/projects/<project_id>/daily-data', methods=['POST'])
@jwt_required()
def save_daily_data(project_id):
    """일일 작업 데이터 저장"""
    try:
        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)
        
        # 권한 확인
        if user['role'] != 'admin' and project_id not in user.get('projects', []):
            return jsonify({'error': '프로젝트 접근 권한이 없습니다.'}), 403

        data = request.get_json()
        work_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        work_data = data.get('work_data', {})

        projects_data = dm.get_projects()
        if project_id not in projects_data:
            return jsonify({'error': '프로젝트를 찾을 수 없습니다.'}), 404

        # 각 공종별 데이터 저장
        saved_count = 0
        for work_type, values in work_data.items():
            day_workers = parse_int(values.get('day', 0), 0)
            night_workers = parse_int(values.get('night', 0), 0)
            midnight_workers = parse_int(values.get('midnight', 0), 0)
            progress = parse_float(values.get('progress', 0), 0.0)

            dm.save_daily_data(
                project_id, work_date, work_type,
                day_workers, night_workers, midnight_workers, progress
            )
            saved_count += 1

        return jsonify({
            'message': f'{saved_count}개 공종 데이터가 저장되었습니다.',
            'saved_count': saved_count
        }), 200

    except Exception as e:
        return jsonify({'error': f'데이터 저장 실패: {str(e)}'}), 500

# ===== 관리자 대시보드 API =====
@app.route('/api/admin/dashboard', methods=['GET'])
@jwt_required()
def get_admin_dashboard():
    """관리자 대시보드 데이터"""
    try:
        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)
        
        if user['role'] != 'admin':
            return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

        dashboard_data = calculate_dashboard_data()
        return jsonify({'dashboard': dashboard_data}), 200

    except Exception as e:
        return jsonify({'error': f'대시보드 데이터 조회 실패: {str(e)}'}), 500

# ===== 노무단가 API =====
@app.route('/api/labor-costs', methods=['GET'])
@jwt_required()
def get_labor_costs():
    """노무단가 목록 조회"""
    try:
        labor_costs = dm.get_labor_costs()
        return jsonify({'labor_costs': labor_costs}), 200

    except Exception as e:
        return jsonify({'error': f'노무단가 조회 실패: {str(e)}'}), 500

@app.route('/api/admin/labor-costs', methods=['POST'])
@jwt_required()
def save_labor_costs():
    """노무단가 저장 (관리자 전용)"""
    try:
        username = get_jwt_identity()
        users = dm.get_users()
        user = users.get(username)
        
        if user['role'] != 'admin':
            return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

        data = request.get_json()
        work_type = data.get('work_type')
        day_cost = parse_int(data.get('day_cost', 0), 0)
        night_cost = parse_int(data.get('night_cost', 0), 0)
        midnight_cost = parse_int(data.get('midnight_cost', 0), 0)

        if not work_type:
            return jsonify({'error': '공종명을 입력해주세요.'}), 400

        dm.save_labor_cost(work_type, day_cost, night_cost, midnight_cost)
        return jsonify({'message': f'{work_type} 노무단가가 저장되었습니다.'}), 200

    except Exception as e:
        return jsonify({'error': f'노무단가 저장 실패: {str(e)}'}), 500

# ===== 헬스 체크 =====
@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'healthy',
        'service': 'LaborApp API',
        'version': '1.0.0'
    }), 200

# ===== 에러 핸들러 =====
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'API 엔드포인트를 찾을 수 없습니다.'}), 404

@app.errorhandler(500)
def internal_error(error):
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

# 추가 라우트 등록
register_additional_routes(app, dm)

if __name__ == '__main__':
    print("🚀 LaborApp API 서버 시작...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)