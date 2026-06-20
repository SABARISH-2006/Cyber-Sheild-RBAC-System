from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from backend_flask.config import Config

# Instantiate database handler
db = SQLAlchemy()

def create_app(config_class=Config):
    """Factory function to build and configure the Flask app instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    from backend_flask.app.routes import auth_bp
    from backend_flask.app.roles import roles_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(roles_bp)
    
    return app
