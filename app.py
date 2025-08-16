import os
from flask import Flask
from flask_login import LoginManager
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from data_manager import get_user_by_id

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))
