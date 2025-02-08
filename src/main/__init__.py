from flask import Flask
from flask_cors import CORS

from .config.Configuration import Configuration
from .controllers.UploadDocumentController import upload_document_bp
from .controllers.ProcessDocumentController import process_document_bp
from .services import services
from .utils.request_utls import get_request_session

config: Configuration = Configuration()

def create_app():
    app: Flask = Flask(__name__)
    app.config.from_object(config)
    app.config.update({
        'CONFIGURATION': config
    })

    # Initialize extensions
    CORS(app)

    services.init_storage_service(app.config['CONFIGURATION'].bucket_name)
    services.init_anthropic_client(app.config['CONFIGURATION'].anthropic_api_key)
    services.init_gemini_client(app.config['CONFIGURATION'].gemini_api_key)

    app.register_blueprint(upload_document_bp, url_prefix='/api/v1/upload')
    app.register_blueprint(process_document_bp, url_prefix='/api/v1/process')

    return app
