from flask import Flask, jsonify, request
import main
app = Flask(__name__)
 
@app.route("/search")
def search():
    response = {"status": "Unable to fulfill request"}
    url = request.args.get('url')
    # if request.method == 'POST':
        # url = request.form.get('url')
    response = {"status": main.start(url)}
    return jsonify(response)

 
if __name__ == "__main__":
    app.run()