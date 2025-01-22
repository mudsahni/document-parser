import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from google.cloud import secretmanager

def get_request_session() -> Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session


def access_secret_version(project_id, secret_id, version_id="latest"):
    """
    Access a secret version in Secret Manager.

    Args:
        project_id (str): Google Cloud project ID.
        secret_id (str): Secret ID.
        version_id (str): Version of the secret (default is "latest").

    Returns:
        str: The payload of the secret.
    """
    # Create the Secret Manager client
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version
    response = client.access_secret_version(request={"name": name})

    # Return the decoded payload of the secret
    payload = response.payload.data.decode("UTF-8")
    return payload
