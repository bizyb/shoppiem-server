from flask import Flask, request, jsonify
from flask_cors import CORS
import main
app = Flask(__name__)
CORS(app)
 
@app.route("/search")
def search():
    url = request.form.get('url')
    if not url: url = request.args.get('url')
    response = jsonify({'status': main.start(url)})
    return response 

 
if __name__ == "__main__":
    app.run()