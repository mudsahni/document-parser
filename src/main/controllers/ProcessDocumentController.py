from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import threading
import time

# Create a thread pool at module level
executor = ThreadPoolExecutor(max_workers=10)

from flask import Blueprint, request, jsonify, current_app

from . import session
from ..services import services
from ..logs.logger import setup_logger
from ..models.dto.response.ProcessDocumentCallbackRequest import ProcessDocumentCallbackRequest
from ..models.dto.request.ProcessDocumentRequest import ProcessDocumentRequest
from ..security.OIDC import verify_oidc_token, get_callback_id_token

process_document_bp = Blueprint('process_document', __name__)
logger = setup_logger(__name__)


@process_document_bp.route('', methods=['POST'])
def process_files():
    config = current_app.config['CONFIGURATION']
    logger.info("Received processing request")

    # Get the optional 'ai' query parameter
    ai_type = request.args.get('ai', None)
    logger.info(f"AI type requested: {ai_type}")

    token = verify_oidc_token(request)
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

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
    """Process document asynchronously in a separate thread"""
    try:
        # Download file
        file_contents = services.storage_service.download_from_signed_url(process_document_request.url)

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

        # Get callback token
        id_token = get_callback_id_token(config.document_store_api)

        # Send callback with retry logic
        send_callback_with_retry(
            process_document_request.callback_url,
            id_token,
            processed_document.to_dict()
        )

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")

        # Attempt to send error callback
        try:
            error_document = ProcessDocumentCallbackRequest(
                id=process_document_request.id,
                name=process_document_request.name,
                type=process_document_request.type,
                parsed_data=None,
                metadata={},
                error=str(e)
            )

            id_token = get_callback_id_token(config.document_store_api)

            send_callback_with_retry(
                process_document_request.callback_url,
                id_token,
                error_document.to_dict()
            )
        except Exception as callback_error:
            logger.error(f"Failed to send error callback: {str(callback_error)}")


def send_callback_with_retry(url, token, data, max_retries=3, initial_backoff=1):
    """Send callback with exponential backoff retry logic"""
    retry_count = 0
    backoff = initial_backoff

    while retry_count < max_retries:
        try:
            response = session.post(
                url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                },
                json=data,
                timeout=30  # 30 second timeout
            )

            if response.status_code == 200:
                logger.info(f"Callback successful with status {response.status_code}")
                return

            logger.warning(f"Callback attempt {retry_count + 1} failed with status {response.status_code}")
        except Exception as e:
            logger.warning(f"Callback attempt {retry_count + 1} failed with error: {str(e)}")

        # Exponential backoff before retry
        retry_count += 1
        if retry_count < max_retries:
            time.sleep(backoff)
            backoff *= 2

    logger.error(f"All callback attempts failed after {max_retries} retries")
