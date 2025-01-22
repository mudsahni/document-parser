from typing import Optional

from .AnthropicClient import AnthropicClient
from .StorageService import StorageService
from ..logs.logger import setup_logger


class ServiceRegistry:

    def __init__(self):
        self.storage_service: Optional[StorageService] = None
        self.anthropic_client: Optional[AnthropicClient] = None
        self.logger = setup_logger(__name__)

    def init_storage_service(self, bucket_name: str):
        self.storage_service = StorageService(bucket_name)
        self.logger.info("Storage service initialized.")

    def init_anthropic_client(self, api_key: str):
        self.anthropic_client = AnthropicClient(api_key)
        self.logger.info("Anthropic client initialized.")


services = ServiceRegistry()
