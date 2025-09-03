# calculations.py - 계산 관련 로직들 (PostgreSQL 버전)
from utils import HEALTH_POLICY, parse_int, parse_float

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
    N = HEALTH_POLICY.get("WORKERS_WINDOW_DAYS", 7)  # 기본값 추가
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

def determine_health(project_data, labor_costs):
    """새로운 위험도 알고리즘에 따른 상태 산정"""
    
    contracts = project_data.get('contracts', {}) or {}
    daily_data = project_data.get('daily_data', {}) or {}
    work_types = project_data.get('work_types', []) or []

    # 1. 비용 위험도 계산: 투입인원/계약인원 비율
    total_contract_workers = 0
    total_invested_workers = 0
    
    for wt in work_types:
        contract_amount = int(contracts.get(wt, 0) or 0)
        rate = (labor_costs.get(wt, {}) or {}).get('day', 0) or 0
        
        # 계약인원
        if rate > 0:
            total_contract_workers += contract_amount / rate
        
        # 투입인원 (누계)
        for date_data in daily_data.values():
            if wt in date_data:
                wd = date_data[wt]
                total_invested_workers += int(wd.get('total', 0) or 0)

    cost_ratio = total_invested_workers / total_contract_workers if total_contract_workers > 0 else 0
    
    cost_flag = 'good'
    if cost_ratio >= HEALTH_POLICY["COST_DANGER_RATIO"]:
        cost_flag = 'bad'
    elif cost_ratio >= HEALTH_POLICY["COST_WARN_RATIO"]:
        cost_flag = 'warn'

    # 2. 공정 위험도 계산: |진행율 - 공정율| 차이
    progress_rate = (total_invested_workers / total_contract_workers * 100) if total_contract_workers > 0 else 0
    
    # 최신 공정율 (사용자가 입력한 값)
    schedule_rate = 0.0
    schedule_count = 0
    if daily_data:
        latest_date = max(daily_data.keys())
        latest_data = daily_data[latest_date]
        for wt in work_types:
            if wt in latest_data:
                schedule_val = latest_data[wt].get('progress', 0)
                schedule_rate += schedule_val
                schedule_count += 1
    
    if schedule_count > 0:
        schedule_rate = schedule_rate / schedule_count
    
    progress_diff = abs(progress_rate - schedule_rate) / 100.0  # 퍼센트를 소수로 변환
    
    sched_flag = 'good'
    if progress_diff >= HEALTH_POLICY["PROGRESS_DANGER_DIFF"]:
        sched_flag = 'bad'
    elif progress_diff >= HEALTH_POLICY["PROGRESS_WARN_DIFF"]:
        sched_flag = 'warn'

    # 3. 인력 급변 (기존 로직 유지)
    delta_ratio, today_workers, recent_avg_workers = _today_vs_recent_workers(project_data)

    workers_flag = 'good'
    if delta_ratio <= HEALTH_POLICY["WORKERS_DANGER_DROP"] or delta_ratio >= HEALTH_POLICY["WORKERS_DANGER_SURGE"]:
        workers_flag = 'bad'
    elif delta_ratio <= HEALTH_POLICY["WORKERS_WARN_DROP"] or delta_ratio >= HEALTH_POLICY["WORKERS_WARN_SURGE"]:
        workers_flag = 'warn'

    # 4. 종합 상태 결정 (3개 신호등의 평균)
    flag_scores = {'good': 0, 'warn': 1, 'bad': 2}
    avg_score = (flag_scores[cost_flag] + flag_scores[sched_flag] + flag_scores[workers_flag]) / 3
    
    if avg_score >= 1.5:
        status, color = '위험', 'danger'
    elif avg_score >= 0.5:
        status, color = '경고', 'warning' 
    else:
        status, color = '양호', 'success'

    return status, color, {
        'cost_ratio': round(cost_ratio, 2),
        'progress_rate': round(progress_rate, 1),
        'schedule_rate': round(schedule_rate, 1),
        'progress_diff': round(progress_diff * 100, 1),
        'today_workers': int(today_workers),
        'recent_avg_workers': float(recent_avg_workers),
        'flags': {
            'cost': cost_flag,
            'schedule': sched_flag,
            'workers': workers_flag,
        }
    }

def calculate_dashboard_data():
    """관리자 대시보드용 데이터 계산 (회사 기준 상태 포함)"""
    from app import dm  # 순환 import 방지
    
    # PostgreSQL 방식으로 데이터 조회
    projects_data = dm.get_projects()
    labor_costs = dm.get_labor_costs()
    
    dashboard = []
    for project_name, project_data in projects_data.items():
        work_types = project_data.get('work_types', [])
        daily_data = project_data.get('daily_data', {})
        contracts = project_data.get('contracts', {})

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

        # 누계 인원 계산
        cumulative_workers = 0
        for date_data in daily_data.values():
            for work_type in work_types:
                if work_type in date_data:
                    cumulative_workers += date_data[work_type].get('total', 0)

        # 총 계약인원 계산 (계약금 / 노무단가)
        total_contract_workers = 0
        for work_type in work_types:
            contract_amount = contracts.get(work_type, 0)
            labor_rate = labor_costs.get(work_type, {}).get('day', 0)
            if labor_rate > 0:
                total_contract_workers += contract_amount / labor_rate

        # 진행률 = 누계인원 / 계약인원 * 100
        progress_rate = 0.0
        if total_contract_workers > 0:
            progress_rate = (cumulative_workers / total_contract_workers) * 100
            progress_rate = min(100, progress_rate)  # 100% 초과 방지

        # 공정률 = 누계 공정률 (각 공종 최신 공정률 평균)
        schedule_rate = 0.0
        progress_count = 0
        if recent_date and recent_date in daily_data:
            for work_type in work_types:
                if work_type in daily_data[recent_date]:
                    progress_val = daily_data[recent_date][work_type].get('progress', 0)
                    schedule_rate += progress_val
                    progress_count += 1
        
        if progress_count > 0:
            schedule_rate = schedule_rate / progress_count

        # 회사 기준 상태 판단
        status, status_color, meta = determine_health(project_data, labor_costs)

        dashboard.append({
            'project_name': project_name,
            'recent_date': recent_date or '데이터 없음',
            'today_workers': total_workers_today,
            'contract_workers': int(total_contract_workers),
            'cumulative_workers': cumulative_workers,
            'schedule_rate': schedule_rate,
            'avg_progress': progress_rate,  # 진행율 = 투입인원/계약인원 * 100
            'work_count': len(work_types),
            'status': status,
            'status_color': status_color,
            'health_meta': meta
        })
    return dashboard

