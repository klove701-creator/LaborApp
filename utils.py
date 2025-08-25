# utils.py - 계산 및 유틸리티 함수들
from datetime import datetime, date

def calculate_dashboard_data(projects_data, labor_costs):
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
            if recent_date and work_type in daily_data.get(recent_date, {}):
                today_data = daily_data[recent_date][work_type]
                total_workers_today += today_data.get('total', 0)

                # 누계 인원
                cumulative_workers = 0
                for date_key, date_data in daily_data.items():
                    if date_key <= recent_date and work_type in date_data:
                        cumulative_workers += date_data[work_type].get('total', 0)
                total_workers_cumulative += cumulative_workers

                # 누계 공정율
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
            'cumulative_workers': total_workers_cumulative,
            'avg_progress': avg_progress,
            'work_count': work_count,
            'status': status,
            'status_color': status_color
        })

    return dashboard

def calculate_project_summary(project_name, current_date, projects_data):
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

        # 선택일자까지 누계
        for date_key, date_data in daily_data.items():
            if date_key <= current_date and work_type in date_data:
                total_workers += date_data[work_type].get('total', 0)
                day_total += date_data[work_type].get('day', 0)
                night_total += date_data[work_type].get('night', 0)
                midnight_total += date_data[work_type].get('midnight', 0)

        # 오늘 데이터
        today_data = daily_data.get(current_date, {}).get(work_type, {})
        today_total = today_data.get('total', 0)
        today_progress = today_data.get('progress', 0)

        # 전일까지의 최고 공정율
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

def calculate_reports_data(projects_data, labor_costs, users):
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

def format_currency(value):
    """숫자를 천 단위 콤마가 포함된 문자열로 변환"""
    if value is None:
        return "0"
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return str(value)