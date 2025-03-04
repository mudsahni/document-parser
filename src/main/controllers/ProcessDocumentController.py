from flask import Blueprint, request, jsonify, current_app
from io import BytesIO
import threading
import requests
import ssl
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

from . import session
from ..services import services
from ..logs.logger import setup_logger
from ..models.dto.response.ProcessDocumentCallbackRequest import ProcessDocumentCallbackRequest
from ..models.dto.request.ProcessDocumentRequest import ProcessDocumentRequest
from ..security.OIDC import verify_oidc_token, get_callback_id_token, get_callback_id_token_secure


# Create a custom SSL adapter with compatibility for both LibreSSL and OpenSSL
class CompatibleSSLAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        # No custom cipher specification - use system defaults

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx,
            **pool_kwargs
        )

# Thread-local storage for session objects
thread_local = threading.local()


# Get a thread-specific session with proper SSL configuration
def get_thread_session():
    if not hasattr(thread_local, "session"):
        session = requests.Session()
        adapter = CompatibleSSLAdapter()
        session.mount("https://", adapter)
        thread_local.session = session
    return thread_local.session


# Create thread pool
executor = ThreadPoolExecutor(max_workers=10)

process_document_bp = Blueprint('process_document', __name__)
logger = setup_logger(__name__)


@process_document_bp.route('', methods=['POST'])
def process_files():
    config = current_app.config['CONFIGURATION']
    logger.info("Received processing request")

    # Get the optional 'ai' query parameter
    ai_type = request.args.get('ai', None)
    logger.info(f"AI type requested: {ai_type}")

    # token = verify_oidc_token(request)
    # if not token:
    #     return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        logger.info(f"Received request: {data}")

        # Create request object
        process_document_request = ProcessDocumentRequest(
            id=data['id'],
            name=data['name'],
            type=data['type'],
            url=data['url'],
            prompt=data['prompt'],
            file_type=data['file_type'],
            tenant_id=data['tenant_id'],
            collection_id=data['collection_id'],
            callback_url=data['callback_url']
        )

        # Submit processing job to thread pool and return immediately
        executor.submit(
            process_document_async,
            process_document_request,
            ai_type,
            config
        )

        # Return immediately without waiting
        return jsonify({"message": "Document processing started", "status": "processing"}), 202

    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return jsonify({"error": "Invalid JSON"}), 400


def process_document_async(process_document_request, ai_type, config):
    """Process document asynchronously with proper SSL handling"""
    try:
        # Get thread-local session with proper SSL configuration
        thread_session = get_thread_session()

        # Download file using secure session
        file_contents = download_file(thread_session, process_document_request.url)

        # Select the appropriate model function
        model_function = services.anthropic_client.process_file
        if ai_type is not None and ai_type == 'GEMINI':
            logger.info("Processing with Gemini")
            model_function = services.gemini_client.process_file
        else:
            logger.info("Processing with Anthropic")

        # Process with primary model with fallback
        try:
            response = model_function(
                file_name=process_document_request.name,
                file_content=file_contents.getvalue(),
                prompt=process_document_request.prompt
            )
        except Exception as e:
            logger.error(f"Error processing with primary model: {str(e)}")

            # Switch to fallback model
            if ai_type is not None and ai_type == 'GEMINI':
                logger.info("Falling back to Anthropic")
                model_function = services.anthropic_client.process_file
            else:
                logger.info("Falling back to Gemini")
                model_function = services.gemini_client.process_file

            response = model_function(
                file_name=process_document_request.name,
                file_content=file_contents.getvalue(),
                prompt=process_document_request.prompt
            )

        # Prepare callback data
        processed_document = ProcessDocumentCallbackRequest(
            id=process_document_request.id,
            name=process_document_request.name,
            type=process_document_request.type,
            parsed_data=response,
            metadata={},
            error=None
        )

        # Get callback token using secure session
        id_token = get_callback_id_token_secure(thread_session, config.document_store_api)

        # Send callback with secure session
        callback_response = thread_session.post(
            process_document_request.callback_url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {id_token}'
            },
            json=processed_document.to_dict(),
            timeout=60
        )

        if callback_response.status_code != 200:
            logger.error(f"Callback failed with status {callback_response.status_code}: {callback_response.text}")
        else:
            logger.info(f"Callback successful with status {callback_response.status_code}")

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")

        # Attempt to send error callback
        try:
            thread_session = get_thread_session()

            error_document = ProcessDocumentCallbackRequest(
                id=process_document_request.id,
                name=process_document_request.name,
                type=process_document_request.type,
                parsed_data=None,
                metadata={},
                error=str(e)
            )

            id_token = get_callback_id_token_secure(thread_session, config.document_store_api)

            thread_session.post(
                process_document_request.callback_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {id_token}'
                },
                json=error_document.to_dict(),
                timeout=60
            )
        except Exception as callback_error:
            logger.error(f"Failed to send error callback: {str(callback_error)}")


def download_file(session, url):
    """Download a file using the provided session with proper error handling"""
    try:
        response = session.get(url, timeout=60)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise
