# user_routes.py - 사용자 관련 라우트 (PostgreSQL 버전)
from flask import render_template, request, redirect, url_for, session, jsonify
from datetime import date
from utils import login_required, parse_int, parse_float
from calculations import calculate_project_summary

def register_user_routes(app, dm):
    
    @app.route('/user')
    @login_required(role='user')
    def user_projects():
        username = session['username']
        users = dm.get_users()
        projects = users[username].get('projects', [])
        return render_template('user_projects.html', projects=projects)

    @app.route('/project/<project_name>')
    @login_required(role='user')
    def project_detail(project_name):
        username = session['username']
        users = dm.get_users()
        user_projects_list = users[username].get('projects', [])
        
        if project_name not in user_projects_list:
            return redirect(url_for('user_projects'))

        selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
        projects_data = dm.get_projects()
        project_data = projects_data.get(project_name, {})
        work_types = project_data.get('work_types', [])
        today_data = project_data.get('daily_data', {}).get(selected_date, {})
        total_summary, summary_totals = calculate_project_summary(project_name, selected_date)

        return render_template('project_input.html',
                               project_name=project_name,
                               work_types=work_types,
                               today_data=today_data,
                               selected_date=selected_date,
                               total_summary=total_summary,
                               summary_totals=summary_totals)

    @app.route('/project/<project_name>/dates-with-data')
    @login_required(role='user')
    def project_dates_with_data(project_name):
        """Return list of dates that have entries for given project"""
        username = session['username']
        users = dm.get_users()
        user_projects_list = users[username].get('projects', [])
        
        if project_name not in user_projects_list:
            return jsonify({'success': False, 'message': '프로젝트 접근 권한이 없습니다.'}), 403

        projects_data = dm.get_projects()
        daily_data = projects_data.get(project_name, {}).get('daily_data', {})
        month = request.args.get('month')  # optional 'YYYY-MM'
        
        if month:
            dates = [d for d in daily_data.keys() if d.startswith(month)]
        else:
            dates = list(daily_data.keys())
        dates.sort()
        return jsonify(dates)

    @app.route('/project/<project_name>/save', methods=['POST'])
    @login_required(role='user')
    def save_project_data(project_name):
        selected_date = request.form.get('date', date.today().strftime('%Y-%m-%d'))
        projects_data = dm.get_projects()
        
        if project_name not in projects_data:
            print(f"프로젝트 '{project_name}'가 존재하지 않습니다.")
            return redirect(url_for('user_projects'))

        project_data = projects_data[project_name]
        work_types = project_data.get('work_types', [])

        # 데이터 변경 여부 확인을 위해
        data_changed = False

        for work_type in work_types:
            day_workers = parse_int(request.form.get(f'{work_type}_day', '0'), 0)
            night_workers = parse_int(request.form.get(f'{work_type}_night', '0'), 0)
            midnight_workers = parse_int(request.form.get(f'{work_type}_midnight', '0'), 0)
            progress = parse_float(request.form.get(f'{work_type}_progress', '0'), 0.0)

            total_workers = day_workers + night_workers + midnight_workers

            # 기존 데이터와 비교
            daily_data = project_data.get('daily_data', {})
            old_data = daily_data.get(selected_date, {}).get(work_type, {})
            new_data = {
                'day': day_workers,
                'night': night_workers,
                'midnight': midnight_workers,
                'total': total_workers,
                'progress': progress
            }
            
            if old_data != new_data:
                data_changed = True
                # PostgreSQL에 개별적으로 저장
                dm.save_daily_data(project_name, selected_date, work_type,
                                   day_workers, night_workers, midnight_workers, progress)
                print(f"✅ 데이터 변경 감지: {project_name} - {work_type} - {selected_date}")

        if data_changed:
            print(f"✅ 프로젝트 데이터 저장 성공: {project_name}")
        else:
            print(f"ℹ️ 변경 사항 없음: {project_name}")

        return redirect(url_for('project_detail', project_name=project_name, date=selected_date))

    @app.route('/project/<project_name>/add-work-type', methods=['POST'])
    @login_required(role='user')
    def add_work_type_to_project(project_name):
        """사용자가 프로젝트에 새 공종 추가"""
        username = session['username']
        users = dm.get_users()
        user_projects_list = users[username].get('projects', [])
        
        if project_name not in user_projects_list:
            return jsonify({'success': False, 'message': '프로젝트 접근 권한이 없습니다.'})
        
        try:
            data = request.get_json()
            work_type = (data.get('work_type', '') or '').strip()
            if not work_type:
                return jsonify({'success': False, 'message': '공종명을 입력해주세요.'})
            
            projects_data = dm.get_projects()
            labor_costs = dm.get_labor_costs()
            
            if work_type in projects_data[project_name]['work_types']:
                return jsonify({'success': False, 'message': '이미 존재하는 공종입니다.'})
            
            # 프로젝트에 공종 추가
            current_work_types = projects_data[project_name]['work_types']
            current_work_types.append(work_type)
            dm.update_project(project_name, work_types=current_work_types)
            
            # 노무단가에 없으면 추가
            if work_type not in labor_costs:
                dm.save_labor_cost(work_type, 0, 0, 0, False)
            
            return jsonify({'success': True, 'message': f'"{work_type}" 공종이 추가되었습니다.'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'오류: {str(e)}'})