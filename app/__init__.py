from flask import Flask
from app.models import db
from app.routes import init_routes
from app.aws_analyzer import init_aws_analyzer
from app.config import Config


def create_app():
    app = Flask(__name__)
    
    # Load configuration from Config class
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    # Initialize routes and AWS analyzer
    init_routes(app)
    init_aws_analyzer(app)
    
    return app
