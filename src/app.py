import os
from main import create_app
from flask import Flask

from dotenv import load_dotenv

load_dotenv()

app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
