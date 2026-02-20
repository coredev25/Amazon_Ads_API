"""
Authentication and User Management Module
Handles user login, signup, session management, and JWT tokens
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
import logging

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError, InvalidTokenError
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# Password hashing
# Use bcrypt with rounds=12 for security
# The version warning is safe to ignore - it's a compatibility check
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=12,
    deprecated="auto"
)

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security
security = HTTPBearer()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UserSignup(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    last_login: Optional[str]
    created_at: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# ============================================================================
# DATABASE DEPENDENCY
# ============================================================================

def get_db():
    """Database dependency"""
    # Import here to avoid circular imports
    # Check both 'dashboard.api.main' and '__main__' modules to handle
    # the case where the server is run directly via 'python dashboard/api/main.py'
    # (module name is __main__) vs 'uvicorn dashboard.api.main:app' (module name is dashboard.api.main)
    import sys
    
    db_connector = None
    
    # Try the standard module path first (uvicorn dashboard.api.main:app from project root)
    try:
        from dashboard.api.main import db_connector as _db
        db_connector = _db
    except (ImportError, AttributeError):
        pass
    
    # Try short module path (uvicorn api.main:app from dashboard/ directory)
    if db_connector is None:
        try:
            from api.main import db_connector as _db
            db_connector = _db
        except (ImportError, AttributeError):
            pass
    
    # Check __main__ module (when run directly with python)
    if db_connector is None:
        try:
            main_module = sys.modules.get('__main__')
            if main_module and hasattr(main_module, 'db_connector'):
                db_connector = main_module.db_connector
        except (AttributeError, TypeError):
            pass
    
    # Check all loaded modules for api.main
    if db_connector is None:
        for mod_name in ['api.main', 'dashboard.api.main']:
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, 'db_connector'):
                db_connector = mod.db_connector
                break
    
    if db_connector is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection not available"
        )
    
    return db_connector

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _preprocess_password(password: str) -> str:
    """
    Preprocess password for bcrypt (bcrypt has a 72-byte limit)
    If password is longer than 72 bytes, hash it with SHA-256 first
    """
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Hash with SHA-256 to reduce to 32 bytes (64 hex chars)
        password_hash = hashlib.sha256(password_bytes).hexdigest()
        return password_hash
    return password


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt for secure storage
    
    This function is used during SIGNUP:
    1. Preprocesses password if longer than 72 bytes (SHA-256)
    2. Hashes the password with bcrypt (12 rounds)
    3. Returns the bcrypt hash string to store in database
    
    The hash includes: algorithm, cost factor, salt, and hash value.
    Example: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEkKd."
    
    Args:
        password: Plain text password from user input
        
    Returns:
        str: Bcrypt hash string (stored in database as password_hash)
        
    Note:
        The plain password is NEVER stored in the database, only the hash.
    """
    processed_password = _preprocess_password(password)
    return pwd_context.hash(processed_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the stored hash from database
    
    This function is used during LOGIN:
    1. Preprocesses plain password if needed
    2. Uses bcrypt's verify() which internally:
       - Extracts the salt from the stored hash
       - Hashes the plain password with that salt
       - Compares the result with the stored hash
    3. Returns True if they match, False otherwise
    
    Args:
        plain_password: Plain text password from user input
        hashed_password: Stored bcrypt hash from database (password_hash column)
        
    Returns:
        bool: True if password matches the hash, False otherwise
        
    Note:
        This uses bcrypt's verify() function which handles the hashing and
        comparison internally. We don't manually hash the password here - bcrypt
        does it using the salt from the stored hash, then compares the results.
    """
    processed_password = _preprocess_password(plain_password)
    return pwd_context.verify(processed_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (PyJWTError, InvalidTokenError) as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

def get_user_by_username(db_connector, username: str) -> Optional[dict]:
    """Get user by username from database"""
    try:
        with db_connector.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, email, username, password_hash, role,
                           is_active, is_verified, last_login, created_at
                    FROM users
                    WHERE username = %s
                """, (username,))
                return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting user by username: {e}")
        return None


def get_user_by_email(db_connector, email: str) -> Optional[dict]:
    """Get user by email from database"""
    try:
        with db_connector.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, email, username, password_hash, role,
                           is_active, is_verified, last_login, created_at
                    FROM users
                    WHERE email = %s
                """, (email,))
                return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None


def get_user_by_username(db_connector, username: str) -> Optional[dict]:
    """
    Get user by username or email from database
    
    This function checks both username and email fields to allow
    users to login with either username or email address.
    """
    try:
        with db_connector.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, email, username, password_hash, role,
                           is_active, is_verified, last_login, created_at
                    FROM users
                    WHERE username = %s OR email = %s
                """, (username, username))
                return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting user by username or email: {e}")
        return None