def calculate_project_summary(project_name, current_date):
    from app import dm  # 순환 import 방지
    
    # PostgreSQL 방식으로 데이터 조회
    projects_data = dm.get_projects()
    project_data = projects_data.get(project_name, {})
    daily_data = project_data.get('daily_data', {})
    work_types = project_data.get('work_types', [])
    summary = []
    
    # 합계를 위한 변수들
    total_today_day = 0
    total_today_night = 0
    total_today_midnight = 0
    total_today_workers = 0
    total_cumulative_day = 0
    total_cumulative_night = 0
    total_cumulative_midnight = 0
    total_cumulative_workers = 0
    total_today_progress = 0
    work_type_count = 0
    
    for work_type in work_types:
        # 오늘 데이터
        today_data = daily_data.get(current_date, {}).get(work_type, {})
        today_progress = parse_float(today_data.get('progress', 0))

        # 이전까지의 최대 누적 공정률(이전 날짜들의 누적치)
        previous_max_progress = 0.0
        for date_key in sorted(daily_data.keys()):
            if date_key < current_date and work_type in daily_data[date_key]:
                progress_val = parse_float(
                    daily_data[date_key][work_type].get('progress', 0)
                )
                if progress_val > previous_max_progress:
                    previous_max_progress = progress_val

        # 누계 공정률 = 이전 누계 + 오늘 증가분
        cumulative_progress = previous_max_progress + today_progress
        
        # 실제 누계 계산 (모든 날짜 합계)
        cumulative_total = 0
        cumulative_day = 0
        cumulative_night = 0 
        cumulative_midnight = 0
        
        for date_key, date_data in daily_data.items():
            if date_key <= current_date and work_type in date_data:  # 오늘까지만 포함
                work_data = date_data[work_type]
                cumulative_total += work_data.get('total', 0)
                cumulative_day += work_data.get('day', 0)
                cumulative_night += work_data.get('night', 0)
                cumulative_midnight += work_data.get('midnight', 0)
        
        # 합계 누적
        today_day = today_data.get('day', 0)
        today_night = today_data.get('night', 0)
        today_midnight = today_data.get('midnight', 0)
        today_total = today_data.get('total', 0)
        
        total_today_day += today_day
        total_today_night += today_night
        total_today_midnight += today_midnight
        total_today_workers += today_total
        total_cumulative_day += cumulative_day
        total_cumulative_night += cumulative_night
        total_cumulative_midnight += cumulative_midnight
        total_cumulative_workers += cumulative_total
        total_today_progress += today_progress
        work_type_count += 1
        
        summary.append({
            'work_type': work_type,
            'today': today_total,
            'today_day': today_day,
            'today_night': today_night,
            'today_midnight': today_midnight,
            'cumulative': cumulative_total,
            'cumulative_day': cumulative_day,
            'cumulative_night': cumulative_night,
            'cumulative_midnight': cumulative_midnight,
            'today_progress': today_progress,
            'cumulative_progress': cumulative_progress,
        })
    
    # 합계 누계 공정률 계산 (공종별 누계 공정률의 평균)
    avg_cumulative_progress = 0.0
    if work_type_count > 0:
        avg_cumulative_progress = sum(item['cumulative_progress'] for item in summary) / work_type_count
    
    # 합계 정보를 별도로 반환 (중복 방지)
    totals = {
        'today_day': total_today_day,
        'today_night': total_today_night,
        'today_midnight': total_today_midnight,
        'today': total_today_workers,
        'cumulative_day': total_cumulative_day,
        'cumulative_night': total_cumulative_night,
        'cumulative_midnight': total_cumulative_midnight,
        'cumulative': total_cumulative_workers,
        'cumulative_progress': avg_cumulative_progress
    }
    
    return summary, totals


def calculate_project_work_summary(project_name):
    """프로젝트별 공종 현황 계산 (엑셀 테이블용)"""
    from app import dm  # 순환 import 방지
    
    # PostgreSQL 방식으로 데이터 조회
    projects_data = dm.get_projects()
    labor_costs = dm.get_labor_costs()
    
    project_data = projects_data.get(project_name, {})
    work_types = project_data.get('work_types', [])
    daily_data = project_data.get('daily_data', {})
    contracts = project_data.get('contracts', {})
    companies = project_data.get('companies', {})
    
    summary = []
    for work_type in work_types:
        # 투입인원 누계 계산
        total_workers = 0
        for date_data in daily_data.values():
            if work_type in date_data:
                total_workers += date_data[work_type].get('total', 0)
        
        # 노무단가
        labor_rate = (labor_costs.get(work_type, {}) or {}).get('day', 0)
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