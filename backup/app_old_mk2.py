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

def load_data():
    """JSON 파일에서 데이터 로드"""
    print(f"🔍 JSON 파일 존재 여부: {os.path.exists(DATA_FILE)}")
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ 기존 데이터 로드 완료! 프로젝트 수: {len(data.get('projects_data', {}))}")
                return data
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
    
    # 기본 데이터 (최초 실행시만)
    print("📄 새 JSON 파일 생성")
    default_data = {
        'users': {
            'admin': {'password': '1234', 'role': 'admin'},
            'user1': {'password': '1234', 'role': 'user', 'projects': ['현대카드 인테리어공사']}
        },
        'projects_data': {
            '현대카드 인테리어공사': {
                'work_types': ['도장공사', '목공사', '타일'],
                'daily_data': {},
                'status': 'active',
                'created_date': '2025-08-24',
                'contracts': {
                    '도장공사': 20000,
                    '목공사': 25000,
                    '타일': 30000
                }
            }
        },
        'labor_costs': {
            '도장공사': {'day': 120000, 'night': 150000, 'midnight': 180000},
            '목공사': {'day': 130000, 'night': 160000, 'midnight': 190000},
            '타일': {'day': 140000, 'night': 170000, 'midnight': 200000}
        }
    }
    
    # 새 파일 저장
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        print("✅ 새 JSON 파일 생성 완료!")
    except Exception as e:
        print(f"❌ JSON 파일 생성 실패: {e}")
    
    return default_data

def save_data():
    """모든 데이터를 JSON 파일에 저장"""
    try:
        data = {
            'users': users,
            'projects_data': projects_data,
            'labor_costs': labor_costs,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 데이터 저장 완료! 프로젝트: {list(projects_data.keys())}")
        return True
    except Exception as e:
        print(f"❌ 데이터 저장 실패: {e}")
        return False

# 앱 시작시 데이터 로드
app_data = load_data()
users = app_data['users']
projects_data = app_data['projects_data']
labor_costs = app_data['labor_costs']

@app.template_filter('format_currency')
def format_currency(value):
    """숫자를 천 단위 콤마가 포함된 문자열로 변환"""
    if value is None:
        return "0"
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return str(value)

# ===== 공통/인증 =====
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']

    if username in users and users[username]['password'] == password:
        session['username'] = username
        session['role'] = users[username]['role']

        if users[username]['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_projects'))
    else:
        return render_template('login.html', error='아이디 또는 비밀번호가 틀렸습니다.')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== 관리자 대시보드 =====
@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    dashboard_data = calculate_dashboard_data()
    return render_template('admin_dashboard.html', dashboard_data=dashboard_data)

def calculate_dashboard_data():
    """관리자 대시보드용 데이터 계산"""
    dashboard = []

    for project_name, project_data in projects_data.items():
        work_types = project_data.get('work_types', [])
        daily_data = project_data.get('daily_data', {})

        # 최근 날짜 찾기
        recent_date = max(daily_data.keys()) if daily_data else None

        total_workers_today = 0
        total_workers_cumulative = 0
        total_progress = 0
        work_count = len(work_types)

        for work_type in work_types:
            # 최근 일자 데이터
            if recent_date and work_type in daily_data.get(recent_date, {}):
                today_data = daily_data[recent_date][work_type]
                total_workers_today += today_data.get('total', 0)

                # 해당 공종의 누계 인원
                cumulative_workers = 0
                for date_key, date_data in daily_data.items():
                    if date_key <= recent_date and work_type in date_data:
                        cumulative_workers += date_data[work_type].get('total', 0)
                total_workers_cumulative += cumulative_workers

                # 해당 공종의 누계 공정율
                max_progress = 0
                for date_key in sorted(daily_data.keys()):
                    if date_key < recent_date and work_type in daily_data[date_key]:
                        progress_val = daily_data[date_key][work_type].get('progress', 0)
                        if progress_val > max_progress:
                            max_progress = progress_val
                    elif date_key == recent_date:
                        max_progress += daily_data[date_key][work_type].get('progress', 0)
                total_progress += max_progress

        avg_progress = round(total_progress / work_count, 1) if work_count > 0 else 0

        # 상태 판정
        if avg_progress >= 80:
            status = "완료임박"
            status_color = "success"
        elif avg_progress >= 50:
            status = "진행중"
            status_color = "warning"
        elif avg_progress >= 1:
            status = "시작됨"
            status_color = "info"
        else:
            status = "대기중"
            status_color = "secondary"

        dashboard.append({
            'project_name': project_name,
            'recent_date': recent_date or '데이터 없음',
            'today_workers': total_workers_today,
            'cumulative_workers': total_workers_cumulative,
            'avg_progress': avg_progress,
            'work_count': work_count,
            'status': status,
            'status_color': status_color
        })

    return dashboard

