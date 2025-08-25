from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, flash
from datetime import datetime, date, timedelta
import json
import os
import csv
import io
from functools import wraps

app = Flask(__name__)
# 세션 키는 환경변수 우선
app.secret_key = os.environ.get('SECRET_KEY', 'change_me_in_env')
app.config['JSON_AS_ASCII'] = False

# ===== 경로/유틸 =====
def parse_int(s, default=0):
    try:
        if s is None:
            return default
        return int(float(str(s).replace(',', '').strip()))
    except Exception:
        return default

def parse_float(s, default=0.0):
    try:
        if s is None:
            return default
        return float(str(s).replace(',', '').strip())
    except Exception:
        return default

# 데이터 파일 안전 경로(볼륨 > TMPDIR > CWD)
BASE_DIR = os.environ.get('RAILWAY_VOLUME') or os.environ.get('TMPDIR') or os.getcwd()
DATA_FILE = os.path.join(BASE_DIR, 'app_data.json')

# ===== Gyun Studio 위험도 기준(회사 정책) =====
HEALTH_POLICY = {
    # 비용(계약 대비 투입노무비) 초과율
    "COST_OVERRUN_WARN":   0.05,   # 5% 이상 초과 → 경고
    "COST_OVERRUN_DANGER": 0.12,   # 12% 이상 초과 → 위험

    # 공정(평균 공정률) 하한선 (0~1 비율로 정의; 내부에서 %로 비교)
    "PROGRESS_WARN_MIN":   0.50,   # 50% 미만 → 경고
    "PROGRESS_DANGER_MIN": 0.20,   # 20% 미만 → 위험

    # 인력 급변(오늘 총투입 vs 최근7일 평균)
    "WORKERS_WINDOW_DAYS": 7,
    "WORKERS_WARN_DROP":   -0.40,  # -40% 이하 급감 → 경고
    "WORKERS_DANGER_DROP": -0.60,  # -60% 이하 급감 → 위험
    "WORKERS_WARN_SURGE":   0.40,  # +40% 이상 급증 → 경고
    "WORKERS_DANGER_SURGE": 0.60,  # +60% 이상 급증 → 위험
}

# ===== 권한 데코레이터 =====
def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if 'username' not in session:
                return redirect(url_for('login'))
            u = session['username']
            udata = dm.users.get(u, {})
            # 비활성 계정 차단(admin 제외)
            if u != 'admin' and udata.get('status', 'active') != 'active':
                session.clear()
                return render_template('login.html', error='계정이 비활성화되었습니다. 관리자에게 문의하세요.')
            if role and session.get('role') != role:
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return wrapper
    return deco

