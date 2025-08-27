# admin_routes.py - 관리자 관련 라우트
from flask import render_template, request, redirect, url_for, session, Response
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
        available_work_types = list(dm.labor_costs.keys())
        return render_template('admin_projects.html',
                               projects_data=dm.projects_data,
                               available_work_types=available_work_types,
                               labor_costs=dm.labor_costs)

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

        if project_name and project_name not in dm.projects_data:
            dm.projects_data[project_name] = {
                'work_types': selected_work_types,
                'contracts': contracts,
                'companies': companies,
                'daily_data': {},
                'status': 'active',
                'created_date': date.today().strftime('%Y-%m-%d')
            }
            dm.save_data()
        return redirect(url_for('admin_projects'))

    @app.route('/admin/projects/edit/<project_name>')
    @login_required(role='admin')
    def edit_project(project_name):
        if project_name not in dm.projects_data:
            return redirect(url_for('admin_projects'))
        available_work_types = list(dm.labor_costs.keys())
        project_data = dm.projects_data[project_name]
        return render_template('admin_project_edit.html',
                               project_name=project_name,
                               project_data=project_data,
                               available_work_types=available_work_types,
                               labor_costs=dm.labor_costs)

    @app.route('/admin/projects/update/<project_name>', methods=['POST'])
    @login_required(role='admin')
    def update_project(project_name):
        if project_name not in dm.projects_data:
            return redirect(url_for('admin_projects'))

        old_name = project_name
        new_name = request.form.get('project_name', '').strip()
        selected_work_types = request.form.getlist('work_types')
        status = request.form.get('status', 'active')

        # 프로젝트명 변경
        if new_name and new_name != old_name and new_name not in dm.projects_data:
            dm.projects_data[new_name] = dm.projects_data.pop(old_name)
            for user_data in dm.users.values():
                if 'projects' in user_data and old_name in user_data['projects']:
                    user_data['projects'].remove(old_name)
                    user_data['projects'].append(new_name)
            project_name = new_name

        # 계약금 업데이트
        contracts = {}
        for wt in selected_work_types:
            contracts[wt] = parse_int(request.form.get(f'contract_{wt}', ''), 0)
        
        dm.projects_data[project_name]['work_types'] = selected_work_types
        dm.projects_data[project_name]['contracts'] = contracts
        dm.projects_data[project_name]['status'] = status
        
        dm.save_data()
        return redirect(url_for('admin_projects'))

    @app.route('/admin/projects/delete/<project_name>')
    @login_required(role='admin')
    def delete_project(project_name):
        if project_name in dm.projects_data:
            del dm.projects_data[project_name]
            for user_data in dm.users.values():
                if 'projects' in user_data and project_name in user_data['projects']:
                    user_data['projects'].remove(project_name)
            dm.save_data()
        return redirect(url_for('admin_projects'))

    @app.route('/admin/projects/update-excel/<project_name>', methods=['POST'])
    @login_required(role='admin')
    def update_project_excel(project_name):
        """엑셀 테이블에서 프로젝트 업데이트"""
        if project_name not in dm.projects_data:
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
            dm.projects_data[project_name]['work_types'] = selected_work_types
            dm.projects_data[project_name]['companies'] = companies
            dm.projects_data[project_name]['contracts'] = contracts
            
            # daily_data에서 삭제된 공종 제거
            daily_data = dm.projects_data[project_name].get('daily_data', {})
            for date_key, date_data in daily_data.items():
                for wt in list(date_data.keys()):
                    if wt not in selected_work_types:
                        del date_data[wt]
            dm.save_data()
            return redirect(url_for('admin_projects'))
            
        except Exception as e:
            print(f"프로젝트 업데이트 오류: {e}")
            return redirect(url_for('admin_projects'))

    # 사용자 관리
    @app.route('/admin/users')
    @login_required(role='admin')
    def admin_users():
        available_projects = list(dm.projects_data.keys())
        return render_template('admin_users.html',
                               users=dm.users,
                               available_projects=available_projects)

    @app.route('/admin/users/create', methods=['POST'])
    @login_required(role='admin')
    def create_user():
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'user')
        selected_projects = request.form.getlist('projects')

        if username and password and username not in dm.users:
            dm.users[username] = {
                'password': password,
                'role': role,
                'projects': selected_projects if role == 'user' else [],
                'created_date': date.today().strftime('%Y-%m-%d'),
                'status': 'active'
            }
            dm.save_data()
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/edit/<username>')
    @login_required(role='admin')
    def edit_user(username):
        if username not in dm.users or username == 'admin':
            return redirect(url_for('admin_users'))
        available_projects = list(dm.projects_data.keys())
        user_data = dm.users[username]
        return render_template('admin_user_edit.html',
                               username=username,
                               user_data=user_data,
                               available_projects=available_projects)

    @app.route('/admin/users/update/<username>', methods=['POST'])
    @login_required(role='admin')
    def update_user(username):
        if username not in dm.users or username == 'admin':
            return redirect(url_for('admin_users'))

        new_username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'user')
        selected_projects = request.form.getlist('projects')
        status = request.form.get('status', 'active')

        # 사용자명 변경
        if new_username and new_username != username and new_username not in dm.users:
            dm.users[new_username] = dm.users.pop(username)
            username = new_username

        # 데이터 업데이트
        if password:
            dm.users[username]['password'] = password
        dm.users[username]['role'] = role
        dm.users[username]['projects'] = selected_projects if role == 'user' else []
        dm.users[username]['status'] = status

        dm.save_data()
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/delete/<username>')
    @login_required(role='admin')
    def delete_user(username):
        if username in dm.users and username != 'admin' and username != session['username']:
            del dm.users[username]
            dm.save_data()
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/toggle-status/<username>')
    @login_required(role='admin')
    def toggle_user_status(username):
        if username in dm.users and username != 'admin':
            current_status = dm.users[username].get('status', 'active')
            dm.users[username]['status'] = 'inactive' if current_status == 'active' else 'active'
            dm.save_data()
        return redirect(url_for('admin_users'))

    # 노무단가 관리
    @app.route('/admin/labor-cost')
    @login_required(role='admin')
    def admin_labor_cost():
        work_types = list(dm.labor_costs.keys())
        return render_template('admin_labor_cost.html',
                               labor_costs=dm.labor_costs,
                               work_types=sorted(work_types))

    @app.route('/admin/labor-cost/save', methods=['POST'])
    @login_required(role='admin')
    def save_labor_cost():
        # 기존 공종 업데이트
        for work_type in list(dm.labor_costs.keys()):
            day_cost = request.form.get(f'{work_type}_day', '')
            night_cost = request.form.get(f'{work_type}_night', '')
            midnight_cost = request.form.get(f'{work_type}_midnight', '')
            try:
                if day_cost and night_cost and midnight_cost:
                    dm.labor_costs[work_type].update({
                        'day': parse_int(day_cost, 0),
                        'night': parse_int(night_cost, 0),
                        'midnight': parse_int(midnight_cost, 0)
                    })
            except (ValueError, AttributeError):
                continue

        # 새 공종 추가
        new_work_type = (request.form.get('new_work_type', '') or '').strip()
        new_day = request.form.get('new_day', '')
        new_night = request.form.get('new_night', '')
        new_midnight = request.form.get('new_midnight', '')

        if new_work_type and new_day and new_night and new_midnight:
            try:
                if new_work_type not in dm.labor_costs:
                    dm.labor_costs[new_work_type] = {
                        'day': parse_int(new_day, 0),
                        'night': parse_int(night_cost, 0),
                        'midnight': parse_int(new_midnight, 0),
                        'locked': False
                    }
            except (ValueError, AttributeError):
                pass
        
        dm.save_data()
        return redirect(url_for('admin_labor_cost'))

    @app.route('/admin/labor-cost/delete/<work_type>')
    @login_required(role='admin')
    def delete_work_type_route(work_type):
        """공종 삭제"""
        if work_type in dm.labor_costs:
            # 해당 공종을 사용하는 프로젝트가 있는지 확인
            projects_using = []
            for proj_name, proj_data in dm.projects_data.items():
                if work_type in proj_data.get('work_types', []):
                    projects_using.append(proj_name)
            
            if projects_using:
                # 프로젝트에서 사용 중이면 삭제하지 않음
                error_msg = f'공종 "{work_type}"은(는) 다음 프로젝트에서 사용 중입니다: {", ".join(projects_using)}'
                return redirect(url_for('admin_labor_cost') + f'?error={error_msg}')
            
            # 사용하지 않으면 삭제
            del dm.labor_costs[work_type]
            dm.save_data()
        
        return redirect(url_for('admin_labor_cost'))

    @app.route('/admin/labor-cost/toggle-lock/<work_type>')
    @login_required(role='admin')
    def toggle_lock_work_type_route(work_type):
        """공종 잠금 토글"""
        if work_type in dm.labor_costs:
            current_lock = dm.labor_costs[work_type].get('locked', False)
            dm.labor_costs[work_type]['locked'] = not current_lock
            dm.save_data()
        
        return redirect(url_for('admin_labor_cost'))

    # 설정 관리
    @app.route('/admin/settings')
    @login_required(role='admin')
    def admin_settings():
        # 현재 설정 로드 (기본값 포함)
        settings = dm.projects_data.get('_system_settings', {})
        
        # 기본 설정값
        default_settings = {
            'theme': 'dark',  # dark, light
            'risk_thresholds': {
                'cost_overrun_warn': 5,      # 5%
                'cost_overrun_danger': 12,   # 12%
                'progress_warn_min': 50,     # 50%
                'progress_danger_min': 20,   # 20%
                'workers_warn_drop': 40,     # 40%
                'workers_danger_drop': 60,   # 60%
                'workers_warn_surge': 40,    # 40%
                'workers_danger_surge': 60,  # 60%
            },
            'notifications': {
                'email_alerts': False,
                'dashboard_alerts': True,
            }
        }
        
        # 기본값과 병합
        for key, value in default_settings.items():
            if key not in settings:
                settings[key] = value
        
        return render_template('admin_settings.html', settings=settings)

    @app.route('/admin/settings/save', methods=['POST'])
    @login_required(role='admin')
    def save_settings():
        # 설정 데이터 수집
        settings = {
            'theme': request.form.get('theme', 'dark'),
            'risk_thresholds': {
                'cost_overrun_warn': parse_int(request.form.get('cost_overrun_warn', '5'), 5),
                'cost_overrun_danger': parse_int(request.form.get('cost_overrun_danger', '12'), 12),
                'progress_warn_min': parse_int(request.form.get('progress_warn_min', '50'), 50),
                'progress_danger_min': parse_int(request.form.get('progress_danger_min', '20'), 20),
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
        
        # 시스템 설정을 projects_data에 저장
        dm.projects_data['_system_settings'] = settings
        
        # utils.py의 HEALTH_POLICY 업데이트
        from utils import HEALTH_POLICY
        HEALTH_POLICY.update({
            'COST_OVERRUN_WARN': settings['risk_thresholds']['cost_overrun_warn'] / 100.0,
            'COST_OVERRUN_DANGER': settings['risk_thresholds']['cost_overrun_danger'] / 100.0,
            'PROGRESS_WARN_MIN': settings['risk_thresholds']['progress_warn_min'] / 100.0,
            'PROGRESS_DANGER_MIN': settings['risk_thresholds']['progress_danger_min'] / 100.0,
            'WORKERS_WARN_DROP': -settings['risk_thresholds']['workers_warn_drop'] / 100.0,
            'WORKERS_DANGER_DROP': -settings['risk_thresholds']['workers_danger_drop'] / 100.0,
            'WORKERS_WARN_SURGE': settings['risk_thresholds']['workers_warn_surge'] / 100.0,
            'WORKERS_DANGER_SURGE': settings['risk_thresholds']['workers_danger_surge'] / 100.0,
        })
        
        dm.save_data()
        return redirect(url_for('admin_settings'))

    @app.route('/admin/labor-cost/delete/<work_type>')
    @login_required(role='admin')
    def delete_labor_cost(work_type):
        """공종 삭제"""
        if work_type in dm.labor_costs:
            # 해당 공종을 사용하는 프로젝트가 있는지 확인
            projects_using = []
            for proj_name, proj_data in dm.projects_data.items():
                if work_type in proj_data.get('work_types', []):
                    projects_using.append(proj_name)
            
            if projects_using:
                # 프로젝트에서 사용 중이면 삭제하지 않음
                return redirect(url_for('admin_labor_cost') + f'?error=공종 "{work_type}"은(는) 다음 프로젝트에서 사용 중입니다: {", ".join(projects_using)}')
            
            # 사용하지 않으면 삭제
            del dm.labor_costs[work_type]
            dm.save_data()
        
        return redirect(url_for('admin_labor_cost'))

    # 리포트
    @app.route('/admin/reports')
    @login_required(role='admin')
    def admin_reports():
        # 간단한 리포트 데이터 계산
        reports_data = {
            'total_projects': len(dm.projects_data),
            'total_users': len([u for u in dm.users.values() if u.get('role') == 'user']),
            'total_work_types': len(dm.labor_costs),
            'projects_summary': [],
            'total_cost': 0,
            'total_workers': 0
        }
        
        # 프로젝트별 요약
        for project_name, project_data in dm.projects_data.items():
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
                    
                    if work_type in dm.labor_costs:
                        day_cost = work_data.get('day', 0) * dm.labor_costs[work_type].get('day', 0)
                        night_cost = work_data.get('night', 0) * dm.labor_costs[work_type].get('night', 0)
                        midnight_cost = work_data.get('midnight', 0) * dm.labor_costs[work_type].get('midnight', 0)
                        total_cost += day_cost + night_cost + midnight_cost

            # 상태 산정(보고서에도 동일 기준 적용)
            p_status, _, p_meta = determine_health(project_data)

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
                               projects_data=dm.projects_data)

    @app.route('/admin/reports/export/csv')
    @login_required(role='admin')
    def export_csv():
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow(['프로젝트', '날짜', '공종', '주간', '야간', '심야', '계', '공정율'])

        for project_name, project_data in dm.projects_data.items():
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