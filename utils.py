# utils.py - 유틸리티 함수

_data_manager = None

# 건강보험료 정책 설정
HEALTH_POLICY = {
    'rate': 0.0334,  # 건강보험료율 3.34%
    'long_term_care_rate': 0.004591  # 장기요양보험료율 0.4591%
}

def set_data_manager(dm):
    """데이터 매니저를 설정합니다."""
    global _data_manager
    _data_manager = dm

def get_data_manager():
    """데이터 매니저를 반환합니다."""
    return _data_manager

def parse_int(value, default=0):
    """문자열을 정수로 변환합니다."""
    try:
        if value is None or value == '':
            return default
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default

def parse_float(value, default=0.0):
    """문자열을 실수로 변환합니다."""
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default