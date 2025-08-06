# backend/run.py
from flask import Flask
from flask_cors import CORS
from api.routes import api # Import the blueprint

def create_app():
    app = Flask(__name__)
    
    # CORS is required to allow your React frontend (on a different port)
    # to make requests to this Flask backend.
    CORS(app) 
    
    app.register_blueprint(api, url_prefix='/api')
    
    return app

if __name__ == '__main__':
    app = create_app()
    # Run in debug mode for development. Use a production server like Gunicorn for deployment.
    app.run(debug=True)