# ===== 관리자 리포트 =====
@app.route('/admin/reports')
def admin_reports():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    reports_data = calculate_reports_data()
    return render_template('admin_reports.html',
                           reports_data=reports_data,
                           projects_data=projects_data)

def calculate_reports_data():
    """리포트용 통합 데이터 계산"""
    reports = {
        'total_projects': len(projects_data),
        'total_users': len([u for u in users.values() if u.get('role') == 'user']),
        'total_work_types': len(labor_costs),
        'projects_summary': [],
        'cost_analysis': {},
        'daily_trends': {}
    }

    total_cost = 0
    total_workers = 0

    for project_name, project_data in projects_data.items():
        work_types = project_data.get('work_types', [])
        daily_data = project_data.get('daily_data', {})

        project_workers = 0
        project_cost = 0
        project_days = len(daily_data)
        avg_progress = 0

        for date_key, date_data in daily_data.items():
            for work_type, work_data in date_data.items():
                day_workers = work_data.get('day', 0)
                night_workers = work_data.get('night', 0)
                midnight_workers = work_data.get('midnight', 0)
                project_workers += day_workers + night_workers + midnight_workers

                if work_type in labor_costs:
                    day_cost = day_workers * labor_costs[work_type].get('day', 0)
                    night_cost = night_workers * labor_costs[work_type].get('night', 0)
                    midnight_cost = midnight_workers * labor_costs[work_type].get('midnight', 0)
                    project_cost += day_cost + night_cost + midnight_cost

        if work_types:
            total_progress = 0
            for work_type in work_types:
                max_progress = 0
                for d in daily_data.values():
                    if work_type in d:
                        max_progress += d[work_type].get('progress', 0)
                total_progress += max_progress
            avg_progress = round(total_progress / len(work_types), 1)

        reports['projects_summary'].append({
            'name': project_name,
            'work_types_count': len(work_types),
            'total_workers': project_workers,
            'total_cost': project_cost,
            'working_days': project_days,
            'avg_progress': avg_progress,
            'status': project_data.get('status', 'active')
        })

        total_cost += project_cost
        total_workers += project_workers

    reports['total_cost'] = total_cost
    reports['total_workers'] = total_workers
    return reports

@app.route('/admin/reports/export/<format>')
def export_data(format):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['프로젝트', '날짜', '공종', '주간', '야간', '심야', '계', '공정율'])

        for project_name, project_data in projects_data.items():
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

    return redirect(url_for('admin_reports'))

# ===== 사용자 화면 =====
@app.route('/user')
def user_projects():
    if 'username' not in session or session['role'] != 'user':
        return redirect(url_for('login'))
    username = session['username']
    projects = users[username].get('projects', [])
    return render_template('user_projects.html', projects=projects)

@app.route('/project/<project_name>')
def project_detail(project_name):
    if 'username' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    username = session['username']
    user_projects_list = users[username].get('projects', [])

    if project_name not in user_projects_list:
        return redirect(url_for('user_projects'))

    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    project_data = projects_data.get(project_name, {})
    work_types = project_data.get('work_types', [])
    today_data = project_data.get('daily_data', {}).get(selected_date, {})
    total_summary = calculate_project_summary(project_name, selected_date)

    return render_template('project_input.html',
                           project_name=project_name,
                           work_types=work_types,
                           today_data=today_data,
                           selected_date=selected_date,
                           total_summary=total_summary)

