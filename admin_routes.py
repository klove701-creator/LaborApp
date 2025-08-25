# admin_routes.py - 관리자 전용 라우트
from flask import Blueprint, render_template, request, redirect, url_for, session, Response
from datetime import date
from utils import calculate_dashboard_data, calculate_reports_data
import csv
import io

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_data_manager():
    """데이터 매니저 인스턴스 가져오기"""
    from app import dm
    return dm

def admin_required(f):
    """관리자 권한 확인 데코레이터"""
    def wrapper(*args, **kwargs):
        if 'username' not in session or session['role'] != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ===== 대시보드 =====
@admin_bp.route('/')
@admin_required
def dashboard():
    dm = get_data_manager()
    dashboard_data = calculate_dashboard_data(dm.projects_data, dm.labor_costs)
    return render_template('admin_dashboard.html', dashboard_data=dashboard_data)

# ===== 프로젝트 관리 =====
@admin_bp.route('/projects')
@admin_required
def projects():
    dm = get_data_manager()
    available_work_types = list(dm.labor_costs.keys())
    return render_template('admin_projects.html',
                           projects_data=dm.projects_data,
                           available_work_types=available_work_types)

@admin_bp.route('/projects/create', methods=['POST'])
@admin_required
def create_project():
    dm = get_data_manager()
    project_name = request.form.get('project_name', '').strip()
    selected_work_types = request.form.getlist('work_types')
    
    contracts = {}
    for wt in selected_work_types:
        raw = (request.form.get(f'contract_{wt}', '') or '').replace(',', '').strip()
        contracts[wt] = int(float(raw)) if raw else 0

    if project_name:
        dm.add_project(project_name, selected_work_types, contracts)

    return redirect(url_for('admin.projects'))

@admin_bp.route('/projects/edit/<project_name>')
@admin_required
def edit_project(project_name):
    dm = get_data_manager()
    if project_name not in dm.projects_data:
        return redirect(url_for('admin.projects'))

    available_work_types = list(dm.labor_costs.keys())
    project_data = dm.projects_data[project_name]

    return render_template('admin_project_edit.html',
                           project_name=project_name,
                           project_data=project_data,
                           available_work_types=available_work_types)

@admin_bp.route('/projects/update/<project_name>', methods=['POST'])
@admin_required
def update_project(project_name):
    dm = get_data_manager()
    if project_name not in dm.projects_data:
        return redirect(url_for('admin.projects'))

    old_name = project_name
    new_name = request.form.get('project_name', '').strip()
    selected_work_types = request.form.getlist('work_types')
    status = request.form.get('status', 'active')

    # 프로젝트명 변경
    if new_name and new_name != old_name and new_name not in dm.projects_data:
        dm.projects_data[new_name] = dm.projects_data.pop(old_name)
        
        # 사용자 프로젝트 목록 업데이트
        for user_data in dm.users.values():
            if 'projects' in user_data and old_name in user_data['projects']:
                user_data['projects'].remove(old_name)
                user_data['projects'].append(new_name)
        project_name = new_name

    # 계약금 업데이트
    contracts = {}
    for wt in selected_work_types:
        raw = (request.form.get(f'contract_{wt}', '') or '').replace(',', '').strip()
        contracts[wt] = int(float(raw)) if raw else 0
    
    dm.projects_data[project_name]['work_types'] = selected_work_types
    dm.projects_data[project_name]['contracts'] = contracts
    dm.projects_data[project_name]['status'] = status
    
    dm.save_data()
    return redirect(url_for('admin.projects'))

@admin_bp.route('/projects/delete/<project_name>')
@admin_required
def delete_project(project_name):
    dm = get_data_manager()
    dm.delete_project(project_name)
    return redirect(url_for('admin.projects'))

# ===== 사용자 관리 =====
@admin_bp.route('/users')
@admin_required
def users():
    dm = get_data_manager()
    available_projects = list(dm.projects_data.keys())
    return render_template('admin_users.html',
                           users=dm.users,
                           available_projects=available_projects)

@admin_bp.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    dm = get_data_manager()
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
        
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/edit/<username>')
@admin_required
def edit_user(username):
    dm = get_data_manager()
    if username not in dm.users or username == 'admin':
        return redirect(url_for('admin.users'))

    available_projects = list(dm.projects_data.keys())
    user_data = dm.users[username]

    return render_template('admin_user_edit.html',
                           username=username,
                           user_data=user_data,
                           available_projects=available_projects)

@admin_bp.route('/users/update/<username>', methods=['POST'])
@admin_required
def update_user(username):
    dm = get_data_manager()
    if username not in dm.users or username == 'admin':
        return redirect(url_for('admin.users'))

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
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/delete/<username>')
@admin_required
def delete_user(username):
    dm = get_data_manager()
    if username in dm.users and username != 'admin' and username != session['username']:
        del dm.users[username]
        dm.save_data()
    return redirect(url_for('admin.users'))

# ===== 노무단가 관리 =====
@admin_bp.route('/labor-cost')
@admin_required
def labor_cost():
    dm = get_data_manager()
    work_types = list(dm.labor_costs.keys())
    return render_template('admin_labor_cost.html',
                           labor_costs=dm.labor_costs,
                           work_types=sorted(work_types))

@admin_bp.route('/labor-cost/save', methods=['POST'])
@admin_required
def save_labor_cost():
    dm = get_data_manager()

    # 기존 공종 업데이트
    for work_type in list(dm.labor_costs.keys()):
        if dm.labor_costs[work_type].get('locked', False):
            continue

        day_cost = request.form.get(f'{work_type}_day', '').strip()
        night_cost = request.form.get(f'{work_type}_night', '').strip()
        midnight_cost = request.form.get(f'{work_type}_midnight', '').strip()

        try:
            if day_cost and night_cost and midnight_cost:
                dm.labor_costs[work_type].update({
                    'day': int(day_cost.replace(',', '')),
                    'night': int(night_cost.replace(',', '')),
                    'midnight': int(midnight_cost.replace(',', ''))
                })
        except (ValueError, AttributeError):
            continue

    # 새 공종 추가
    new_work_type = request.form.get('new_work_type', '').strip()
    new_day = request.form.get('new_day', '').strip()
    new_night = request.form.get('new_night', '').strip()
    new_midnight = request.form.get('new_midnight', '').strip()

    if new_work_type and new_day and new_night and new_midnight:
        try:
            if new_work_type not in dm.labor_costs:
                dm.labor_costs[new_work_type] = {
                    'day': int(new_day.replace(',', '')),
                    'night': int(new_night.replace(',', '')),
                    'midnight': int(new_midnight.replace(',', '')),
                    'locked': False
                }
        except (ValueError, AttributeError):
            pass
    
    dm.save_data()
    return redirect(url_for('admin.labor_cost'))

# ===== 리포트 =====
@admin_bp.route('/reports')
@admin_required
def reports():
    dm = get_data_manager()
    reports_data = calculate_reports_data(dm.projects_data, dm.labor_costs, dm.users)
    return render_template('admin_reports.html',
                           reports_data=reports_data,
                           projects_data=dm.projects_data)

@admin_bp.route('/reports/export/csv')
@admin_required
def export_csv():
    dm = get_data_manager()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['프로젝트', '날짜', '공종', '주간', '야간', '심야', '계', '공정율'])

    for project_name, project_data in dm.projects_data.items():
        daily_data = project_data.get('daily_data', {})
        for date_key, date_data in daily_data.items():
            for work_type, work_data in date_data.items():
                writer.writerow([
                    project_name, date_key, work_type,
                    work_data.get('day', 0), work_data.get('night', 0),
                    work_data.get('midnight', 0), work_data.get('total', 0),
                    work_data.get('progress', 0)
                ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=labor_data.csv'}
    )