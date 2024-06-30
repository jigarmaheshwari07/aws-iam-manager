from flask import Flask
from app.models import db
from app.routes import init_routes
from app.aws_analyzer import init_aws_analyzer
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def create_app():
    app = Flask(__name__)
    
    # Load configuration from environment variables or use default values
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///aws_roles.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey')
    
    db.init_app(app)
    
    # Initialize routes and AWS analyzer
    init_routes(app)
    init_aws_analyzer(app)
    
    return app
