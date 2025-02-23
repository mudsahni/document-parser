import base64
import json
from typing import Optional, Dict, List

import anthropic
from anthropic import Anthropic

from ..config.constants.MimeTypes import MIME_TYPES
from ..logs.logger import setup_logger

def build_anthropic_api_pdf_parsing_request(
        pdf: str,
        prompt: str,
        media_type: str
) -> Dict:
    return {
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": pdf
                }
            },
            {
                "type": "text",
                "text": prompt
            }
        ]
    }


class AnthropicClient:

    # Headers for different file types
    FILE_HEADERS: Dict[str, tuple] = {
        'application/pdf': ('anthropic-beta', 'pdfs-2024-09-25'),
        'image/jpeg': ('anthropic-beta', 'images-2024-09-25'),
        'image/png': ('anthropic-beta', 'images-2024-09-25'),
        'image/tiff': ('anthropic-beta', 'images-2024-09-25')
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = setup_logger(__name__)
        self.client: Anthropic = anthropic.Anthropic(api_key=api_key)
        self.MAX_TOKENS = 8192
        self.ANTHROPIC_PDF_HEADER_KEY = "anthropic-beta"
        self.ANTHROPIC_PDF_HEADER_VALUE = "pdfs-2024-09-25"

    def _get_mime_type(self, file_name: str) -> Optional[str]:
        """
        Determine MIME type based on file extension
        """
        extension = file_name.lower().split('.')[-1]
        mime_type = MIME_TYPES.get(extension)

        if not mime_type:
            self.logger.warning(f"Unsupported file format: {extension}")

        return mime_type

    def _get_file_header(self, mime_type: str) -> Optional[tuple]:
        """
        Get the appropriate header for the file type
        """
        return self.FILE_HEADERS.get(mime_type)

    def process_file(
            self,
            file_name: str,
            file_content: bytes,
            prompt: str
    ) -> str:
        """
        Process any supported file format (PDF, JPEG, PNG, TIFF)
        """

        mime_type = self._get_mime_type(file_name)
        if not mime_type:
            raise ValueError(f"Unsupported file format for file: {file_name}")

        header = self._get_file_header(mime_type)
        if not header:
            raise ValueError(f"No header configuration for MIME type: {mime_type}")

        try:
            base64_content = base64.b64encode(file_content).decode()

            if base64_content is None:
                # TODO: Change to specific exception
                raise ValueError("Could not encode file content to base64")

            messages: List[Dict] = [build_anthropic_api_pdf_parsing_request(base64_content, prompt, mime_type)]
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                messages=messages,
                max_tokens=self.MAX_TOKENS,
                extra_headers={header[0]: header[1]}
            )

            file_response = response.content[0].to_dict()['text']

            if not isinstance(file_response, str):
                self.logger.error("Error parsing PDF with name: " + file_name + " Invoice response is not a string")
                raise Exception("Invoice response is not a string")

            if file_response is None:
                self.logger.error("Error parsing PDF with name: " + file_name + " Invoice response is None")
                raise Exception("Invoice response is None")

            return str(file_response)
        except Exception as e:
            self.logger.error("Error parsing PDF with name: " + file_name)
            raise Exception("Error parsing PDF with name: " + file_name)

