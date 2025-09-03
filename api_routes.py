# api_routes.py - 추가 API 라우트들
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from utils import parse_int, parse_float
from calculations import calculate_project_work_summary

def register_additional_routes(app, dm):
    
    # ===== 프로젝트 관리 API (관리자) =====
    @app.route('/api/admin/projects', methods=['POST'])
    @jwt_required()
    def create_project():
        """프로젝트 생성 (관리자 전용)"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            if user['role'] != 'admin':
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

            data = request.get_json()
            project_name = data.get('project_name', '').strip()
            work_types = data.get('work_types', [])
            contracts = data.get('contracts', {})
            companies = data.get('companies', {})

            if not project_name:
                return jsonify({'error': '프로젝트명을 입력해주세요.'}), 400

            # 프로젝트 중복 확인
            projects_data = dm.get_projects()
            if project_name in projects_data:
                return jsonify({'error': '이미 존재하는 프로젝트명입니다.'}), 400

            dm.create_project(project_name, work_types, contracts, companies)
            return jsonify({'message': f'프로젝트 "{project_name}"이 생성되었습니다.'}), 201

        except Exception as e:
            return jsonify({'error': f'프로젝트 생성 실패: {str(e)}'}), 500

    @app.route('/api/admin/projects/<project_name>', methods=['PUT'])
    @jwt_required()
    def update_project(project_name):
        """프로젝트 업데이트 (관리자 전용)"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            if user['role'] != 'admin':
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

            data = request.get_json()
            work_types = data.get('work_types', [])
            contracts = data.get('contracts', {})
            companies = data.get('companies', {})
            status = data.get('status', 'active')

            projects_data = dm.get_projects()
            if project_name not in projects_data:
                return jsonify({'error': '프로젝트를 찾을 수 없습니다.'}), 404

            dm.update_project(
                project_name,
                work_types=work_types,
                contracts=contracts,
                companies=companies,
                status=status
            )

            return jsonify({'message': f'프로젝트 "{project_name}"이 업데이트되었습니다.'}), 200

        except Exception as e:
            return jsonify({'error': f'프로젝트 업데이트 실패: {str(e)}'}), 500

    @app.route('/api/admin/projects/<project_name>', methods=['DELETE'])
    @jwt_required()
    def delete_project(project_name):
        """프로젝트 삭제 (관리자 전용)"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            if user['role'] != 'admin':
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

            projects_data = dm.get_projects()
            if project_name not in projects_data:
                return jsonify({'error': '프로젝트를 찾을 수 없습니다.'}), 404

            dm.delete_project(project_name)
            return jsonify({'message': f'프로젝트 "{project_name}"이 삭제되었습니다.'}), 200

        except Exception as e:
            return jsonify({'error': f'프로젝트 삭제 실패: {str(e)}'}), 500

    # ===== 사용자 관리 API (관리자) =====
    @app.route('/api/admin/users', methods=['GET'])
    @jwt_required()
    def get_users():
        """사용자 목록 조회 (관리자 전용)"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            if user['role'] != 'admin':
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

            return jsonify({'users': users}), 200

        except Exception as e:
            return jsonify({'error': f'사용자 목록 조회 실패: {str(e)}'}), 500

    @app.route('/api/admin/users', methods=['POST'])
    @jwt_required()
    def create_user():
        """사용자 생성 (관리자 전용)"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            if user['role'] != 'admin':
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

            data = request.get_json()
            new_username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            role = data.get('role', 'user')
            projects = data.get('projects', [])

            if not new_username or not password:
                return jsonify({'error': '사용자명과 비밀번호를 입력해주세요.'}), 400

            # 사용자 중복 확인
            if new_username in users:
                return jsonify({'error': '이미 존재하는 사용자명입니다.'}), 400

            dm.create_user(new_username, password, role, projects)
            return jsonify({'message': f'사용자 "{new_username}"이 생성되었습니다.'}), 201

        except Exception as e:
            return jsonify({'error': f'사용자 생성 실패: {str(e)}'}), 500

    @app.route('/api/admin/users/<target_username>', methods=['PUT'])
    @jwt_required()
    def update_user(target_username):
        """사용자 업데이트 (관리자 전용)"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            if user['role'] != 'admin':
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

            if target_username not in users:
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404

            data = request.get_json()
            new_username = data.get('username', target_username).strip()
            password = data.get('password')
            role = data.get('role')
            projects = data.get('projects')
            status = data.get('status')

            dm.update_user(
                target_username,
                new_username=new_username,
                password=password,
                role=role,
                projects=projects,
                status=status
            )

            return jsonify({'message': f'사용자 "{target_username}"이 업데이트되었습니다.'}), 200

        except Exception as e:
            return jsonify({'error': f'사용자 업데이트 실패: {str(e)}'}), 500

    @app.route('/api/admin/users/<target_username>', methods=['DELETE'])
    @jwt_required()
    def delete_user(target_username):
        """사용자 삭제 (관리자 전용)"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            if user['role'] != 'admin':
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

            if target_username not in users or target_username == 'admin' or target_username == username:
                return jsonify({'error': '삭제할 수 없는 사용자입니다.'}), 400

            dm.delete_user(target_username)
            return jsonify({'message': f'사용자 "{target_username}"이 삭제되었습니다.'}), 200

        except Exception as e:
            return jsonify({'error': f'사용자 삭제 실패: {str(e)}'}), 500

    # ===== 공종 관리 API =====
    @app.route('/api/projects/<project_name>/work-types', methods=['POST'])
    @jwt_required()
    def add_work_type_to_project(project_name):
        """프로젝트에 공종 추가"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            # 권한 확인
            if user['role'] != 'admin' and project_name not in user.get('projects', []):
                return jsonify({'error': '프로젝트 접근 권한이 없습니다.'}), 403

            data = request.get_json()
            work_type = data.get('work_type', '').strip()

            if not work_type:
                return jsonify({'error': '공종명을 입력해주세요.'}), 400

            projects_data = dm.get_projects()
            if project_name not in projects_data:
                return jsonify({'error': '프로젝트를 찾을 수 없습니다.'}), 404

            current_work_types = projects_data[project_name].get('work_types', [])
            
            if work_type in current_work_types:
                return jsonify({'error': '이미 존재하는 공종입니다.'}), 400

            # 공종 추가
            current_work_types.append(work_type)
            dm.update_project(project_name, work_types=current_work_types)

            # 노무단가에 없으면 추가
            labor_costs = dm.get_labor_costs()
            if work_type not in labor_costs:
                dm.save_labor_cost(work_type, 0, 0, 0)

            return jsonify({'message': f'공종 "{work_type}"이 추가되었습니다.'}), 200

        except Exception as e:
            return jsonify({'error': f'공종 추가 실패: {str(e)}'}), 500

    # ===== 리포트 API =====
    @app.route('/api/admin/reports/project-summary', methods=['GET'])
    @jwt_required()
    def get_project_work_summary():
        """프로젝트별 공종 현황 (관리자 전용)"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            if user['role'] != 'admin':
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

            project_name = request.args.get('project')
            if not project_name:
                return jsonify({'error': '프로젝트명을 지정해주세요.'}), 400

            summary = calculate_project_work_summary(project_name)
            return jsonify({'summary': summary}), 200

        except Exception as e:
            return jsonify({'error': f'프로젝트 현황 조회 실패: {str(e)}'}), 500

    # ===== 날짜별 데이터 조회 API =====
    @app.route('/api/projects/<project_name>/dates-with-data', methods=['GET'])
    @jwt_required()
    def get_project_dates_with_data(project_name):
        """프로젝트의 데이터가 있는 날짜들 조회"""
        try:
            username = get_jwt_identity()
            users = dm.get_users()
            user = users.get(username)
            
            # 권한 확인
            if user['role'] != 'admin' and project_name not in user.get('projects', []):
                return jsonify({'error': '프로젝트 접근 권한이 없습니다.'}), 403

            projects_data = dm.get_projects()
            if project_name not in projects_data:
                return jsonify({'error': '프로젝트를 찾을 수 없습니다.'}), 404

            daily_data = projects_data[project_name].get('daily_data', {})
            month = request.args.get('month')  # optional 'YYYY-MM'
            
            if month:
                dates = [d for d in daily_data.keys() if d.startswith(month)]
            else:
                dates = list(daily_data.keys())
            
            dates.sort()
            return jsonify({'dates': dates}), 200

        except Exception as e:
            return jsonify({'error': f'날짜 조회 실패: {str(e)}'}), 500

    # ===== 유틸리티 API =====
    @app.route('/api/available-work-types', methods=['GET'])
    @jwt_required()
    def get_available_work_types():
        """사용 가능한 공종 목록"""
        try:
            labor_costs = dm.get_labor_costs()
            return jsonify({'work_types': list(labor_costs.keys())}), 200

        except Exception as e:
            return jsonify({'error': f'공종 목록 조회 실패: {str(e)}'}), 500

    @app.route('/api/work-type-similarity', methods=['POST'])
    @jwt_required()
    def check_work_type_similarity():
        """공종명 유사성 검사"""
        try:
            data = request.get_json()
            new_type = data.get('work_type', '').strip()
            
            if not new_type:
                return jsonify({'similar_types': [], 'has_similarity': False}), 200

            labor_costs = dm.get_labor_costs()
            existing_types = list(labor_costs.keys())
            similar_types = []
            
            for existing in existing_types:
                if new_type in existing or existing in new_type:
                    if new_type.lower() != existing.lower():
                        similar_types.append(existing)

            return jsonify({
                'similar_types': similar_types,
                'has_similarity': len(similar_types) > 0
            }), 200

        except Exception as e:
            return jsonify({'error': f'유사성 검사 실패: {str(e)}'}), 500