def get_user_by_id(db_connector, user_id: int) -> Optional[dict]:
    """Get user by ID from database"""
    try:
        with db_connector.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, email, username, role,
                           is_active, is_verified, last_login, created_at
                    FROM users
                    WHERE id = %s
                """, (user_id,))
                return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None


def create_user(db_connector, user_data: UserSignup) -> dict:
    """
    Create a new user in the database
    
    Process:
    1. Validate input (email, username, password)
    2. Check if user already exists (username or email)
    3. Hash the password using bcrypt
    4. Store user information in database with hashed password
    
    Args:
        db_connector: Database connector instance
        user_data: UserSignup model with user information
        
    Returns:
        dict: Created user data (without password_hash)
        
    Raises:
        HTTPException: If user already exists or database error
    """
    try:
        logger.info(f"Creating new user: {user_data.username}")
        
        # Step 1: Check if user already exists (username)
        existing_user = get_user_by_username(db_connector, user_data.username)
        if existing_user:
            logger.warning(f"Signup failed: Username '{user_data.username}' already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Step 2: Check if email already exists
        existing_email = get_user_by_email(db_connector, user_data.email)
        if existing_email:
            logger.warning(f"Signup failed: Email '{user_data.email}' already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Step 3: Hash the password before storing in database
        logger.debug("Hashing password for new user")
        password_hash = hash_password(user_data.password)
        logger.debug("Password hashed successfully")
        
        # Step 4: Insert user into database with hashed password
        try:
            with db_connector.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        INSERT INTO users (email, username, password_hash, role, is_active, is_verified)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, email, username, role, is_active, is_verified, created_at
                    """, (
                        user_data.email,
                        user_data.username,
                        password_hash,  # Store hashed password, NOT plain text
                        'user',  # Default role
                        True,    # is_active
                        False    # is_verified (can be changed to True for auto-verification)
                    ))
                    conn.commit()
                    new_user = cursor.fetchone()
                    logger.info(f"User created successfully: {user_data.username} (ID: {new_user['id']})")
                    return new_user
        except psycopg2.IntegrityError as e:
            # Handle database constraint violations (race condition fallback)
            error_msg = str(e).lower()
            if 'username' in error_msg or 'unique constraint' in error_msg:
                logger.warning(f"Signup failed: Username '{user_data.username}' already exists (database constraint)")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            elif 'email' in error_msg:
                logger.warning(f"Signup failed: Email '{user_data.email}' already exists (database constraint)")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            else:
                logger.error(f"Database integrity error during signup: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this information already exists"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


def authenticate_user(db_connector, username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user with username or email and password
    
    Process:
    1. Retrieve user from database by username OR email
    2. Hash the provided password and compare with stored password_hash
    3. If passwords match, check if account is active
    4. Update last_login timestamp
    5. Return user data if authentication successful
    
    Args:
        db_connector: Database connector instance
        username: Username or email address to authenticate
        password: Plain text password to verify
        
    Returns:
        dict: User data if authentication successful, None otherwise
        
    Raises:
        HTTPException: If account is inactive
    """
    logger.info(f"Attempting authentication for: {username}")
    
    # Step 1: Get user from database by username OR email
    user = get_user_by_username(db_connector, username)
    if not user:
        logger.warning(f"Login failed: User '{username}' not found")
        return None
    
    # Step 2: Hash the provided password and verify against stored password_hash
    logger.debug("Verifying password against stored hash")
    password_matches = verify_password(password, user['password_hash'])
    
    if not password_matches:
        logger.warning(f"Login failed: Incorrect password for user '{username}'")
        return None
    
    logger.debug("Password verified successfully")
    
    # Step 3: Check if account is active
    if not user['is_active']:
        logger.warning(f"Login failed: Account '{username}' is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Step 4: Update last login timestamp
    try:
        with db_connector.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (user['id'],))
                conn.commit()
        logger.debug(f"Last login updated for user '{username}'")
    except Exception as e:
        logger.warning(f"Failed to update last login: {e}")
    
    logger.info(f"Authentication successful for user: {username}")
    return user


def get_current_user(
    db_connector = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """Dependency to get the current authenticated user"""
    
    token = credentials.credentials
    payload = decode_token(token)
    
    # JWT 'sub' claim must be a string, so we convert it back to int
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert string to int (JWT requires sub to be string)
    try:
        user_id: int = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_by_id(db_connector, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return UserResponse(
        id=user['id'],
        email=user['email'],
        username=user['username'],
        role=user['role'],
        is_active=user['is_active'],
        is_verified=user['is_verified'],
        last_login=user['last_login'].isoformat() if user['last_login'] else None,
        created_at=user['created_at'].isoformat()
    )


def require_role(required_role: str):
    """Dependency to require a specific role"""
    def role_checker(user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if user.role != required_role and user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return role_checker


def change_password(db_connector, user_id: int, current_password: str, new_password: str) -> bool:
    """Change user password"""
    try:
        # Get current user
        with db_connector.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT password_hash FROM users WHERE id = %s
                """, (user_id,))
                user = cursor.fetchone()
                
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                
                # Verify current password
                if not verify_password(current_password, user['password_hash']):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Current password is incorrect"
                    )
                
                # Hash new password and update
                new_password_hash = hash_password(new_password)
                cursor.execute("""
                    UPDATE users
                    SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (new_password_hash, user_id))
                conn.commit()
                
                return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

