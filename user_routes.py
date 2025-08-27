# user_routes.py - 사용자 관련 라우트
from flask import render_template, request, redirect, url_for, session, jsonify
from datetime import date
from utils import login_required, parse_int, parse_float
from calculations import calculate_project_summary

def register_user_routes(app, dm):
    
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

        # 데이터 변경 여부 확인을 위해
        data_changed = False

        for work_type in dm.projects_data[project_name]['work_types']:
            day_workers = parse_int(request.form.get(f'{work_type}_day', '0'), 0)
            night_workers = parse_int(request.form.get(f'{work_type}_night', '0'), 0)
            midnight_workers = parse_int(request.form.get(f'{work_type}_midnight', '0'), 0)
            progress = parse_float(request.form.get(f'{work_type}_progress', '0'), 0.0)

            total_workers = day_workers + night_workers + midnight_workers

            # 기존 데이터와 비교해서 변경 여부 확인
            old_data = dm.projects_data[project_name]['daily_data'][selected_date].get(work_type, {})
            new_data = {
                'day': day_workers,
                'night': night_workers,
                'midnight': midnight_workers,
                'total': total_workers,
                'progress': progress
            }
            
            if old_data != new_data:
                data_changed = True
                dm.projects_data[project_name]['daily_data'][selected_date][work_type] = new_data
                print(f"✅ 데이터 변경 감지: {project_name} - {work_type} - {selected_date}")

        # 데이터가 변경된 경우에만 저장
        if data_changed:
            success = dm.save_data()
            if success:
                print(f"✅ 프로젝트 데이터 저장 성공: {project_name}")
            else:
                print(f"❌ 프로젝트 데이터 저장 실패: {project_name}")
        else:
            print(f"ℹ️ 변경 사항 없음: {project_name}")

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