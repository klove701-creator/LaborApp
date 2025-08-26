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
                        'night': parse_int(new_night, 0),
                        'midnight': parse_int(new_midnight, 0),
                        'locked': False
                    }
            except (ValueError, AttributeError):
                pass
        
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