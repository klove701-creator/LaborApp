# auth.py - 인증 관리
import hashlib
import secrets

class AuthManager:
    def __init__(self, database_manager):
        self.dm = database_manager
    
    def authenticate_user(self, username, password):
        """사용자 인증"""
        try:
            users = self.dm.get_users()
            user = users.get(username)
            
            if not user:
                return None
                
            # 단순 비교 (실제 운영에서는 해시 비교 사용)
            if user['password'] == password:
                return user
                
            return None
            
        except Exception as e:
            print(f"❌ 사용자 인증 실패: {e}")
            return None
    
    def hash_password(self, password):
        """비밀번호 해시화 (향후 사용)"""
        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return salt + pwdhash.hex()
    
    def verify_password(self, stored_password, provided_password):
        """해시된 비밀번호 검증 (향후 사용)"""
        try:
            salt = stored_password[:32]
            stored_hash = stored_password[32:]
            pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return pwdhash.hex() == stored_hash
        except:
            return False