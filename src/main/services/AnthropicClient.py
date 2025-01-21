from ..logs.logger import setup_logger


class AnthropicClient:

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = setup_logger(__name__)
        self.client: Anthropic = anthropic.Anthropic(api_key=api_key, http_client=httpx_client)
        self.MAX_TOKENS = 8192
        self.ANTHROPIC_PDF_HEADER_KEY = "anthropic-beta"
        self.ANTHROPIC_PDF_HEADER_VALUE = "pdfs-2024-09-25"

    def process_pdf(self, model: str, file_path: str, file_content: bytes, prompt: str) -> Dict:
        base64_pdf: Optional[str] = None
        # with open(f"./{file_path}", "rb") as f:
        #     base64_pdf = base64.b64encode(f.read()).decode()

        base64_pdf = base64.b64encode(file_content).decode()

        if base64_pdf is None: