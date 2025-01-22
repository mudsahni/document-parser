from io import BytesIO

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
def process_pdfs():
    config = current_app.config['CONFIGURATION']
    logger.info("Received processing request")

    token = verify_oidc_token(request)
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        logger.info(f"Received request: {data}")

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

        # downloading file
        file_contents: BytesIO = services.storage_service.download_from_signed_url(process_document_request.url)

        response = services.anthropic_client.process_pdf(
            file_name=process_document_request.name,
            file_content=file_contents,
            prompt=process_document_request.prompt
        )

        logger.info("This is the response")
        logger.info(response)

        # Map the data to the UploadDocumentTask dataclass
        processed_document = ProcessDocumentCallbackRequest(
            id=process_document_request.id,
            name=process_document_request.name,
            type=process_document_request.type,
            parsed_data=response,
            metadata={},
            error=None
        )

        id_token = get_callback_id_token(config.document_store_api)

        # make a call to the callback api
        callback_response = session.post(
            process_document_request.callback_url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {id_token}'
            },
            json=processed_document.to_dict()
        )

        if callback_response.status_code != 200:
            logger.error(f"Callback failed with status {callback_response.status_code}: {callback_response.text}")
            return jsonify({"error": "Callback failed"}), 500

        logger.info(f"Callback response: {callback_response.status_code}")
        return jsonify({"message": "File processed successfully"}), 200

    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return jsonify({"error": "Invalid JSON"}), 400
