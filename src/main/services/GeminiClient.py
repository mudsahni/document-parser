import requests
from google import genai
from google.genai import types, Client

from ..logs.logger import setup_logger


class GeminiClient:

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = setup_logger(__name__)
        self.client: Client = genai.Client(api_key="")
        self.GEMINI_MODEL = "gemini-2.0-flash"

    def process_pdf(
            self,
            file_name: str,
            file_content: bytes,
            prompt: str
    ) -> str:
        response = self.client.models.generate_content(
            model=self.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(
                    data=file_content,
                    mime_type='application/pdf',
                ),
                prompt])

        try:
            invoice_response = response.text

            if type(invoice_response) is not str:
                self.logger.error("Error parsing PDF with name: " + file_name + " Invoice response is not a string")
                raise Exception("Invoice response is not a string")

            if invoice_response is None:
                self.logger.error("Error parsing PDF with name: " + file_name + " Invoice response is None")
                raise Exception("Invoice response is None")

            return str(invoice_response).replace("```json", "").replace("```", "")
        except Exception as e:
            self.logger.error("Error parsing PDF with name: " + file_name)
            raise Exception("Error parsing PDF with name: " + file_name)
