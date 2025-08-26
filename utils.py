# utils.py - 유틸리티 함수들
from functools import wraps
from flask import session, redirect, url_for, render_template

# Gyun Studio 위험도 기준(회사 정책)
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

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from app import dm  # 순환 import 방지
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