def calculate_project_summary(project_name, current_date):
    """프로젝트 전체 현황 계산"""
    project_data = projects_data.get(project_name, {})
    daily_data = project_data.get('daily_data', {})
    work_types = project_data.get('work_types', [])

    summary = []

    for work_type in work_types:
        total_workers = 0
        day_total = 0
        night_total = 0
        midnight_total = 0

        for date_key, date_data in daily_data.items():
            if date_key <= current_date and work_type in date_data:
                total_workers += date_data[work_type].get('total', 0)
                day_total += date_data[work_type].get('day', 0)
                night_total += date_data[work_type].get('night', 0)
                midnight_total += date_data[work_type].get('midnight', 0)

        today_data = daily_data.get(current_date, {}).get(work_type, {})
        today_total = today_data.get('total', 0)
        today_progress = today_data.get('progress', 0)

        previous_max_progress = 0
        for date_key in sorted(daily_data.keys()):
            if date_key < current_date and work_type in daily_data[date_key]:
                progress_val = daily_data[date_key][work_type].get('progress', 0)
                if progress_val > previous_max_progress:
                    previous_max_progress = progress_val

        cumulative_progress = previous_max_progress + today_progress

        summary.append({
            'work_type': work_type,
            'today': today_total,
            'cumulative': total_workers,
            'today_progress': today_progress,
            'cumulative_progress': cumulative_progress
        })

    return summary

@app.route('/project/<project_name>/save', methods=['POST'])
def save_project_data(project_name):
    if 'username' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    selected_date = request.form.get('date', date.today().strftime('%Y-%m-%d'))

    if project_name not in projects_data:
        projects_data[project_name] = {'work_types': [], 'daily_data': {}}

    if selected_date not in projects_data[project_name]['daily_data']:
        projects_data[project_name]['daily_data'][selected_date] = {}

    for work_type in projects_data[project_name]['work_types']:
        day_input = request.form.get(f'{work_type}_day', '0')
        night_input = request.form.get(f'{work_type}_night', '0')
        midnight_input = request.form.get(f'{work_type}_midnight', '0')
        progress_input = request.form.get(f'{work_type}_progress', '0')

        day_workers = int(day_input) if day_input and day_input.strip() else 0
        night_workers = int(night_input) if night_input and night_input.strip() else 0
        midnight_workers = int(midnight_input) if midnight_input and midnight_input.strip() else 0
        
        try:
            progress = float(progress_input) if progress_input and progress_input.strip() else 0.0
        except ValueError:
            progress = 0.0

        total_workers = day_workers + night_workers + midnight_workers

        projects_data[project_name]['daily_data'][selected_date][work_type] = {
            'day': day_workers,
            'night': night_workers,
            'midnight': midnight_workers,
            'total': total_workers,
            'progress': progress
        }

    save_data()
    return redirect(url_for('project_detail', project_name=project_name, date=selected_date))

