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
