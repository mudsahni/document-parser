from dataclasses import dataclass
from typing import Dict, Optional

from ...enum.DocumentType import DocumentType


@dataclass
class ProcessDocumentCallbackRequest:
    id: str
    name: str
    type: DocumentType
    parsed_data: Optional[str]
    metadata: Dict[str, str]
    error: Optional[str]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "parsed_data": self.parsed_data,
            "metadata": self.metadata,
            "error": self.error
        }