# ===== 데이터 저장/로드 시스템 =====
class DataManager:
    def __init__(self):
        self.users = {}
        self.projects_data = {}
        self.labor_costs = {}
        self.load_data()
    
    def load_data(self):
        """JSON 파일에서 데이터 로드"""
        print(f"🔍 JSON 파일 경로: {DATA_FILE} (존재: {os.path.exists(DATA_FILE)})")
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
            'user1': {'password': '1234', 'role': 'user', 'projects': ['현대카드 인테리어공사'], 'status': 'active'}
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
                },
                'companies': {}
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
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            data = {
                'users': self.users,
                'projects_data': self.projects_data,
                'labor_costs': self.labor_costs,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 데이터 저장 완료! → {DATA_FILE}")
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

# ===== 상태 계산 유틸 =====
def _avg_progress(project_data):
    """전체 일자·공종의 progress 평균(입력된 값만). 없으면 0."""
    daily_data = project_data.get('daily_data', {}) or {}
    s = 0.0
    c = 0
    for date_data in daily_data.values():
        for wd in date_data.values():
            try:
                p = float(wd.get('progress') or 0.0)
                s += p
                c += 1
            except:
                pass
    return (s / c) if c else 0.0

def _today_vs_recent_workers(project_data):
    """오늘 총투입 vs 최근 N일 평균 대비 증감률을 반환 (delta_ratio, today_total, recent_avg)."""
    daily_data = project_data.get('daily_data', {}) or {}
    if not daily_data:
        return 0.0, 0, 0.0

    dates = sorted(daily_data.keys())
    today_key = dates[-1] if dates else None
    if not today_key:
        return 0.0, 0, 0.0

    # 오늘 총투입
    today_total = 0
    for wd in daily_data.get(today_key, {}).values():
        today_total += int(wd.get('total', 0) or 0)

    # 최근 N일 평균(오늘 제외)
    N = HEALTH_POLICY["WORKERS_WINDOW_DAYS"]
    prev_keys = dates[:-1][-N:] if len(dates) > 1 else []
    sums = []
    for k in prev_keys:
        t = 0
        for wd in daily_data.get(k, {}).values():
            t += int(wd.get('total', 0) or 0)
        sums.append(t)
    recent_avg = (sum(sums) / len(sums)) if sums else 0.0

    if recent_avg <= 0:
        delta_ratio = 0.0
    else:
        delta_ratio = (today_total - recent_avg) / recent_avg

    return delta_ratio, today_total, recent_avg

def determine_health(project_data):
    """
    회사 기준(HEALTH_POLICY)에 따른 상태 산정:
    - 비용: 계약 vs 투입노무비 초과율
    - 공정: 평균 공정률 하한
    - 인력: 오늘 총투입 vs 최근7일 평균 대비 급변
    → 하나라도 위험이면 '위험', 그 다음 경고, 모두 양호면 '양호'
    """
    contracts = project_data.get('contracts', {}) or {}
    daily_data = project_data.get('daily_data', {}) or {}
    work_types = project_data.get('work_types', []) or []

    # 비용(계약/투입) 집계
    total_contract = 0
    total_labor_cost = 0
    for wt in work_types:
        total_contract += int(contracts.get(wt, 0) or 0)
        # 누계 인원
        cum_total = 0
        for date_data in daily_data.values():
            if wt in date_data:
                wd = date_data[wt]
                cum_total += int(wd.get('total', 0) or 0)
        # 단가(주간 기준 사용)
        rate = (dm.labor_costs.get(wt, {}) or {}).get('day', 0) or 0
        total_labor_cost += cum_total * int(rate)

    # 비용 초과율
    overrun_pct = 0.0
    if total_contract > 0:
        overrun_pct = (total_labor_cost - total_contract) / float(total_contract)

    # 공정 평균 (0~100 가정)
    avg_progress = _avg_progress(project_data)

    # 인력 급변
    delta_ratio, today_workers, recent_avg_workers = _today_vs_recent_workers(project_data)

    # 개별 플래그 판단
    cost_flag = 'good'
    if overrun_pct >= HEALTH_POLICY["COST_OVERRUN_DANGER"]:
        cost_flag = 'bad'
    elif overrun_pct >= HEALTH_POLICY["COST_OVERRUN_WARN"]:
        cost_flag = 'warn'

    sched_flag = 'good'
    if avg_progress < (HEALTH_POLICY["PROGRESS_DANGER_MIN"] * 100.0):
        sched_flag = 'bad'
    elif avg_progress < (HEALTH_POLICY["PROGRESS_WARN_MIN"] * 100.0):
        sched_flag = 'warn'

    workers_flag = 'good'
    if delta_ratio <= HEALTH_POLICY["WORKERS_DANGER_DROP"] or delta_ratio >= HEALTH_POLICY["WORKERS_DANGER_SURGE"]:
        workers_flag = 'bad'
    elif delta_ratio <= HEALTH_POLICY["WORKERS_WARN_DROP"] or delta_ratio >= HEALTH_POLICY["WORKERS_WARN_SURGE"]:
        workers_flag = 'warn'

    # 종합 결정
    if 'bad' in (cost_flag, sched_flag, workers_flag):
        status, color = '위험', 'danger'
    elif 'warn' in (cost_flag, sched_flag, workers_flag):
        status, color = '경고', 'warning'
    else:
        status, color = '양호', 'success'

    return status, color, {
        'avg_progress': round(avg_progress, 1),
        'overrun_pct': overrun_pct,  # 0.08 → 8%
        'today_workers': int(today_workers),
        'recent_avg_workers': float(recent_avg_workers),
        'flags': {
            'cost': cost_flag,
            'schedule': sched_flag,
            'workers': workers_flag,
        }
    }

# ===== 대시보드/요약 =====
def calculate_dashboard_data():
    """관리자 대시보드용 데이터 계산 (회사 기준 상태 포함)"""
    dashboard = []
    for project_name, project_data in dm.projects_data.items():
        work_types = project_data.get('work_types', [])
        daily_data = project_data.get('daily_data', {})

        # 최근 날짜
        recent_date = None
        try:
            if daily_data:
                recent_date = max(daily_data.keys())
        except:
            recent_date = None
        
        # 오늘 총투입
        total_workers_today = 0
        if recent_date and recent_date in daily_data:
            today_pack = daily_data.get(recent_date, {})
            for work_type in work_types:
                today_data = today_pack.get(work_type, {})
                total_workers_today += parse_int(today_data.get('total', 0), 0)

        # 회사 기준 상태 판단
        status, status_color, meta = determine_health(project_data)

        dashboard.append({
            'project_name': project_name,
            'recent_date': recent_date or '데이터 없음',
            'today_workers': total_workers_today,
            'cumulative_workers': total_workers_today * 10,  # TODO: 실제 누계 인원 계산으로 교체 가능
            'schedule_rate': meta.get('avg_progress', 0.0),
            'avg_progress': meta.get('avg_progress', 0.0),
            'work_count': len(work_types),
            'status': status,            # 양호/경고/위험
            'status_color': status_color,
            'health_meta': meta
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
            'today_day': today_data.get('day', 0),
            'today_night': today_data.get('night', 0),
            'today_midnight': today_data.get('midnight', 0),
            'cumulative': cumulative_total,
            'cumulative_day': cumulative_day,
            'cumulative_night': cumulative_night,
            'cumulative_midnight': cumulative_midnight,
            'today_progress': today_data.get('progress', 0),
            'cumulative_progress': today_data.get('progress', 0)
        })
    return summary

def calculate_project_work_summary(project_name):
    """프로젝트별 공종 현황 계산 (엑셀 테이블용)"""
    project_data = dm.projects_data.get(project_name, {})
    work_types = project_data.get('work_types', [])
    daily_data = project_data.get('daily_data', {})
    contracts = project_data.get('contracts', {})
    companies = project_data.get('companies', {})  # 업체 정보
    
    summary = []
    for work_type in work_types:
        # 투입인원 누계 계산
        total_workers = 0
        for date_data in daily_data.values():
            if work_type in date_data:
                total_workers += date_data[work_type].get('total', 0)
        # 노무단가
        labor_rate = (dm.labor_costs.get(work_type, {}) or {}).get('day', 0)
        # 계약노무비
        contract_amount = contracts.get(work_type, 0)
        # 투입노무비
        total_labor_cost = total_workers * parse_int(labor_rate, 0)
        # 잔액
        balance = contract_amount - total_labor_cost
        summary.append({
            'work_type': work_type,
            'company': companies.get(work_type, ''),
            'contract_amount': contract_amount,
            'total_workers': total_workers,
            'labor_rate': labor_rate,
            'total_labor_cost': total_labor_cost,
            'balance': balance
        })
    return summary

@app.context_processor
def utility_processor():
    return dict(
        calculate_project_work_summary=calculate_project_work_summary,
        sum=sum
    )

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
    for wt in selected_work_types:
        contracts[wt] = parse_int(request.form.get(f'contract_{wt}', ''), 0)

    if project_name and project_name not in dm.projects_data:
        dm.projects_data[project_name] = {
            'work_types': selected_work_types,
            'contracts': contracts,
            'daily_data': {},
            'status': 'active',
            'created_date': date.today().strftime('%Y-%m-%d'),
            'companies': {}
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

# ===== 사용자 관리 =====
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

# ===== 노무단가 관리 =====
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

# ===== 리포트 =====
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

# ===== 사용자 라우트 =====
@app.route('/user')
@login_required(role='user')
def user_projects():
    username = session['username']
    projects = dm.users[username].get('projects', [])
    return render_template('user_projects.html', projects=projects)

@app.route('/project/<project_name>')
@login_required(role='user')
def project_detail(project_name):
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
@login_required(role='user')
def save_project_data(project_name):
    selected_date = request.form.get('date', date.today().strftime('%Y-%m-%d'))

    if project_name not in dm.projects_data:
        dm.projects_data[project_name] = {'work_types': [], 'daily_data': {}}

    if selected_date not in dm.projects_data[project_name]['daily_data']:
        dm.projects_data[project_name]['daily_data'][selected_date] = {}

    for work_type in dm.projects_data[project_name]['work_types']:
        day_workers = parse_int(request.form.get(f'{work_type}_day', '0'), 0)
        night_workers = parse_int(request.form.get(f'{work_type}_night', '0'), 0)
        midnight_workers = parse_int(request.form.get(f'{work_type}_midnight', '0'), 0)
        progress = parse_float(request.form.get(f'{work_type}_progress', '0'), 0.0)

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
@login_required(role='user')
def add_work_type_to_project(project_name):
    """사용자가 프로젝트에 새 공종 추가"""
    username = session['username']
    user_projects_list = dm.users[username].get('projects', [])
    if project_name not in user_projects_list:
        return jsonify({'success': False, 'message': '프로젝트 접근 권한이 없습니다.'})
    
    try:
        data = request.get_json()
        work_type = (data.get('work_type', '') or '').strip()
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
        return jsonify({'success': True, 'message': f'"{work_type}" 공종이 추가되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

# ===== 유사 공종 체크/가용 공종 조회/공종명 변경 =====
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
@login_required(role='admin')
def update_work_type_name():
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

# ===== 전체 초기화 (운영 보호: 관리자+POST) =====
@app.route('/reset-all-data', methods=['POST'])
@login_required(role='admin')
def reset_all_data():
    try:
        dm._create_default_data()
        dm.save_data()
        return """
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .success { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; }
            .info { background: #d1ecf1; border: 1px solid #bee5eb; padding: 10px; border-radius: 5px; margin: 10px 0; }
            .button { display: inline-block; background: #007bff; color: white; padding: 10px 20px;
                      text-decoration: none; border-radius: 5px; margin: 5px; }
        </style>
        <div class="success"><h2>✅ 시스템 초기화 완료!</h2></div>
        <div class="info">
            <h3>📊 초기 데이터</h3>
            <p><strong>프로젝트:</strong> {projects}</p>
            <p><strong>공종:</strong> {worktypes}</p>
            <p><strong>노무단가:</strong> {costs}</p>
        </div>
        <div class="info">
            <h3>🔑 계정 정보</h3>
            <p><strong>관리자:</strong> admin / 1234</p>
            <p><strong>사용자:</strong> user1 / 1234</p>
        </div>
        <div style="margin-top: 30px;">
            <a href="/" class="button">🏠 홈으로</a>
        </div>
        """.format(
            projects=list(dm.projects_data.keys()),
            worktypes=dm.projects_data.get('현대카드 인테리어공사', {}).get('work_types', []),
            costs=list(dm.labor_costs.keys())
        )
    except Exception as e:
        return f"초기화 실패: {str(e)}"

# ===== 실행 =====
if __name__ == '__main__':
    print("🚀 노무비 관리 시스템 시작...")
    print(f"📊 초기 데이터 로드: 프로젝트 {len(dm.projects_data)}개, 노무단가 {len(dm.labor_costs)}개")
    print(f"💾 데이터 파일: {DATA_FILE}")
    print("🌐 브라우저에서 http://localhost:5000 접속")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
