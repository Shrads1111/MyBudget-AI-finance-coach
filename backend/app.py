import os
# CRITICAL: Must be set before ANY google/firebase/protobuf imports.
# Python 3.14 removed support for C-extension metaclasses (tp_new).
# This forces protobuf to use its pure-Python fallback implementation.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
# FirebaseService will be imported lazily within create_app to avoid import-time failures
from middleware.error_handler import register_error_handlers

# Configure central logging
def setup_logging():
    log_dir = Config.LOG_DIR
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
        
    log_file = Config.LOG_FILE
    
    # Configure root logger
    logging.basicConfig(level=logging.INFO)
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=5)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] - %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Add handler to Flask's parent logger
    logging.getLogger('').addHandler(file_handler)

def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Setup logs
    setup_logging()
    
    # Initialize Firebase singleton
    try:
        from services.firebase_service import FirebaseService
        FirebaseService.initialize()
    except Exception as e:
        app.logger.critical(f"Failed to initialize Firebase Service: {str(e)}")

    # Register centralized exception handlers
    register_error_handlers(app)

    # Import blueprints
    from routes.user_routes import user_bp
    from routes.expense_routes import expense_bp
    from routes.budget_routes import budget_bp
    from routes.savings_routes import savings_bp
    from routes.analytics_routes import analytics_bp
    from routes.group_routes import group_bp
    from routes.notification_routes import notification_bp
    from routes.ai_routes import ai_bp
    from routes.health_score_routes import health_score_bp
    from routes.goal_planner_routes import goal_planner_bp
    from routes.pattern_routes import pattern_bp
    from routes.report_routes import report_bp
    from routes.simulator_routes import simulator_bp
    from routes.account_routes import account_bp
    from routes.category_routes import category_bp
    from routes.health_routes import health_bp
    from routes.auth_routes import auth_bp
    from routes.recurring_routes import recurring_bp
    from routes.voice_routes import voice_bp
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(savings_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(health_score_bp)
    app.register_blueprint(goal_planner_bp)
    app.register_blueprint(pattern_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(auth_bp)


    @app.route('/health', methods=['GET'])
    def health_check():
        try:
            from services.firebase_service import FirebaseService
            firebase_status = "initialized" if FirebaseService._initialized else "failed"
        except Exception:
            firebase_status = "failed"
        return jsonify({
            "status": "healthy",
            "firebase": firebase_status
        }), 200

    return app

if __name__ == '__main__':
    app = create_app()
    port = Config.PORT
    app.logger.info(f"Starting MyBudget backend on port {port} under {Config.FLASK_ENV} mode")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
