from dataclasses import dataclass
from io import BytesIO

from werkzeug.datastructures import FileStorage


@dataclass
class UploadDocumentRequest:

    uploadPath: str
    fileName: str
    collectionId: str
    tenantId: str
    userId: str
    fileType: str
    fileSize: int
    file: BytesIO
    callbackUrl: str
