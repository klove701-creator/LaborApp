# utils.py - 유틸리티 함수들 (PostgreSQL 버전)
from functools import wraps
from flask import session, redirect, url_for, request, g
import re

# 전역 데이터매니저 참조
dm = None

def set_data_manager(data_manager):
    """데이터매니저 설정"""
    global dm
    dm = data_manager

# 상태 평가 정책
HEALTH_POLICY = {
    # 비용 초과 임계값
    'COST_OVERRUN_WARN': 0.05,    # 5%
    'COST_OVERRUN_DANGER': 0.12,  # 12%
    
    # 공정율 임계값
    'PROGRESS_WARN_MIN': 0.50,     # 50%
    'PROGRESS_DANGER_MIN': 0.20,   # 20%
    
    # 인력 변동 임계값
    'WORKERS_WARN_DROP': -0.40,    # 40% 감소
    'WORKERS_DANGER_DROP': -0.60,  # 60% 감소
    'WORKERS_WARN_SURGE': 0.40,    # 40% 증가
    'WORKERS_DANGER_SURGE': 0.60,  # 60% 증가
}

def login_required(role=None):
    """로그인 확인 데코레이터"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'username' not in session:
                return redirect(url_for('login'))
            
            u = session['username']
            
            # 사용자 데이터 조회 (PostgreSQL 방식)
            try:
                users = dm.get_users()
                udata = users.get(u, {})
            except Exception as e:
                print(f"사용자 조회 실패: {e}")
                return redirect(url_for('login'))
            
            # 사용자가 존재하지 않거나 비활성화된 경우
            if not udata or udata.get('status') == 'inactive':
                session.clear()
                return redirect(url_for('login'))
            
            # 역할 확인
            user_role = udata.get('role', 'user')
            if role and user_role != role:
                return redirect(url_for('login'))
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def parse_int(value, default=0):
    """문자열을 정수로 변환 (안전)"""
    try:
        return int(str(value).replace(',', '').replace(' ', '') or default)
    except (ValueError, AttributeError):
        return default

def parse_float(value, default=0.0):
    """문자열을 실수로 변환 (안전)"""
    try:
        return float(str(value).replace(',', '').replace(' ', '') or default)
    except (ValueError, AttributeError):
        return default

def validate_work_type_name(name):
    """공종명 유효성 검사"""
    if not name or not isinstance(name, str):
        return False, "공종명을 입력해주세요."
    
    name = name.strip()
    if len(name) < 2:
        return False, "공종명은 2자 이상이어야 합니다."
    
    if len(name) > 50:
        return False, "공종명은 50자를 초과할 수 없습니다."
    
    # 특수문자 제한
    if re.search(r'[<>"\'\\\n\r\t]', name):
        return False, "공종명에 사용할 수 없는 문자가 포함되어 있습니다."
    
    return True, ""

def validate_project_name(name):
    """프로젝트명 유효성 검사"""
    if not name or not isinstance(name, str):
        return False, "프로젝트명을 입력해주세요."
    
    name = name.strip()
    if len(name) < 2:
        return False, "프로젝트명은 2자 이상이어야 합니다."
    
    if len(name) > 100:
        return False, "프로젝트명은 100자를 초과할 수 없습니다."
    
    return True, ""

def calculate_cost_summary(project_data, labor_costs, selected_date=None):
    """프로젝트의 비용 요약 계산"""
    daily_data = project_data.get('daily_data', {})
    
    if selected_date and selected_date in daily_data:
        # 특정 날짜의 비용
        date_data = daily_data[selected_date]
        total_cost = 0
        
        for work_type, work_data in date_data.items():
            if work_type in labor_costs:
                rates = labor_costs[work_type]
                day_cost = work_data.get('day', 0) * rates.get('day', 0)
                night_cost = work_data.get('night', 0) * rates.get('night', 0)
                midnight_cost = work_data.get('midnight', 0) * rates.get('midnight', 0)
                total_cost += day_cost + night_cost + midnight_cost
        
        return {'daily_cost': total_cost}
    else:
        # 전체 프로젝트 비용
        total_cost = 0
        total_days = len(daily_data)
        
        for date_data in daily_data.values():
            for work_type, work_data in date_data.items():
                if work_type in labor_costs:
                    rates = labor_costs[work_type]
                    day_cost = work_data.get('day', 0) * rates.get('day', 0)
                    night_cost = work_data.get('night', 0) * rates.get('night', 0)
                    midnight_cost = work_data.get('midnight', 0) * rates.get('midnight', 0)
                    total_cost += day_cost + night_cost + midnight_cost
        
        return {
            'total_cost': total_cost,
            'working_days': total_days,
            'average_daily_cost': total_cost / max(total_days, 1)
        }

def format_number(value, decimal_places=0):
    """숫자 포맷팅"""
    try:
        if decimal_places == 0:
            return "{:,}".format(int(value))
        else:
            return "{:,.{}f}".format(float(value), decimal_places)
    except (ValueError, TypeError):
        return str(value)

def get_project_health_status(project_data, labor_costs):
    """프로젝트 상태 평가"""
    daily_data = project_data.get('daily_data', {})
    if not daily_data:
        return 'unknown', '데이터 없음'
    
    # 최근 데이터 분석
    dates = sorted(daily_data.keys())
    if len(dates) < 2:
        return 'normal', '데이터 부족'
    
    recent_date = dates[-1]
    previous_date = dates[-2]
    
    recent_data = daily_data[recent_date]
    previous_data = daily_data[previous_date]
    
    # 인력 변화율 계산
    recent_workers = sum(data.get('total', 0) for data in recent_data.values())
    previous_workers = sum(data.get('total', 0) for data in previous_data.values())
    
    if previous_workers > 0:
        worker_change_rate = (recent_workers - previous_workers) / previous_workers
    else:
        worker_change_rate = 0
    
    # 평균 공정율
    recent_progress = []
    for data in recent_data.values():
        if data.get('progress', 0) > 0:
            recent_progress.append(data['progress'])
    
    avg_progress = sum(recent_progress) / len(recent_progress) if recent_progress else 0
    avg_progress_ratio = avg_progress / 100.0
    
    # 상태 판정
    warnings = []
    dangers = []
    
    # 공정율 체크
    if avg_progress_ratio < HEALTH_POLICY['PROGRESS_DANGER_MIN']:
        dangers.append(f"공정율 위험 ({avg_progress:.1f}%)")
    elif avg_progress_ratio < HEALTH_POLICY['PROGRESS_WARN_MIN']:
        warnings.append(f"공정율 주의 ({avg_progress:.1f}%)")
    
    # 인력 변동 체크
    if worker_change_rate <= HEALTH_POLICY['WORKERS_DANGER_DROP']:
        dangers.append(f"인력 급감 ({worker_change_rate*100:.1f}%)")
    elif worker_change_rate <= HEALTH_POLICY['WORKERS_WARN_DROP']:
        warnings.append(f"인력 감소 ({worker_change_rate*100:.1f}%)")
    elif worker_change_rate >= HEALTH_POLICY['WORKERS_DANGER_SURGE']:
        dangers.append(f"인력 급증 ({worker_change_rate*100:.1f}%)")
    elif worker_change_rate >= HEALTH_POLICY['WORKERS_WARN_SURGE']:
        warnings.append(f"인력 급증 주의 ({worker_change_rate*100:.1f}%)")
    
    # 최종 상태 결정
    if dangers:
        return 'danger', '; '.join(dangers)
    elif warnings:
        return 'warning', '; '.join(warnings)
    else:
        return 'normal', '정상'