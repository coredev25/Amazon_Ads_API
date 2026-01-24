#!/usr/bin/env python3
import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], bcrypt__rounds=12, deprecated='auto')

def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_hash = hashlib.sha256(password_bytes).hexdigest()
        return pwd_context.hash(password_hash)
    return pwd_context.hash(password)

# Generate hash for password 'password123'
hashed = hash_password('password123')
print('New password hash for user vohuy:')
print(hashed)
print()
print('SQL to update database:')
print("UPDATE users SET password_hash = '" + hashed + "' WHERE username = 'vohuy';")
