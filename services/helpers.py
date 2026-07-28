import bcrypt
import string
import secrets

def validate_password(password:str)->tuple[bool, str]:
    if not password:
        return False, "Password is required"
    
    if len(password) < 10:
        return False, f"Password is too short {len(password)}, It needs to be at least 10 characters long."
    
    if len(password) > 250:
        return False, f"Password is too long {len(password)}, Maximum allowed length is 250 characters."
    
    if not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
        return False, "Password must contain at least one uppercase letter and one number."
    
    return True, "valid password"

def generate_secure_password(length: int = 12) -> str:
    """Generates a secure, random alphanumeric password."""
  
    alphabet = string.ascii_letters + string.digits

    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password:str):
    password_bytes = password.encode('utf-8')

    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    
    return hashed_bytes.decode('utf-8')

def verify_password(password:str, hashed_password_str:str):
    if not hashed_password_str:
        return False
    
    password_bytes = password.encode('utf-8')
  
    hashed_bytes = hashed_password_str.encode('utf-8')

    return bcrypt.checkpw(password_bytes, hashed_bytes)
      

