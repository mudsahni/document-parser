import os
from typing import Dict
from deepmerge import always_merger
import yaml

from .constants.EnvConstants import EnvConstants
from ..logs.logger import setup_logger

logger = setup_logger(__name__)

def load_yaml_file(path: str) -> Dict:
    with open(path, 'r') as file:
        return yaml.safe_load(file) or {}

def load_config() -> Dict:
    # Load base configuration first
    base_config = load_yaml_file(os.path.join(os.getcwd() + '/resources/application.yaml'))

    # Load environment specific config
    env = os.getenv(EnvConstants.ENV.value, 'dev')
    env_config = load_yaml_file(os.path.join(os.getcwd() + f'/resources/application-{env.lower()}.yaml'))

    # Merge configs, with env-specific values overriding base values
    return always_merger.merge(base_config, env_config)


class Configuration(object):
    def __init__(self):
        self._config = load_config()

    @property
    def env(self):
        return os.getenv(EnvConstants.ENV.value, 'dev')

    @property
    def bucket_name(self):
        return self._config['storage']['bucket']

    @property
    def document_store_api(self):
        return self._config['document-store']['url']
