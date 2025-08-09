import streamlit as st
import hashlib
import sqlite3
import os
from datetime import datetime, timedelta
import secrets

class AuthManager:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the user database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return salt + password_hash.hex()
    
    def verify_password(self, password, stored_hash):
        """Verify password against stored hash"""
        salt = stored_hash[:32]
        stored_password_hash = stored_hash[32:]
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_hash.hex() == stored_password_hash
    
    def create_user(self, username, email, password):
        """Create a new user account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                return False, "Username or email already exists"
            
            # Create new user
            password_hash = self.hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            ''', (username, email, password_hash))
            
            conn.commit()
            conn.close()
            return True, "Account created successfully"
        
        except Exception as e:
            return False, f"Error creating account: {str(e)}"
    
    def authenticate_user(self, username, password):
        """Authenticate user login"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, password_hash, is_active
                FROM users WHERE username = ? OR email = ?
            ''', (username, username))
            
            user = cursor.fetchone()
            if not user:
                return False, None, "Invalid username or password"
            
            user_id, username, email, stored_hash, is_active = user
            
            if not is_active:
                return False, None, "Account is deactivated"
            
            if not self.verify_password(password, stored_hash):
                return False, None, "Invalid username or password"
            
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            return True, {"id": user_id, "username": username, "email": email}, "Login successful"
        
        except Exception as e:
            return False, None, f"Login error: {str(e)}"
    
    def create_session(self, user_id):
        """Create a new session for authenticated user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=7)  # 7 days expiry
            
            cursor.execute('''
                INSERT INTO sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            
            conn.commit()
            conn.close()
            
            return session_token
        
        except Exception as e:
            st.error(f"Session creation error: {str(e)}")
            return None
    
    def validate_session(self, session_token):
        """Validate session token"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.user_id, u.username, u.email
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP
            ''', (session_token,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                user_id, username, email = result
                return True, {"id": user_id, "username": username, "email": email}
            
            return False, None
        
        except Exception as e:
            return False, None
    
    def logout_user(self, session_token):
        """Logout user by invalidating session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            return False

def show_login_page():
    """Display login page"""
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username or Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if username and password:
                auth_manager = AuthManager()
                success, user_data, message = auth_manager.authenticate_user(username, password)
                
                if success:
                    session_token = auth_manager.create_session(user_data["id"])
                    if session_token:
                        st.session_state.authenticated = True
                        st.session_state.user = user_data
                        st.session_state.session_token = session_token
                        st.success(message)
                        st.rerun()
                    else:
                        st.error("Failed to create session")
                else:
                    st.error(message)
            else:
                st.error("Please fill in all fields")

def show_signup_page():
    """Display signup page"""
    st.title("📝 Sign Up")
    
    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Create Account")
        
        if submit:
            if username and email and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    auth_manager = AuthManager()
                    success, message = auth_manager.create_user(username, email, password)
                    
                    if success:
                        st.success(message)
                        st.info("Please login with your new account")
                    else:
                        st.error(message)
            else:
                st.error("Please fill in all fields")

def check_authentication():
    """Check if user is authenticated"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'session_token' in st.session_state and st.session_state.session_token:
        auth_manager = AuthManager()
        valid, user_data = auth_manager.validate_session(st.session_state.session_token)
        
        if valid:
            st.session_state.authenticated = True
            st.session_state.user = user_data
        else:
            st.session_state.authenticated = False
            if 'session_token' in st.session_state:
                del st.session_state.session_token
    
    return st.session_state.authenticated

def logout():
    """Logout current user"""
    if 'session_token' in st.session_state:
        auth_manager = AuthManager()
        auth_manager.logout_user(st.session_state.session_token)
        del st.session_state.session_token
    
    st.session_state.authenticated = False
    if 'user' in st.session_state:
        del st.session_state.user
    
    st.rerun()
