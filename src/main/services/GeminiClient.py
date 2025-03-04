import json
from typing import Optional

import requests
from google import genai
from google.genai import types, Client

from ..config.constants.MimeTypes import MIME_TYPES
from ..logs.logger import setup_logger


class GeminiClient:

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = setup_logger(__name__)
        self.client: Client = genai.Client(api_key=api_key)
        self.GEMINI_MODEL = "gemini-2.0-flash"

    def _get_mime_type(self, file_name: str) -> Optional[str]:
        """
        Determine MIME type based on file extension
        """
        extension = file_name.lower().split('.')[-1]
        mime_type = MIME_TYPES.get(extension)

        if not mime_type:
            self.logger.warning(f"Unsupported file format: {extension}")

        return mime_type

    def _validate_json_response(self, response_text: str, file_name: str) -> str:
        """
        Validate that the response is a valid JSON string

        Args:
            response_text: The text response from Claude
            file_name: The name of the file being processed (for error reporting)

        Returns:
            The validated response text

        Raises:
            Exception: If the response is not valid JSON
        """
        try:
            # Attempt to parse the string as JSON
            json.loads(response_text)
            return response_text
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response for file {file_name}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"Response content: {response_text[:200]}...")  # Log first 200 chars
            raise Exception(error_msg)

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

        try:
            response = self.client.models.generate_content(
                model=self.GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(
                        data=file_content,
                        mime_type=mime_type,
                    ),
                    prompt])

            file_response = response.text

            if not isinstance(file_response, str):
                self.logger.error("Error parsing PDF with name: " + file_name + " Invoice response is not a string")
                raise Exception("Invoice response is not a string")

            if file_response is None:
                self.logger.error("Error parsing PDF with name: " + file_name + " Invoice response is None")
                raise Exception("Invoice response is None")

            json_response = str(file_response).replace("```json", "").replace("```", "")
            # Validate that the response is valid JSON
            validated_response = self._validate_json_response(json_response, file_name)

            return validated_response
        except Exception as e:
            self.logger.error("Error parsing PDF with name: " + file_name + " " + str(e))
            raise Exception("Error parsing PDF with name: " + file_name + " " + str(e))
