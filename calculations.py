# calculations.py - 계산 관련 로직들
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
    """회사 기준(HEALTH_POLICY)에 따른 상태 산정"""
    from app import dm  # 순환 import 방지
    
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
        'overrun_pct': overrun_pct,
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
            'status': status,
            'status_color': status_color,
            'health_meta': meta
        })
    return dashboard

def calculate_project_summary(project_name, current_date):
    from app import dm  # 순환 import 방지
    
    project_data = dm.projects_data.get(project_name, {})
    daily_data = project_data.get('daily_data', {})
    work_types = project_data.get('work_types', [])
    summary = []
    
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
            'today_progress': today_progress,
            'cumulative_progress': cumulative_progress,
        })
    return summary


def calculate_project_work_summary(project_name):
    """프로젝트별 공종 현황 계산 (엑셀 테이블용)"""
    from app import dm  # 순환 import 방지
    
    project_data = dm.projects_data.get(project_name, {})
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