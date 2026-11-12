import os
from pathlib import Path
from flask import Flask, send_from_directory
from backend.config import Config
from backend.database import init_db
from backend.routes import api_bp

def create_app(test_config=None):
    app = Flask(__name__, static_folder=str(Config.BASE_DIR / "frontend"), static_url_path="")
    app.config.from_object(Config)
    
    if test_config:
        app.config.update(test_config)
        
    # Initialize DB
    init_db(app.config.get("DATABASE_PATH"))
    
    # Register blueprints
    app.register_blueprint(api_bp)
    
    # Serve Frontend Single Page App
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    print(f"Municipal Grievance Platform listening on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
