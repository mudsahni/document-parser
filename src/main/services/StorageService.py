from io import BytesIO
from typing import List

from google.cloud import storage
from werkzeug.utils import secure_filename

from src.main.logs.logger import setup_logger


class StorageService:
    def __init__(self, bucket_name: str):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(bucket_name)
        self.logger = setup_logger(__name__)

    def upload_file(self, file_name: str, file_path: str, file: BytesIO) -> str:
        """Upload files to GCS and return their GCS paths"""

        self.logger.info(f"Uploading file {file_name} to {file_path}")
        # Create a safe filename
        secure_file_name = secure_filename(file_name)
        filename = f"{file_path}/{secure_file_name}"
        blob = self.bucket.blob(filename)
        # Upload file
        blob.upload_from_file(file)

        self.logger.info(f"File uploaded to {filename}")
        return f"{file_path}/{secure_file_name}"

    def get_download_urls(self, filenames: List[str], expiration: int = 3600) -> List[str]:
        """Generate signed URLs for downloading files"""
        urls = []
        for filename in filenames:
            blob = self.bucket.blob(filename)
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            urls.append(url)
        return urls
