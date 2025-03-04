from io import BytesIO
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import certifi
import requests
from flask import Blueprint, request, jsonify, current_app

from . import session
from ..utils.request_utls import get_request_session
from ..services import services
from ..logs.logger import setup_logger
from ..models.dto.response.ProcessDocumentCallbackRequest import ProcessDocumentCallbackRequest
from ..models.dto.request.ProcessDocumentRequest import ProcessDocumentRequest
from ..security.OIDC import verify_oidc_token, get_callback_id_token

process_document_bp = Blueprint('process_document', __name__)
logger = setup_logger(__name__)

# Create a thread pool for handling background processing
executor = ThreadPoolExecutor(max_workers=4)  # Adjust based on your CPU cores and memory


def process_and_callback(process_document_request, ai_type, config):
    """Background task to handle file processing and callback"""
    try:
        logger.info(f"Processing document in background: {process_document_request.id}")

        # Downloading file
        file_contents: BytesIO = services.storage_service.download_from_signed_url(process_document_request.url)

        # Select the appropriate model
        model_function = services.anthropic_client.process_file
        if ai_type is not None and ai_type == 'GEMINI':
            logger.info("Processing with Gemini")
            model_function = services.gemini_client.process_file
        else:
            logger.info("Processing with Anthropic")

        # Process the file with the selected model
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

        # Get ID token for callback
        id_token = get_callback_id_token(config.document_store_api)
        # Create a new session for this thread
        local_session = get_request_session()

        # Make callback request
        callback_response = local_session.post(
            process_document_request.callback_url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {id_token}'
            },
            json=processed_document.to_dict()
        )

        if callback_response.status_code != 200:
            logger.error(
                f"Callback failed for {process_document_request.id} with status {callback_response.status_code}: {callback_response.text}")
        else:
            logger.info(f"Callback successful for {process_document_request.id}")

    except Exception as e:
        logger.error(f"Error processing document {process_document_request.id}: {str(e)}")

        # Attempt to send error to callback if possible
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
            error_session = get_request_session()

            error_session.post(
                process_document_request.callback_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {id_token}'
                },
                json=error_document.to_dict()
            )
        except Exception as callback_error:
            logger.error(f"Failed to send error callback for {process_document_request.id}: {str(callback_error)}")


@process_document_bp.route('', methods=['POST'])
def process_files():
    config = current_app.config['CONFIGURATION']
    logger.info("Received processing request")

    # Get the optional 'ai' query parameter
    ai_type = request.args.get('ai', None)
    logger.info(f"AI type requested: {ai_type}")

    # Verify authentication
    token = verify_oidc_token(request)
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        logger.info(f"Received request: {data}")

        # Parse request data
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

        # Submit the processing task to our thread pool
        executor.submit(
            process_and_callback,
            process_document_request,
            ai_type,
            config
        )

        # Return immediately with a 202 Accepted status
        return jsonify({
            "message": "Request accepted for processing",
            "id": process_document_request.id
        }), 202

    except Exception as e:
        logger.error(f"Error parsing request: {str(e)}")
        return jsonify({"error": str(e)}), 400