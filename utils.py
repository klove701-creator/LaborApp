# utils.py - 유틸리티 함수

_data_manager = None

def set_data_manager(dm):
    """데이터 매니저를 설정합니다."""
    global _data_manager
    _data_manager = dm

def get_data_manager():
    """데이터 매니저를 반환합니다."""
    return _data_manager