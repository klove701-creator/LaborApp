# user_routes.py - 사용자 라우트

def register_user_routes(app, dm):
    """사용자 관련 라우트를 등록합니다."""
    
    @app.route('/user/projects')
    def user_projects():
        """사용자 프로젝트 목록 페이지 (임시)"""
        from flask import session, redirect, url_for
        if 'username' not in session:
            return redirect(url_for('login'))
        return "<h1>사용자 프로젝트 페이지</h1><p>개발 중입니다.</p>"
    
    pass