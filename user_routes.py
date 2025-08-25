# user_routes.py - 사용자 전용 라우트
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from datetime import date
from utils import calculate_project_summary

user_bp = Blueprint('user', __name__)

def get_data_manager():
    """데이터 매니저 인스턴스 가져오기"""
    from app import dm
    return dm

def user_required(f):
    """사용자 권한 확인 데코레이터"""
    def wrapper(*args, **kwargs):
        if 'username' not in session or session['role'] != 'user':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def project_access_required(f):
    """프로젝트 접근 권한 확인 데코레이터"""
    def wrapper(project_name, *args, **kwargs):
        dm = get_data_manager()
        username = session['username']
        user_projects_list = dm.users[username].get('projects', [])
        
        if project_name not in user_projects_list:
            return redirect(url_for('user.projects'))
        return f(project_name, *args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ===== 사용자 프로젝트 목록 =====
@user_bp.route('/')
@user_required
def projects():
    dm = get_data_manager()
    username = session['username']
    user_projects = dm.users[username].get('projects', [])
    
    # 프로젝트 상세 정보 추가
    project_details = []
    for project_name in user_projects:
        if project_name in dm.projects_data:
            project_data = dm.projects_data[project_name]
            work_types_count = len(project_data.get('work_types', []))
            daily_data = project_data.get('daily_data', {})
            
            # 최근 입력 날짜
            recent_date = max(daily_data.keys()) if daily_data else None
            
            # 총 작업일수
            total_days = len(daily_data)
            
            # 평균 공정율 계산
            total_progress = 0
            work_types = project_data.get('work_types', [])
            if work_types:
                for work_type in work_types:
                    max_progress = 0
                    for date_data in daily_data.values():
                        if work_type in date_data:
                            progress = date_data[work_type].get('progress', 0)
                            if progress > max_progress:
                                max_progress = progress
                    total_progress += max_progress
                avg_progress = round(total_progress / len(work_types), 1)
            else:
                avg_progress = 0
            
            project_details.append({
                'name': project_name,
                'work_types_count': work_types_count,
                'recent_date': recent_date,
                'total_days': total_days,
                'avg_progress': avg_progress,
                'status': project_data.get('status', 'active')
            })
    
    return render_template('user_projects.html', 
                           projects=user_projects,
                           project_details=project_details)

# ===== 프로젝트 상세 (출역 입력) =====
@user_bp.route('/project/<project_name>')
@user_required
@project_access_required
def project_detail(project_name):
    dm = get_data_manager()
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    project_data = dm.projects_data.get(project_name, {})
    work_types = project_data.get('work_types', [])
    today_data = project_data.get('daily_data', {}).get(selected_date, {})
    total_summary = calculate_project_summary(project_name, selected_date, dm.projects_data)

    # 최근 5일 데이터 (참고용)
    recent_dates = sorted(project_data.get('daily_data', {}).keys(), reverse=True)[:5]
    recent_data = []
    for recent_date in recent_dates:
        date_data = project_data['daily_data'][recent_date]
        total_workers = sum(work_data.get('total', 0) for work_data in date_data.values())
        recent_data.append({
            'date': recent_date,
            'total_workers': total_workers
        })

    return render_template('project_input.html',
                           project_name=project_name,
                           work_types=work_types,
                           today_data=today_data,
                           selected_date=selected_date,
                           total_summary=total_summary,
                           recent_data=recent_data)

# ===== 출역 데이터 저장 =====
@user_bp.route('/project/<project_name>/save', methods=['POST'])
@user_required
@project_access_required
def save_project_data(project_name):
    dm = get_data_manager()
    selected_date = request.form.get('date', date.today().strftime('%Y-%m-%d'))
    work_data = {}

    for work_type in dm.projects_data[project_name]['work_types']:
        day_input = request.form.get(f'{work_type}_day', '0')
        night_input = request.form.get(f'{work_type}_night', '0')
        midnight_input = request.form.get(f'{work_type}_midnight', '0')
        progress_input = request.form.get(f'{work_type}_progress', '0')

        # 입력값 처리
        day_workers = int(day_input) if day_input.strip() else 0
        night_workers = int(night_input) if night_input.strip() else 0
        midnight_workers = int(midnight_input) if midnight_input.strip() else 0
        
        try:
            progress = float(progress_input) if progress_input.strip() else 0.0
        except ValueError:
            progress = 0.0

        work_data[work_type] = {
            'day': day_workers,
            'night': night_workers,
            'midnight': midnight_workers,
            'total': day_workers + night_workers + midnight_workers,
            'progress': progress
        }

    # 데이터 저장
    if dm.save_daily_work(project_name, selected_date, work_data):
        return redirect(url_for('user.project_detail', 
                               project_name=project_name, 
                               date=selected_date))
    else:
        # 에러 처리
        return redirect(url_for('user.project_detail', 
                               project_name=project_name, 
                               error='저장에 실패했습니다.'))

# ===== 공종 추가 (AJAX) =====
@user_bp.route('/project/<project_name>/add-work-type', methods=['POST'])
@user_required
@project_access_required
def add_work_type_to_project(project_name):
    dm = get_data_manager()
    username = session['username']
    
    try:
        data = request.get_json()
        work_type = data.get('work_type', '').strip()
        
        if not work_type:
            return jsonify({'success': False, 'message': '공종명을 입력해주세요.'})
        
        if dm.add_work_type_to_project(project_name, work_type, username):
            return jsonify({
                'success': True,
                'message': f'"{work_type}" 공종이 추가되었습니다.'
            })
        else:
            return jsonify({'success': False, 'message': '이미 존재하는 공종입니다.'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

# ===== 프로젝트 현황 보기 =====
@user_bp.route('/project/<project_name>/status')
@user_required
@project_access_required
def project_status(project_name):
    dm = get_data_manager()
    project_data = dm.projects_data.get(project_name, {})
    daily_data = project_data.get('daily_data', {})
    work_types = project_data.get('work_types', [])
    
    # 날짜별 통계
    date_stats = []
    total_workers_all = 0
    total_cost_all = 0
    
    for date_key in sorted(daily_data.keys(), reverse=True):
        date_data = daily_data[date_key]
        daily_workers = sum(work_data.get('total', 0) for work_data in date_data.values())
        
        # 일일 비용 계산
        daily_cost = 0
        for work_type, work_data in date_data.items():
            if work_type in dm.labor_costs:
                daily_cost += (
                    work_data.get('day', 0) * dm.labor_costs[work_type].get('day', 0) +
                    work_data.get('night', 0) * dm.labor_costs[work_type].get('night', 0) +
                    work_data.get('midnight', 0) * dm.labor_costs[work_type].get('midnight', 0)
                )
        
        # 일일 평균 공정율
        daily_progress = 0
        if work_types:
            total_progress = sum(date_data.get(wt, {}).get('progress', 0) for wt in work_types)
            daily_progress = round(total_progress / len(work_types), 1)
        
        date_stats.append({
            'date': date_key,
            'workers': daily_workers,
            'cost': daily_cost,
            'progress': daily_progress
        })
        
        total_workers_all += daily_workers
        total_cost_all += daily_cost
    
    # 공종별 통계
    work_type_stats = []
    for work_type in work_types:
        wt_workers = 0
        wt_cost = 0
        wt_days = 0
        max_progress = 0
        
        for date_data in daily_data.values():
            if work_type in date_data:
                wt_data = date_data[work_type]
                wt_workers += wt_data.get('total', 0)
                wt_days += 1
                
                if work_type in dm.labor_costs:
                    wt_cost += (
                        wt_data.get('day', 0) * dm.labor_costs[work_type].get('day', 0) +
                        wt_data.get('night', 0) * dm.labor_costs[work_type].get('night', 0) +
                        wt_data.get('midnight', 0) * dm.labor_costs[work_type].get('midnight', 0)
                    )
                
                progress = wt_data.get('progress', 0)
                if progress > max_progress:
                    max_progress = progress
        
        work_type_stats.append({
            'work_type': work_type,
            'total_workers': wt_workers,
            'total_cost': wt_cost,
            'working_days': wt_days,
            'avg_daily_workers': round(wt_workers / wt_days, 1) if wt_days > 0 else 0,
            'max_progress': max_progress
        })
    
    return render_template('user_project_status.html',
                           project_name=project_name,
                           project_data=project_data,
                           date_stats=date_stats,
                           work_type_stats=work_type_stats,
                           total_workers=total_workers_all,
                           total_cost=total_cost_all,
                           total_days=len(daily_data))

# ===== 프로젝트 과거 데이터 수정 =====
@user_bp.route('/project/<project_name>/edit/<edit_date>')
@user_required
@project_access_required
def edit_project_data(project_name, edit_date):
    dm = get_data_manager()
    project_data = dm.projects_data.get(project_name, {})
    work_types = project_data.get('work_types', [])
    edit_data = project_data.get('daily_data', {}).get(edit_date, {})
    
    return render_template('user_edit_data.html',
                           project_name=project_name,
                           work_types=work_types,
                           edit_data=edit_data,
                           edit_date=edit_date)

@user_bp.route('/project/<project_name>/update/<edit_date>', methods=['POST'])
@user_required
@project_access_required
def update_project_data(project_name, edit_date):
    dm = get_data_manager()
    work_data = {}

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

        work_data[work_type] = {
            'day': day_workers,
            'night': night_workers,
            'midnight': midnight_workers,
            'total': day_workers + night_workers + midnight_workers,
            'progress': progress
        }

    dm.save_daily_work(project_name, edit_date, work_data)
    return redirect(url_for('user.project_status', project_name=project_name))