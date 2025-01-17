import functools
import json
import os

from firebase_admin import credentials, initialize_app, auth
from flask import Blueprint, request, jsonify
from google.cloud import secretmanager
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

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
@firebase_auth_required  # Apply authentication to this route
def process_pdfs():
    try:
        # Ensure all necessary fields are present
        required_fields = [
            "upload_path", "file_name", "collection_id", "tenant_id",
            "user_id", "file_type", "file_size", "callback_url"
        ]

        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        # Check if any required fields are missing in the form data
        missing_fields = [field for field in required_fields if field not in request.form]
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

        uploaded_file: FileStorage = request.files.get("file")
        if not uploaded_file:
            return jsonify({"error": "Missing 'file' field in the form data"}), 400

        upload_path = request.form.get("upload_path")
        file_name = secure_filename(uploaded_file.filename)
        collection_id = request.form.get("collection_id")
        tenant_id = request.form.get("tenant_id")
        user_id = request.form.get("user_id")
        file_type = request.form.get("file_type")
        file_size = int(request.form.get("file_size"))
        callback_url = request.form.get("callback_url")

        logger.info(f"Received upload task for file: {file_name}")
        # Map the data to the UploadDocumentTask dataclass
        task = UploadDocumentRequest(
            uploadPath=upload_path,
            fileName=file_name,
            collectionId=collection_id,
            tenantId=tenant_id,
            userId=user_id,
            fileType=file_type,  # Optionally validate against FileType Enum
            fileSize=file_size,
            file=uploaded_file,  # Assuming file is sent as a Base64-encoded string
            callbackUrl=callback_url
        )

        logger.info(f"Uploading file: {task.fileName}")
        storage_service.upload_files(task.uploadPath, [task.file])
        logger.info("File uploaded successfully")
        return jsonify({"message": "Upload task received"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
