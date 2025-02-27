from io import BytesIO

from flask import Blueprint, request, jsonify
from google.auth.transport import requests
import requests as r
from google.oauth2 import id_token
from google.oauth2.id_token import fetch_id_token
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from ..config.Configuration import Configuration
from ..logs.logger import setup_logger
from ..models.dto.request.UploadDocumentRequest import UploadDocumentRequest
from ..security.OIDC import verify_oidc_token
from ..services.StorageService import StorageService

upload_document_bp = Blueprint('upload_document', __name__)
logger = setup_logger(__name__)

config = Configuration()
storage_service = StorageService(config.bucket_name)


@upload_document_bp.route('/health', methods=['GET'])
def health_check():
    logger.info("Health check")
    return jsonify({"message": "Upload Document Service is healthy"}), 200


@upload_document_bp.route("/hello", methods=['GET'])
def hello():
    return jsonify({"message": "Hello, World!"}), 200


@upload_document_bp.route('', methods=['POST'])
# @firebase_auth_required  # Apply authentication to this route
def upload_pdfs():
    logger.info("Received request")

    token = verify_oidc_token(request)
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    try:
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
            documentId=data['document_id'],
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
        storage_service.upload_file(task.fileName, task.uploadPath, task.file)
        logger.info("File uploaded successfully")

        # Get ID token for the callback
        auth_req = requests.Request()
        id_token = fetch_id_token(auth_req, config.document_store_api)

        logger.info(f"This is the token: {id_token}")
        session = r.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        # make a call to the callback api
        callback_response = session.post(
            task.callbackUrl,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {id_token}'
            },
            json={
                "tenantId": task.tenantId,
                "userId": task.userId,
                "collectionId": task.collectionId,
                "documentId": task.documentId,
                "uploadPath": task.uploadPath + "/" + task.fileName,
                "status": "SUCCESS",
                "error": None
            }
        )

        if callback_response.status_code != 200:
            logger.error(f"Callback failed with status {callback_response.status_code}: {callback_response.text}")
            return jsonify({"error": "Callback failed"}), 500

        logger.info(f"Callback response: {callback_response.status_code}")
        return jsonify({"message": "File uploaded successfully"}), 200
    except Exception as e:
        logger.error(f"Error making callback request: {str(e)}")
        return jsonify({"error": str(e)}), 500
