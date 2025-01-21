from typing import Optional

from .StorageService import StorageService
from ..logs.logger import setup_logger


class ServiceRegistry:

    def __init__(self):
        self.storage_service: Optional[StorageService] = None
        self.logger = setup_logger(__name__)

    def init_storage_service(self, bucket_name: str):
        self.storage_service = StorageService(bucket_name)
        self.logger.info("Storage service initialized.")

services = ServiceRegistry()
