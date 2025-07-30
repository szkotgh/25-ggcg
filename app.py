import os
from flask import Flask
from dotenv import load_dotenv
load_dotenv()
from router import router_bp


app = Flask(__name__)
app.register_blueprint(router_bp)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

if __name__ == '__main__':
    app.run(os.environ['SERVER_IP'], os.environ['SERVER_PORT'], debug=True)