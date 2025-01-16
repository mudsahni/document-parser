from flask import Flask
from flask_cors import CORS

from .controllers.UploadDocumentController import upload_documents_bp


def create_app():
    app: Flask = Flask(__name__)

    # Initialize extensions
    CORS(app)

    app.register_blueprint(upload_documents_bp, url_prefix='/api/v1/')

    return app
