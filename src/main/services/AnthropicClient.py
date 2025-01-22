import base64
import json
from typing import Optional, Dict, List

import anthropic
from anthropic import Anthropic

from ..logs.logger import setup_logger

def build_anthropic_api_pdf_parsing_request(
        pdf: str,
        prompt: str
) -> Dict:
    return {
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
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

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = setup_logger(__name__)
        self.client: Anthropic = anthropic.Anthropic(api_key=api_key)
        self.MAX_TOKENS = 8192
        self.ANTHROPIC_PDF_HEADER_KEY = "anthropic-beta"
        self.ANTHROPIC_PDF_HEADER_VALUE = "pdfs-2024-09-25"

    def process_pdf(
            self,
            file_name: str,
            file_content: bytes,
            prompt: str
    ) -> str:

        base64_pdf = base64.b64encode(file_content).decode()

        if base64_pdf is None:
            # TODO: Change to specific exception
            raise Exception("Could not read PDF file")

        messages: List[Dict] = [build_anthropic_api_pdf_parsing_request(base64_pdf, prompt)]
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            max_tokens=self.MAX_TOKENS,
            extra_headers={self.ANTHROPIC_PDF_HEADER_KEY: self.ANTHROPIC_PDF_HEADER_VALUE}
        )

        try:
            invoice_response = response.content[0].to_dict()['text']

            if type(invoice_response) is not str:
                self.logger.error("Error parsing PDF with name: " + file_name + " Invoice response is not a string")
                raise Exception("Invoice response is not a string")

            if invoice_response is None:
                self.logger.error("Error parsing PDF with name: " + file_name + " Invoice response is None")
                raise Exception("Invoice response is None")

            return str(invoice_response)
        except Exception as e:
            self.logger.error("Error parsing PDF with name: " + file_name)
            raise Exception("Error parsing PDF with name: " + file_name)

