from flask import Flask
from config import Config
from models import db
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)

    with app.app_context():
        db.create_all()
    
    @app.route('/')
    def index():
        return "<h1>Expense Tracker API</h1><p>Setup complete. Ready for next steps.</p>"
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
    