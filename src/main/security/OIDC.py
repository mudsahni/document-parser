from google.auth.transport import requests
from google.oauth2 import id_token
from google.oauth2.id_token import fetch_id_token


def verify_oidc_token(request):
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        return None

    token = auth_header.split('Bearer ')[1]
    try:
        # Verify the token
        decoded_token = id_token.verify_oauth2_token(
            token, requests.Request())
        return decoded_token
    except Exception as e:
        return None


def get_callback_id_token(aud: str) -> str:
    # Get ID token for the callback
    auth_req = requests.Request()
    return fetch_id_token(auth_req, aud)
#

def get_callback_id_token_secure(session, aud: str) -> str:
    """
    Get ID token for callback with SSL compatibility

    Args:
        session: The session with SSL configuration
        aud: The audience for the token

    Returns:
        str: The ID token
    """
    from google.auth.transport import requests
    from google.oauth2.id_token import fetch_id_token
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Create a custom Request class that uses our secure session
        class SecureRequest(requests.Request):
            def __init__(self, session):
                self.session = session

            def __call__(self, url, method="GET", body=None, headers=None, timeout=60, **kwargs):
                response = self.session.request(
                    method,
                    url,
                    data=body,
                    headers=headers,
                    timeout=timeout,
                    **kwargs
                )

                # Create a properly adapted response object
                class AdaptedResponse:
                    def __init__(self, orig_response):
                        self.orig_response = orig_response
                        self.status = orig_response.status_code
                        self.headers = orig_response.headers
                        self.data = orig_response.content

                    def __getattr__(self, name):
                        return getattr(self.orig_response, name)

                return AdaptedResponse(response)

        # Create a request object that uses our secure session
        auth_req = SecureRequest(session)

        # Use Google's fetch_id_token function with our secure request
        token = fetch_id_token(auth_req, aud)
        return token
    except Exception as e:
        logger.error(f"Error getting callback token: {str(e)}")

        # Fallback to original implementation if secure version fails
        try:
            logger.info("Falling back to original token implementation")
            from google.auth.transport import requests as google_requests
            auth_req = google_requests.Request()
            return fetch_id_token(auth_req, aud)
        except Exception as fallback_error:
            logger.error(f"Fallback token retrieval also failed: {str(fallback_error)}")
            raise fallback_error