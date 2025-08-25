from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from datetime import datetime, date, timedelta
import json
import os
import csv
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['JSON_AS_ASCII'] = False

# ===== 데이터 저장/로드 시스템 =====
DATA_FILE = 'app_data.json'

class DataManager:
    def __init__(self):
        self.users = {}
        self.projects_data = {}
        self.labor_costs = {}
        self.load_data()
    
    def load_data(self):
        """JSON 파일에서 데이터 로드"""
        print(f"🔍 JSON 파일 존재 여부: {os.path.exists(DATA_FILE)}")
        
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.projects_data = data.get('projects_data', {})
                    self.labor_costs = data.get('labor_costs', {})
                    print(f"✅ 데이터 로드 완료! 프로젝트 수: {len(self.projects_data)}")
                    return
            except Exception as e:
                print(f"❌ 데이터 로드 실패: {e}")
        
        print("📄 새 데이터 생성")
        self._create_default_data()
        self.save_data()
    
    def _create_default_data(self):
        """기본 데이터 생성"""
        self.users = {
            'admin': {'password': '1234', 'role': 'admin'},
            'user1': {'password': '1234', 'role': 'user', 'projects': ['현대카드 인테리어공사']}
        }
        
        self.projects_data = {
            '현대카드 인테리어공사': {
                'work_types': ['도장공사', '목공사', '타일'],
                'daily_data': {},
                'status': 'active',
                'created_date': '2025-08-24',
                'contracts': {
                    '도장공사': 200000,
                    '목공사': 250000,
                    '타일': 300000
                }
            }
        }
        
        self.labor_costs = {
            '도장공사': {'day': 120000, 'night': 150000, 'midnight': 180000},
            '목공사': {'day': 130000, 'night': 160000, 'midnight': 190000},
            '타일': {'day': 140000, 'night': 170000, 'midnight': 200000}
        }
    
    def save_data(self):
        """모든 데이터를 JSON 파일에 저장"""
        try:
            data = {
                'users': self.users,
                'projects_data': self.projects_data,
                'labor_costs': self.labor_costs,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 데이터 저장 완료!")
            return True
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {e}")
            return False

# 데이터 매니저 초기화
dm = DataManager()

@app.template_filter('format_currency')
def format_currency(value):
    """숫자를 천 단위 콤마가 포함된 문자열로 변환"""
    if value is None:
        return "0"
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return str(value)

def calculate_dashboard_data():
    """관리자 대시보드용 데이터 계산"""
    dashboard = []
    for project_name, project_data in dm.projects_data.items():
        work_types = project_data.get('work_types', [])
        daily_data = project_data.get('daily_data', {})
        recent_date = max(daily_data.keys()) if daily_data else None
        
        total_workers_today = 0
        work_count = len(work_types)
        avg_progress = 30.0  # 임시값
        
        if recent_date:
            for work_type in work_types:
                if work_type in daily_data.get(recent_date, {}):
                    today_data = daily_data[recent_date][work_type]
                    total_workers_today += today_data.get('total', 0)
        
        if avg_progress >= 80:
            status, status_color = "완료임박", "success"
        elif avg_progress >= 50:
            status, status_color = "진행중", "warning"
        elif avg_progress >= 1:
            status, status_color = "시작됨", "info"
        else:
            status, status_color = "대기중", "secondary"
            
        dashboard.append({
            'project_name': project_name,
            'recent_date': recent_date or '데이터 없음',
            'today_workers': total_workers_today,
            'cumulative_workers': total_workers_today * 10,  # 임시값
            'avg_progress': avg_progress,
            'work_count': work_count,
            'status': status,
            'status_color': status_color
        })
    return dashboard

def calculate_project_summary(project_name, current_date):
    project_data = dm.projects_data.get(project_name, {})
    daily_data = project_data.get('daily_data', {})
    work_types = project_data.get('work_types', [])
    summary = []
    
    for work_type in work_types:
        # 오늘 데이터
        today_data = daily_data.get(current_date, {}).get(work_type, {})
        
        # 실제 누계 계산 (모든 날짜 합계)
        cumulative_total = 0
        cumulative_day = 0
        cumulative_night = 0 
        cumulative_midnight = 0
        
        for date_key, date_data in daily_data.items():
            if work_type in date_data:
                work_data = date_data[work_type]
                cumulative_total += work_data.get('total', 0)
                cumulative_day += work_data.get('day', 0)
                cumulative_night += work_data.get('night', 0)
                cumulative_midnight += work_data.get('midnight', 0)
        
        summary.append({
            'work_type': work_type,
            'today': today_data.get('total', 0),
            'today_day': today_data.get('day', 0),        # ← 추가!
            'today_night': today_data.get('night', 0),    # ← 추가!
            'today_midnight': today_data.get('midnight', 0),  # ← 추가!
            'cumulative': cumulative_total,
            'cumulative_day': cumulative_day,             # ← 추가!
            'cumulative_night': cumulative_night,         # ← 추가!
            'cumulative_midnight': cumulative_midnight,   # ← 추가!
            'today_progress': today_data.get('progress', 0),
            'cumulative_progress': today_data.get('progress', 0)
        })
    return summary

# ===== 인증 라우트 =====
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

# ===== 관리자 라우트 =====
@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    dashboard_data = calculate_dashboard_data()
    return render_template('admin_dashboard.html', dashboard_data=dashboard_data)

@app.route('/admin/projects')
def admin_projects():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    available_work_types = list(dm.labor_costs.keys())
    return render_template('admin_projects.html',
                           projects_data=dm.projects_data,
                           available_work_types=available_work_types)

@app.route('/admin/projects/create', methods=['POST'])
def create_project():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    project_name = request.form.get('project_name', '').strip()
    selected_work_types = request.form.getlist('work_types')
    
    contracts = {}
    for wt in selected_work_types:
        raw = (request.form.get(f'contract_{wt}', '') or '').replace(',', '').strip()
        contracts[wt] = int(float(raw)) if raw else 0

    if project_name and project_name not in dm.projects_data:
        dm.projects_data[project_name] = {
            'work_types': selected_work_types,
            'contracts': contracts,
            'daily_data': {},
            'status': 'active',
            'created_date': date.today().strftime('%Y-%m-%d')
        }
        dm.save_data()

    return redirect(url_for('admin_projects'))

@app.route('/admin/projects/edit/<project_name>')
def edit_project(project_name):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if project_name not in dm.projects_data:
        return redirect(url_for('admin_projects'))

    available_work_types = list(dm.labor_costs.keys())
    project_data = dm.projects_data[project_name]

    return render_template('admin_project_edit.html',
                           project_name=project_name,
                           project_data=project_data,
                           available_work_types=available_work_types)

@app.route('/admin/projects/update/<project_name>', methods=['POST'])
def update_project(project_name):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if project_name not in dm.projects_data:
        return redirect(url_for('admin_projects'))

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
    return redirect(url_for('admin_projects'))

@app.route('/admin/projects/delete/<project_name>')
def delete_project(project_name):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if project_name in dm.projects_data:
        del dm.projects_data[project_name]
        for user_data in dm.users.values():
            if 'projects' in user_data and project_name in user_data['projects']:
                user_data['projects'].remove(project_name)
        dm.save_data()
    return redirect(url_for('admin_projects'))

# ===== 사용자 관리 =====
@app.route('/admin/users')
def admin_users():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    available_projects = list(dm.projects_data.keys())
    return render_template('admin_users.html',
                           users=dm.users,
                           available_projects=available_projects)

@app.route('/admin/users/create', methods=['POST'])
def create_user():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

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
def edit_user(username):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if username not in dm.users or username == 'admin':
        return redirect(url_for('admin_users'))

    available_projects = list(dm.projects_data.keys())
    user_data = dm.users[username]

    return render_template('admin_user_edit.html',
                           username=username,
                           user_data=user_data,
                           available_projects=available_projects)

@app.route('/admin/users/update/<username>', methods=['POST'])
def update_user(username):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
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
def delete_user(username):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if username in dm.users and username != 'admin' and username != session['username']:
        del dm.users[username]
        dm.save_data()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/toggle-status/<username>')
def toggle_user_status(username):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if username in dm.users and username != 'admin':
        current_status = dm.users[username].get('status', 'active')
        dm.users[username]['status'] = 'inactive' if current_status == 'active' else 'active'
        dm.save_data()
    return redirect(url_for('admin_users'))

# ===== 노무단가 관리 =====
@app.route('/admin/labor-cost')
def admin_labor_cost():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    work_types = list(dm.labor_costs.keys())
    return render_template('admin_labor_cost.html',
                           labor_costs=dm.labor_costs,
                           work_types=sorted(work_types))

@app.route('/admin/labor-cost/save', methods=['POST'])
def save_labor_cost():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # 기존 공종 업데이트
    for work_type in list(dm.labor_costs.keys()):
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
    return redirect(url_for('admin_labor_cost'))

# ===== 리포트 =====
@app.route('/admin/reports')
def admin_reports():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
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
                
                # 비용 계산
                if work_type in dm.labor_costs:
                    day_cost = work_data.get('day', 0) * dm.labor_costs[work_type].get('day', 0)
                    night_cost = work_data.get('night', 0) * dm.labor_costs[work_type].get('night', 0)
                    midnight_cost = work_data.get('midnight', 0) * dm.labor_costs[work_type].get('midnight', 0)
                    total_cost += day_cost + night_cost + midnight_cost
        
        reports_data['projects_summary'].append({
            'name': project_name,
            'work_types_count': len(work_types),
            'total_workers': total_workers,
            'total_cost': total_cost,
            'working_days': total_days,
            'avg_progress': 25.0,  # 임시값
            'status': project_data.get('status', 'active')
        })
        
        reports_data['total_cost'] += total_cost
        reports_data['total_workers'] += total_workers
    
    return render_template('admin_reports.html',
                           reports_data=reports_data,
                           projects_data=dm.projects_data)

@app.route('/admin/reports/export/csv')
def export_csv():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
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

# ===== 사용자 라우트 =====
@app.route('/user')
def user_projects():
    if 'username' not in session or session['role'] != 'user':
        return redirect(url_for('login'))
    username = session['username']
    projects = dm.users[username].get('projects', [])
    return render_template('user_projects.html', projects=projects)

@app.route('/project/<project_name>')
def project_detail(project_name):
    if 'username' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    username = session['username']
    user_projects_list = dm.users[username].get('projects', [])

    if project_name not in user_projects_list:
        return redirect(url_for('user_projects'))

    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    project_data = dm.projects_data.get(project_name, {})
    work_types = project_data.get('work_types', [])
    today_data = project_data.get('daily_data', {}).get(selected_date, {})
    total_summary = calculate_project_summary(project_name, selected_date)

    return render_template('project_input.html',
                           project_name=project_name,
                           work_types=work_types,
                           today_data=today_data,
                           selected_date=selected_date,
                           total_summary=total_summary)

@app.route('/project/<project_name>/save', methods=['POST'])
def save_project_data(project_name):
    if 'username' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    selected_date = request.form.get('date', date.today().strftime('%Y-%m-%d'))

    if project_name not in dm.projects_data:
        dm.projects_data[project_name] = {'work_types': [], 'daily_data': {}}

    if selected_date not in dm.projects_data[project_name]['daily_data']:
        dm.projects_data[project_name]['daily_data'][selected_date] = {}

    for work_type in dm.projects_data[project_name]['work_types']:
        day_input = request.form.get(f'{work_type}_day', '0')
        night_input = request.form.get(f'{work_type}_night', '0')
        midnight_input = request.form.get(f'{work_type}_midnight', '0')
        progress_input = request.form.get(f'{work_type}_progress', '0')

        day_workers = int(day_input) if day_input.strip() else 0
        night_workers = int(night_input) if night_input.strip() else 0
        midnight_workers = int(midnight_input) if midnight_input.strip() else 0
        
        try:
            progress = float(progress_input) if progress_input.strip() else 0.0
        except ValueError:
            progress = 0.0

        total_workers = day_workers + night_workers + midnight_workers

        dm.projects_data[project_name]['daily_data'][selected_date][work_type] = {
            'day': day_workers,
            'night': night_workers,
            'midnight': midnight_workers,
            'total': total_workers,
            'progress': progress
        }

    dm.save_data()
    return redirect(url_for('project_detail', project_name=project_name, date=selected_date))

@app.route('/project/<project_name>/add-work-type', methods=['POST'])
def add_work_type_to_project(project_name):
    """사용자가 프로젝트에 새 공종 추가"""
    if 'username' not in session or session['role'] != 'user':
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    username = session['username']
    user_projects_list = dm.users[username].get('projects', [])
    
    if project_name not in user_projects_list:
        return jsonify({'success': False, 'message': '프로젝트 접근 권한이 없습니다.'})
    
    try:
        data = request.get_json()
        work_type = data.get('work_type', '').strip()
        
        if not work_type:
            return jsonify({'success': False, 'message': '공종명을 입력해주세요.'})
        
        if work_type in dm.projects_data[project_name]['work_types']:
            return jsonify({'success': False, 'message': '이미 존재하는 공종입니다.'})
        
        dm.projects_data[project_name]['work_types'].append(work_type)
        
        if work_type not in dm.labor_costs:
            dm.labor_costs[work_type] = {
                'day': 0, 'night': 0, 'midnight': 0,
                'locked': False,
                'created_by_user': username,
                'created_date': date.today().strftime('%Y-%m-%d')
            }
        
        dm.save_data()
        
        return jsonify({
            'success': True,
            'message': f'"{work_type}" 공종이 추가되었습니다.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

# ===== 유틸리티 라우트 =====
@app.route('/reset-all-data')
def reset_all_data():
    """전체 데이터 완전 초기화"""
    try:
        dm._create_default_data()
        dm.save_data()
        
        return f"""
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            .success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; }}
            .info {{ background: #d1ecf1; border: 1px solid #bee5eb; padding: 10px; border-radius: 5px; margin: 10px 0; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 10px 20px; 
                      text-decoration: none; border-radius: 5px; margin: 5px; }}
        </style>
        
        <div class="success">
            <h2>✅ 시스템 초기화 완료!</h2>
        </div>
        
        <div class="info">
            <h3>📊 초기 데이터</h3>
            <p><strong>프로젝트:</strong> {list(dm.projects_data.keys())}</p>
            <p><strong>공종:</strong> {dm.projects_data.get('현대카드 인테리어공사', {}).get('work_types', [])}</p>
            <p><strong>노무단가:</strong> {list(dm.labor_costs.keys())}</p>
        </div>
        
        <div class="info">
            <h3>🔑 계정 정보</h3>
            <p><strong>관리자:</strong> admin / 1234</p>
            <p><strong>사용자:</strong> user1 / 1234</p>
        </div>
        
        <div style="margin-top: 30px;">
            <a href="/" class="button">🏠 홈으로</a>
        </div>
        """
        
    except Exception as e:
        return f"초기화 실패: {str(e)}"
    
    # 이 코드를 app.py 맨 마지막 부분에 추가 (if __name__ == '__main__' 위에)
@app.route('/check-work-type-similarity', methods=['POST'])
def check_work_type_similarity():
    data = request.get_json()
    new_type = data.get('work_type', '').strip()
    
    existing_types = list(dm.labor_costs.keys())  # 기존 공종들
    similar_types = []
    
    for existing in existing_types:
        # "타일" 입력했을 때 "타일공사" 찾기
        if new_type in existing or existing in new_type:
            if new_type.lower() != existing.lower():  # 완전히 같지 않으면
                similar_types.append(existing)
    
    return jsonify({
        'similar_types': similar_types,
        'has_similarity': len(similar_types) > 0
    })

# 기존 공종 목록 가져오기
@app.route('/get-available-work-types')
def get_available_work_types():
    return jsonify({
        'work_types': list(dm.labor_costs.keys())
    })
    
    
@app.route('/admin/update-work-type-name', methods=['POST'])
def update_work_type_name():
    if 'username' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    try:
        data = request.get_json()
        old_name = data.get('old_name', '').strip()
        new_name = data.get('new_name', '').strip()
        
        if not old_name or not new_name:
            return jsonify({'success': False, 'message': '공종명을 입력해주세요.'})
        
        if old_name == new_name:
            return jsonify({'success': True, 'message': '변경사항이 없습니다.'})
            
        if new_name in dm.labor_costs and new_name != old_name:
            return jsonify({'success': False, 'message': '이미 존재하는 공종명입니다.'})
        
        # 노무단가에서 공종명 변경
        if old_name in dm.labor_costs:
            dm.labor_costs[new_name] = dm.labor_costs.pop(old_name)
        
        # 모든 프로젝트에서 공종명 변경
        for project_data in dm.projects_data.values():
            if 'work_types' in project_data and old_name in project_data['work_types']:
                idx = project_data['work_types'].index(old_name)
                project_data['work_types'][idx] = new_name
            
            # 일일 데이터에서도 공종명 변경
            for daily_data in project_data.get('daily_data', {}).values():
                if old_name in daily_data:
                    daily_data[new_name] = daily_data.pop(old_name)
        
        dm.save_data()
        return jsonify({'success': True, 'message': '공종명이 변경되었습니다.'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})    
    
def calculate_project_work_summary(project_name):
    """프로젝트별 공종 현황 계산 (엑셀 테이블용)"""
    project_data = dm.projects_data.get(project_name, {})
    work_types = project_data.get('work_types', [])
    daily_data = project_data.get('daily_data', {})
    contracts = project_data.get('contracts', {})
    companies = project_data.get('companies', {})  # 새로 추가될 업체 정보
    
    summary = []
    
    for work_type in work_types:
        # 투입인원 누계 계산
        total_workers = 0
        for date_data in daily_data.values():
            if work_type in date_data:
                total_workers += date_data[work_type].get('total', 0)
        
        # 노무단가 가져오기
        labor_rate = dm.labor_costs.get(work_type, {}).get('day', 0)
        
        # 계약노무비
        contract_amount = contracts.get(work_type, 0)
        
        # 투입노무비 계산
        total_labor_cost = total_workers * labor_rate
        
        # 잔액 계산
        balance = contract_amount - total_labor_cost
        
        summary.append({
            'work_type': work_type,
            'company': companies.get(work_type, ''),  # 업체명
            'contract_amount': contract_amount,       # 계약노무비
            'total_workers': total_workers,           # 투입인원
            'labor_rate': labor_rate,                # 단가
            'total_labor_cost': total_labor_cost,    # 투입노무비
            'balance': balance                       # 잔액
        })
    
    return summary    
    

# ===== 실행 =====
if __name__ == '__main__':
    print("🚀 노무비 관리 시스템 시작...")
    print(f"📊 초기 데이터 로드: 프로젝트 {len(dm.projects_data)}개, 노무단가 {len(dm.labor_costs)}개")
    print("🌐 브라우저에서 http://localhost:5000 접속")
    
    # Railway 배포용 포트 설정 수정 체크차해봄
    
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)