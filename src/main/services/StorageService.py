from io import BytesIO
from typing import List

from google.cloud import storage
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class StorageService:
    def __init__(self, bucket_name: str):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(bucket_name)

    def upload_files(self, file_name: str, file_path: str, files: List[BytesIO]) -> List[str]:
        """Upload files to GCS and return their GCS paths"""
        uploaded_paths = []

        for file in files:
            # Create a safe filename
            secure_file_name = secure_filename(file_name)
            filename = f"{file_path}/{secure_file_name}"
            blob = self.bucket.blob(filename)

            # Upload file
            blob.upload_from_file(file)
            uploaded_paths.append(filename)

        return uploaded_paths

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
