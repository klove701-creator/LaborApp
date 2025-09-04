# admin_routes.py - 관리자 관련 라우트 (PostgreSQL 버전)
from flask import render_template, request, redirect, url_for, session, Response, jsonify
from datetime import date
import csv
import io
from utils import login_required, parse_int, parse_float
from calculations import calculate_dashboard_data, determine_health

def register_admin_routes(app, dm):
    
    @app.route('/admin')
    @login_required(role='admin')
    def admin_dashboard():
        dashboard_data = calculate_dashboard_data()
        return render_template('admin_dashboard.html', dashboard_data=dashboard_data)

    @app.route('/admin/projects')
    @login_required(role='admin')
    def admin_projects():
        # PostgreSQL 방식으로 데이터 조회
        labor_costs = dm.get_labor_costs()
        projects_data = dm.get_projects()
        available_work_types = list(labor_costs.keys())
        
        return render_template('admin_projects.html',
                               projects_data=projects_data,
                               available_work_types=available_work_types,
                               labor_costs=labor_costs)

    @app.route('/admin/projects/create', methods=['POST'])
    @login_required(role='admin')
    def create_project():
        project_name = request.form.get('project_name', '').strip()
        selected_work_types = request.form.getlist('work_types')
        contracts = {}
        companies = {}
        
        for wt in selected_work_types:
            contracts[wt] = parse_int(request.form.get(f'contract_{wt}', ''), 0)
            companies[wt] = request.form.get(f'company_{wt}', '').strip()

        if project_name:
            # 프로젝트 존재 여부 확인
            projects_data = dm.get_projects()
            if project_name not in projects_data:
                dm.create_project(project_name, selected_work_types, contracts, companies)
        
        return redirect(url_for('admin_projects'))

    @app.route('/admin/projects/edit/<project_name>')
    @login_required(role='admin')
    def edit_project(project_name):
        projects_data = dm.get_projects()
        labor_costs = dm.get_labor_costs()
        
        if project_name not in projects_data:
            return redirect(url_for('admin_projects'))
            
        available_work_types = list(labor_costs.keys())
        project_data = projects_data[project_name]
        
        return render_template('admin_project_edit.html',
                               project_name=project_name,
                               project_data=project_data,
                               available_work_types=available_work_types,
                               labor_costs=labor_costs)

    @app.route('/admin/projects/update/<project_name>', methods=['POST'])
    @login_required(role='admin')
    def update_project(project_name):
        projects_data = dm.get_projects()
        if project_name not in projects_data:
            return redirect(url_for('admin_projects'))

        new_name = request.form.get('project_name', '').strip()
        selected_work_types = request.form.getlist('work_types')
        status = request.form.get('status', 'active')

        # 계약금 업데이트
        contracts = {}
        companies = {}
        for wt in selected_work_types:
            contracts[wt] = parse_int(request.form.get(f'contract_{wt}', ''), 0)
            companies[wt] = request.form.get(f'company_{wt}', '').strip()
        
        # 프로젝트 업데이트
        dm.update_project(project_name, 
                         work_types=selected_work_types,
                         contracts=contracts,
                         companies=companies,
                         status=status)
        
        return redirect(url_for('admin_projects'))

    @app.route('/admin/projects/delete/<project_name>')
    @login_required(role='admin')
    def delete_project(project_name):
        projects_data = dm.get_projects()
        if project_name in projects_data:
            dm.delete_project(project_name)
        return redirect(url_for('admin_projects'))

    @app.route('/admin/projects/update-excel/<project_name>', methods=['POST'])
    @login_required(role='admin')
    def update_project_excel(project_name):
        """엑셀 테이블에서 프로젝트 업데이트"""
        projects_data = dm.get_projects()
        if project_name not in projects_data:
            return redirect(url_for('admin_projects'))

        try:
            # 선택된 공종들
            selected_work_types = request.form.getlist('selected_work_types')
            # 업체/계약금
            companies = {}
            contracts = {}
            for work_type in selected_work_types:
                companies[work_type] = (request.form.get(f'company_{work_type}', '') or '').strip()
                contracts[work_type] = parse_int(request.form.get(f'contract_{work_type}', '0'), 0)

            # 프로젝트 데이터 업데이트
            dm.update_project(project_name,
                             work_types=selected_work_types,
                             companies=companies,
                             contracts=contracts)
            
            return redirect(url_for('admin_projects'))
            
        except Exception as e:
            print(f"프로젝트 업데이트 오류: {e}")
            return redirect(url_for('admin_projects'))

    # 사용자 관리
    @app.route('/admin/users')
    @login_required(role='admin')
    def admin_users():
        users = dm.get_users()
        projects_data = dm.get_projects()
        available_projects = list(projects_data.keys())
        
        return render_template('admin_users.html',
                               users=users,
                               available_projects=available_projects)

    @app.route('/admin/users/create', methods=['POST'])
    @login_required(role='admin')
    def create_user():
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'user')
        selected_projects = request.form.getlist('projects')

        if username and password:
            users = dm.get_users()
            if username not in users:
                dm.create_user(username, password, role, 
                              selected_projects if role == 'user' else [])
        
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/edit/<username>')
    @login_required(role='admin')
    def edit_user(username):
        users = dm.get_users()
        projects_data = dm.get_projects()
        
        if username not in users or username == 'admin':
            return redirect(url_for('admin_users'))
            
        available_projects = list(projects_data.keys())
        user_data = users[username]
        
        return render_template('admin_user_edit.html',
                               username=username,
                               user_data=user_data,
                               available_projects=available_projects)

    @app.route('/admin/users/update/<username>', methods=['POST'])
    @login_required(role='admin')
    def update_user(username):
        users = dm.get_users()
        if username not in users or username == 'admin':
            return redirect(url_for('admin_users'))

        new_username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'user')
        selected_projects = request.form.getlist('projects')
        status = request.form.get('status', 'active')

        # 사용자 업데이트
        dm.update_user(username, new_username, password, role, 
                      selected_projects if role == 'user' else [], status)
        
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/delete/<username>')
    @login_required(role='admin')
    def delete_user(username):
        users = dm.get_users()
        if username in users and username != 'admin' and username != session['username']:
            dm.delete_user(username)
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/toggle-status/<username>')
    @login_required(role='admin')
    def toggle_user_status(username):
        users = dm.get_users()
        if username in users and username != 'admin':
            current_status = users[username].get('status', 'active')
            new_status = 'inactive' if current_status == 'active' else 'active'
            dm.update_user(username, status=new_status)
        return redirect(url_for('admin_users'))

    # 노무단가 관리
    @app.route('/admin/labor-cost')
    @login_required(role='admin')
    def admin_labor_cost():
        labor_costs = dm.get_labor_costs()
        work_types = list(labor_costs.keys())
        
        return render_template('admin_labor_cost.html',
                               labor_costs=labor_costs,
                               work_types=sorted(work_types))

    @app.route('/admin/labor-cost/save', methods=['POST'])
    @login_required(role='admin')
    def save_labor_cost():
        labor_costs = dm.get_labor_costs()
        
        # 기존 공종 업데이트
        for work_type in labor_costs.keys():
            day_cost = request.form.get(f'{work_type}_day', '')
            night_cost = request.form.get(f'{work_type}_night', '')
            midnight_cost = request.form.get(f'{work_type}_midnight', '')
            
            try:
                if day_cost and night_cost and midnight_cost:
                    dm.save_labor_cost(work_type,
                                      parse_int(day_cost, 0),
                                      parse_int(night_cost, 0),
                                      parse_int(midnight_cost, 0))
            except (ValueError, AttributeError):
                continue

        # 새 공종 추가
        new_work_type = (request.form.get('new_work_type', '') or '').strip()
        new_day = request.form.get('new_day', '')
        new_night = request.form.get('new_night', '')
        new_midnight = request.form.get('new_midnight', '')

        if new_work_type and new_day and new_night and new_midnight:
            try:
                if new_work_type not in labor_costs:
                    dm.save_labor_cost(new_work_type,
                                      parse_int(new_day, 0),
                                      parse_int(new_night, 0),
                                      parse_int(new_midnight, 0))
            except (ValueError, AttributeError):
                pass
        
        return redirect(url_for('admin_labor_cost'))

    @app.route('/admin/labor-cost/update-single', methods=['POST'])
    @login_required(role='admin')
    def update_single_work_type():
        """개별 공종 노무비 업데이트"""
        try:
            labor_costs = dm.get_labor_costs()
            
            # 폼에서 공종별 데이터 찾기
            updated_work_type = None
            for work_type in labor_costs.keys():
                day_key = f'{work_type}_day'
                night_key = f'{work_type}_night'
                midnight_key = f'{work_type}_midnight'
                
                if day_key in request.form:
                    day_cost = parse_int(request.form.get(day_key, '0'), 0)
                    night_cost = parse_int(request.form.get(night_key, '0'), 0)
                    midnight_cost = parse_int(request.form.get(midnight_key, '0'), 0)
                    
                    # 값이 유효하면 업데이트
                    if day_cost >= 0 and night_cost >= 0 and midnight_cost >= 0:
                        dm.save_labor_cost(work_type, day_cost, night_cost, midnight_cost)
                        updated_work_type = work_type
                        break
            
            if updated_work_type:
                return jsonify({
                    'success': True,
                    'message': f'"{updated_work_type}" 공종 노무비가 업데이트되었습니다.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '업데이트할 공종을 찾을 수 없습니다.'
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'업데이트 중 오류가 발생했습니다: {str(e)}'
            })

    @app.route('/admin/labor-cost/delete/<work_type>')
    @login_required(role='admin')
    def delete_work_type_route(work_type):
        """공종 삭제"""
        labor_costs = dm.get_labor_costs()
        projects_data = dm.get_projects()
        
        if work_type in labor_costs:
            # 해당 공종을 사용하는 프로젝트가 있는지 확인
            projects_using = []
            for proj_name, proj_data in projects_data.items():
                if work_type in proj_data.get('work_types', []):
                    projects_using.append(proj_name)
            
            if projects_using:
                # 프로젝트에서 사용 중이면 삭제하지 않음
                error_msg = f'공종 "{work_type}"은(는) 다음 프로젝트에서 사용 중입니다: {", ".join(projects_using)}'
                return redirect(url_for('admin_labor_cost') + f'?error={error_msg}')
            
            # 사용하지 않으면 삭제
            dm.delete_labor_cost(work_type)
        
        return redirect(url_for('admin_labor_cost'))

    @app.route('/admin/labor-cost/toggle-lock/<work_type>')
    @login_required(role='admin')
    def toggle_lock_work_type_route(work_type):
        """공종 잠금 토글"""
        labor_costs = dm.get_labor_costs()
        if work_type in labor_costs:
            current_lock = labor_costs[work_type].get('locked', False)
            # PostgreSQL에는 별도의 lock 테이블이나 컬럼이 필요 - 일단 단순화
            print(f"공종 잠금 토글: {work_type} - {not current_lock}")
        
        return redirect(url_for('admin_labor_cost'))

    # 설정 관리
    @app.route('/admin/settings')
    @login_required(role='admin')
    def admin_settings():
        # HEALTH_POLICY에서 현재 설정값 가져오기
        from utils import HEALTH_POLICY
        settings = {
            'theme': 'dark',
            'risk_thresholds': {
                'cost_warn_ratio': int(HEALTH_POLICY['COST_WARN_RATIO'] * 100),
                'cost_danger_ratio': int(HEALTH_POLICY['COST_DANGER_RATIO'] * 100),
                'progress_warn_diff': int(HEALTH_POLICY['PROGRESS_WARN_DIFF'] * 100),
                'progress_danger_diff': int(HEALTH_POLICY['PROGRESS_DANGER_DIFF'] * 100),
                'workers_warn_drop': int(abs(HEALTH_POLICY['WORKERS_WARN_DROP']) * 100),
                'workers_danger_drop': int(abs(HEALTH_POLICY['WORKERS_DANGER_DROP']) * 100),
                'workers_warn_surge': int(HEALTH_POLICY['WORKERS_WARN_SURGE'] * 100),
                'workers_danger_surge': int(HEALTH_POLICY['WORKERS_DANGER_SURGE'] * 100),
            },
            'notifications': {
                'email_alerts': False,
                'dashboard_alerts': True,
            }
        }
        
        return render_template('admin_settings.html', settings=settings)

    @app.route('/admin/settings/save', methods=['POST'])
    @login_required(role='admin')
    def save_settings():
        # 설정 데이터 수집
        settings = {
            'theme': request.form.get('theme', 'dark'),
            'risk_thresholds': {
                'cost_warn_ratio': parse_int(request.form.get('cost_warn_ratio', '80'), 80),
                'cost_danger_ratio': parse_int(request.form.get('cost_danger_ratio', '100'), 100),
                'progress_warn_diff': parse_int(request.form.get('progress_warn_diff', '5'), 5),
                'progress_danger_diff': parse_int(request.form.get('progress_danger_diff', '10'), 10),
                'workers_warn_drop': parse_int(request.form.get('workers_warn_drop', '40'), 40),
                'workers_danger_drop': parse_int(request.form.get('workers_danger_drop', '60'), 60),
                'workers_warn_surge': parse_int(request.form.get('workers_warn_surge', '40'), 40),
                'workers_danger_surge': parse_int(request.form.get('workers_danger_surge', '60'), 60),
            },
            'notifications': {
                'email_alerts': 'email_alerts' in request.form,
                'dashboard_alerts': 'dashboard_alerts' in request.form,
            }
        }
        
        # utils.py의 HEALTH_POLICY 업데이트
        from utils import HEALTH_POLICY
        HEALTH_POLICY.update({
            'COST_WARN_RATIO': settings['risk_thresholds']['cost_warn_ratio'] / 100.0,
            'COST_DANGER_RATIO': settings['risk_thresholds']['cost_danger_ratio'] / 100.0,
            'PROGRESS_WARN_DIFF': settings['risk_thresholds']['progress_warn_diff'] / 100.0,
            'PROGRESS_DANGER_DIFF': settings['risk_thresholds']['progress_danger_diff'] / 100.0,
            'WORKERS_WARN_DROP': -settings['risk_thresholds']['workers_warn_drop'] / 100.0,
            'WORKERS_DANGER_DROP': -settings['risk_thresholds']['workers_danger_drop'] / 100.0,
            'WORKERS_WARN_SURGE': settings['risk_thresholds']['workers_warn_surge'] / 100.0,
            'WORKERS_DANGER_SURGE': settings['risk_thresholds']['workers_danger_surge'] / 100.0,
        })
        
        try:
            # PostgreSQL에 설정 저장 로직 필요 (나중에 구현)
            print("설정이 업데이트되었습니다.")
            
            # 성공 메시지와 함께 리다이렉트
            return render_template('admin_settings.html', 
                                 settings={**settings, 'theme': request.form.get('theme', 'dark')},
                                 success_msg="위험도 알고리즘 설정이 성공적으로 저장되었습니다.")
        except Exception as e:
            # 오류 메시지와 함께 리다이렉트
            return render_template('admin_settings.html', 
                                 settings={**settings, 'theme': request.form.get('theme', 'dark')},
                                 error_msg=f"설정 저장 중 오류가 발생했습니다: {str(e)}")

    # 리포트
    @app.route('/admin/reports')
    @login_required(role='admin')
    def admin_reports():
        # PostgreSQL 방식으로 데이터 조회
        projects_data = dm.get_projects()
        users = dm.get_users()
        labor_costs = dm.get_labor_costs()
        
        # 간단한 리포트 데이터 계산
        reports_data = {
            'total_projects': len(projects_data),
            'total_users': len([u for u in users.values() if u.get('role') == 'user']),
            'total_work_types': len(labor_costs),
            'projects_summary': [],
            'total_cost': 0,
            'total_workers': 0
        }
        
        # 프로젝트별 요약
        for project_name, project_data in projects_data.items():
            work_types = project_data.get('work_types', [])
            daily_data = project_data.get('daily_data', {})
            
            total_workers = 0
            total_cost = 0
            total_days = len(daily_data)
            
            # 총 인원 및 비용 계산
            for date_data in daily_data.values():
                for work_type, work_data in date_data.items():
                    workers = work_data.get('total', 0)
                    total_workers += workers
                    
                    if work_type in labor_costs:
                        day_cost = work_data.get('day', 0) * labor_costs[work_type].get('day', 0)
                        night_cost = work_data.get('night', 0) * labor_costs[work_type].get('night', 0)
                        midnight_cost = work_data.get('midnight', 0) * labor_costs[work_type].get('midnight', 0)
                        total_cost += day_cost + night_cost + midnight_cost

            # 상태 산정
            p_status, _, p_meta = determine_health(project_data, labor_costs)

            reports_data['projects_summary'].append({
                'name': project_name,
                'work_types_count': len(work_types),
                'total_workers': total_workers,
                'total_cost': total_cost,
                'working_days': total_days,
                'avg_progress': round(p_meta.get('avg_progress', 0.0), 1),
                'status': p_status
            })
            
            reports_data['total_cost'] += total_cost
            reports_data['total_workers'] += total_workers
        
        return render_template('admin_reports.html',
                               reports_data=reports_data,
                               projects_data=projects_data)

    @app.route('/admin/reports/export/csv')
    @login_required(role='admin')
    def export_csv():
        projects_data = dm.get_projects()
        
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow(['프로젝트', '날짜', '공종', '주간', '야간', '심야', '계', '공정율'])

        for project_name, project_data in projects_data.items():
            daily_data = project_data.get('daily_data', {})
            for date_key, date_data in daily_data.items():
                for work_type, work_data in date_data.items():
                    writer.writerow([
                        project_name, date_key, work_type,
                        parse_int(work_data.get('day', 0), 0),
                        parse_int(work_data.get('night', 0), 0),
                        parse_int(work_data.get('midnight', 0), 0),
                        parse_int(work_data.get('total', 0), 0),
                        parse_float(work_data.get('progress', 0), 0.0)
                    ])

        csv_text = '\ufeff' + output.getvalue()  # BOM 추가(엑셀 한글 안전)
        return Response(
            csv_text,
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': 'attachment; filename=labor_data.csv'}
        )