import hashlib
import streamlit as st
from database import Database

class Auth:
    def __init__(self):
        self.db = Database()

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def login(self, username, password):
        if not username or not password:
            return False
        
        password_hash = self.hash_password(password)
        user = self.db.verify_user(username, password_hash)
        
        if user:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            return True
        return False

    def register(self, username, password):
        if not username or not password:
            return False
        
        password_hash = self.hash_password(password)
        return self.db.create_user(username, password_hash)

    def logout(self):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None

    def is_logged_in(self):
        return st.session_state.get('logged_in', False)
