
from gevent import monkey
monkey.patch_all()

import os
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

from main import create_app

from dotenv import load_dotenv

load_dotenv()

app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
