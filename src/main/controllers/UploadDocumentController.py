import functools
import json
import os
from io import BytesIO

from firebase_admin import credentials, initialize_app, auth
from flask import Blueprint, request, jsonify
from google.cloud import secretmanager

from ..logs.logger import setup_logger
from ..models.dto.request.UploadDocumentRequest import UploadDocumentRequest
from ..services.StorageService import StorageService

upload_documents_bp = Blueprint('upload_documents', __name__)
logger = setup_logger(__name__)

storage_service = StorageService("ms_document_store_one")


def get_firebase_credentials(env: str) -> str:
    if env == 'dev':
        with open("../secrets/firebase-service-account.json", 'r') as creds:
            return creds.read()
    else:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/muditsahni-bb2eb/secrets/firebase-sa-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode('UTF-8')


@upload_documents_bp.route('/health', methods=['GET'])
def health_check():
    logger.info("Health check")
    return jsonify({"message": "Upload Document Service is healthy"}), 200


# Initialize Firebase Admin SDK
cred = credentials.Certificate(json.loads(get_firebase_credentials(os.getenv("ENV", "dev"))))
initialize_app(cred)


# Decorator for Firebase token authentication
def firebase_auth_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract Authorization header
        auth_header = request.headers.get('Authorization', None)
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authorization header missing or invalid"}), 401

        token = auth_header.split('Bearer ')[1]

        try:
            # Verify the token with Firebase
            decoded_token = auth.verify_id_token(token)
            request.user = decoded_token  # Attach user info to the request
        except Exception as e:
            return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

        return f(*args, **kwargs)

    return decorated_function


@upload_documents_bp.route("/hello", methods=['GET'])
def hello():
    return jsonify({"message": "Hello, World!"}), 200


@upload_documents_bp.route('/upload', methods=['POST'])
# @firebase_auth_required  # Apply authentication to this route
def process_pdfs():
    try:
        logger.info("Received request")
        import base64

        # Get JSON data
        data = request.get_json()
        file_bytes = base64.b64decode(data['file'])

        # Convert base64 string to bytes if needed
        # file_bytes = data['file'] if isinstance(data['file'], bytes) else bytes(data['file'])
        # Create a file-like object
        file = BytesIO(file_bytes)

        # Map the data to the UploadDocumentTask dataclass
        task = UploadDocumentRequest(
            uploadPath=data['upload_path'],
            fileName=data['file_name'],
            collectionId=data['collection_id'],
            tenantId=data['tenant_id'],
            userId=data['user_id'],
            fileType=data['file_type'],
            fileSize=data['file_size'] or len(file_bytes),
            file=file,
            callbackUrl=data['callback_url']
        )

        logger.info(f"Received upload task for file: {task.fileName}")
        # Map the data to the UploadDocumentTask dataclass

        logger.info(f"Uploading file: {task.fileName}")
        storage_service.upload_files(task.fileName, task.uploadPath, [task.file])
        logger.info("File uploaded successfully")
        return jsonify({"message": "Upload task received"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
