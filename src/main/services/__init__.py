from typing import Optional

from .AnthropicClient import AnthropicClient
from .GeminiClient import GeminiClient
from .StorageService import StorageService
from ..logs.logger import setup_logger


class ServiceRegistry:

    def __init__(self):
        self.storage_service: Optional[StorageService] = None
        self.anthropic_client: Optional[AnthropicClient] = None
        self.gemini_client: Optional[GeminiClient] = None
        self.logger = setup_logger(__name__)

    def init_storage_service(self, bucket_name: str):
        self.storage_service = StorageService(bucket_name)
        self.logger.info("Storage service initialized.")

    def init_anthropic_client(self, api_key: str):
        self.anthropic_client = AnthropicClient(api_key)
        self.logger.info("Anthropic client initialized.")

    def init_gemini_client(self, api_key: str):
        self.gemini_client = GeminiClient(api_key)
        self.logger.info("Gemini client initialized.")


services = ServiceRegistry()