@app.route('/project/<project_name>/add-work-type', methods=['POST'])
def add_work_type_to_project(project_name):
    """사용자가 프로젝트에 새 공종 추가"""
    if 'username' not in session or session['role'] != 'user':
        return jsonify({'success': False, 'message': '권한이 없습니다.'})
    
    username = session['username']
    user_projects_list = users[username].get('projects', [])
    
    if project_name not in user_projects_list:
        return jsonify({'success': False, 'message': '프로젝트 접근 권한이 없습니다.'})
    
    try:
        data = request.get_json()
        work_type = data.get('work_type', '').strip()
        
        if not work_type:
            return jsonify({'success': False, 'message': '공종명을 입력해주세요.'})
        
        if work_type in projects_data[project_name]['work_types']:
            return jsonify({'success': False, 'message': '이미 존재하는 공종입니다.'})
        
        projects_data[project_name]['work_types'].append(work_type)
        
        if work_type not in labor_costs:
            labor_costs[work_type] = {
                'day': 0,
                'night': 0,
                'midnight': 0,
                'locked': False,
                'created_by_user': username,
                'created_date': date.today().strftime('%Y-%m-%d')
            }
        
        save_data()
        
        return jsonify({
            'success': True,
            'message': f'"{work_type}" 공종이 추가되었습니다.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

# ===== 관리자: 프로젝트 관리 =====
@app.route('/admin/projects')
def admin_projects():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    available_work_types = list(labor_costs.keys())
    return render_template('admin_projects.html',
                           projects_data=projects_data,
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

    if project_name and project_name not in projects_data:
        projects_data[project_name] = {
            'work_types': selected_work_types,
            'contracts': contracts,
            'daily_data': {},
            'status': 'active',
            'created_date': date.today().strftime('%Y-%m-%d')
        }

    save_data()
    return redirect(url_for('admin_projects'))

@app.route('/admin/projects/delete/<project_name>')
def delete_project(project_name):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if project_name in projects_data:
        del projects_data[project_name]
        for user_data in users.values():
            if 'projects' in user_data and project_name in user_data['projects']:
                user_data['projects'].remove(project_name)
    save_data()
    return redirect(url_for('admin_projects'))

# ===== 관리자: 사용자 관리 =====
@app.route('/admin/users')
def admin_users():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    available_projects = list(projects_data.keys())
    return render_template('admin_users.html',
                           users=users,
                           available_projects=available_projects)

@app.route('/admin/users/create', methods=['POST'])
def create_user():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'user')
    selected_projects = request.form.getlist('projects')

    if username and password and username not in users:
        users[username] = {
            'password': password,
            'role': role,
            'projects': selected_projects if role == 'user' else [],
            'created_date': date.today().strftime('%Y-%m-%d'),
            'status': 'active'
        }
    save_data()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/update/<username>', methods=['POST'])
def update_user(username):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if username not in users or username == 'admin':
        return redirect(url_for('admin_users'))

    new_username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'user')
    selected_projects = request.form.getlist('projects')
    status = request.form.get('status', 'active')

    if new_username and new_username != username and new_username not in users:
        users[new_username] = users.pop(username)
        username = new_username

    if password:
        users[username]['password'] = password
    users[username]['role'] = role
    users[username]['projects'] = selected_projects if role == 'user' else []
    users[username]['status'] = status

    save_data()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<username>')
def delete_user(username):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if username in users and username != 'admin' and username != session['username']:
        del users[username]
    save_data()
    return redirect(url_for('admin_users'))

# ===== 관리자: 노무단가 =====
@app.route('/admin/labor-cost')
def admin_labor_cost():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    work_types = list(labor_costs.keys())
    return render_template('admin_labor_cost.html',
                           labor_costs=labor_costs,
                           work_types=sorted(work_types))

@app.route('/admin/labor-cost/save', methods=['POST'])
def save_labor_cost():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # 기존 공종 업데이트
    for work_type in list(labor_costs.keys()):
        if labor_costs[work_type].get('locked', False):
            continue

        day_cost = request.form.get(f'{work_type}_day', '').strip()
        night_cost = request.form.get(f'{work_type}_night', '').strip()
        midnight_cost = request.form.get(f'{work_type}_midnight', '').strip()

        try:
            if day_cost and night_cost and midnight_cost:
                day_value = int(day_cost.replace(',', ''))
                night_value = int(night_cost.replace(',', ''))
                midnight_value = int(midnight_cost.replace(',', ''))
                labor_costs[work_type].update({
                    'day': day_value,
                    'night': night_value,
                    'midnight': midnight_value
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
            if new_work_type not in labor_costs:
                day_value = int(new_day.replace(',', ''))
                night_value = int(new_night.replace(',', ''))
                midnight_value = int(new_midnight.replace(',', ''))
                labor_costs[new_work_type] = {
                    'day': day_value,
                    'night': night_value,
                    'midnight': midnight_value,
                    'locked': False
                }
        except (ValueError, AttributeError):
            pass
    
    save_data()
    return redirect(url_for('admin_labor_cost'))

# ===== 긴급 복구 및 디버그 =====
@app.route('/reset-all-data')
def reset_all_data():
    """전체 데이터 완전 초기화"""
    try:
        new_data = {
            'users': {
                'admin': {'password': '1234', 'role': 'admin'},
                'user1': {'password': '1234', 'role': 'user', 'projects': ['현대카드 인테리어공사']}
            },
            'projects_data': {
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
            },
            'labor_costs': {
                '도장공사': {'day': 120000, 'night': 150000, 'midnight': 180000},
                '목공사': {'day': 130000, 'night': 160000, 'midnight': 190000},
                '타일': {'day': 140000, 'night': 170000, 'midnight': 200000}
            },
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        
        # 메모리 업데이트
        projects_data.clear()
        projects_data.update(new_data['projects_data'])
        labor_costs.clear()
        labor_costs.update(new_data['labor_costs'])
        users.clear()
        users.update(new_data['users'])
        
        return f"""
        <h2>✅ 전체 데이터 초기화 완료!</h2>
        <p><strong>프로젝트:</strong> {list(projects_data.keys())}</p>
        <p><strong>공종:</strong> {projects_data.get('현대카드 인테리어공사', {}).get('work_types', [])}</p>
        <p><strong>노무단가:</strong> {list(labor_costs.keys())}</p>
        <p><strong>계정:</strong> admin/1234, user1/1234</p>
        <br>
        <a href="/">홈으로</a>
        """
        
    except Exception as e:
        return f"초기화 실패: {str(e)}"

# ===== 실행 =====
if __name__ == '__main__':
    app.run(debug=True, port=5000)