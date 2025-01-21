from dataclasses import dataclass

from ...enum.DocumentType import DocumentType


@dataclass
class ProcessDocumentRequest:
    tenant_id: str
    collection_id: str
    id: str
    type: DocumentType
    file_type: str
    url: str
    name: str
    callback_url: str

    def to_dict(self):
        return {
            "tenant_id": self.tenant_id,
            "collection_id": self.collection_id,
            "id": self.id,
            "type": self.type,
            "file_type": self.file_type,
            "url": self.url,
            "name": self.name,
            "callback_url": self.callback_url
        }