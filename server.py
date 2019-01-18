from flask import Flask, request, jsonify
from flask_cors import CORS
import main
app = Flask(__name__)
CORS(app)

@app.route("/search", methods=["POST"])
def search():

    json = request.json.get('url')
    if not json: return jsonify({})

    res = main.start(json.get("q"))
    if res: return jsonify(res)
    return jsonify(res)
    

@app.route("/recent")
def recent():
    """
    Return the most recent three items that have been analyzed.
    """
    recent = main.get_most_recent()
    return jsonify({"recent": recent})

@app.route("/status")
def status():
    """
    Return the status of the current sku.
    """
    sku = request.form.get('sku')
    if not sku: sku = request.args.get('sku')
    response = main.get_status(sku)
    return jsonify(response)

@app.route("/question")
def question():
    """
    Query the appropriate model for answer.
    """
    sku = request.args.get("sku")
    question = request.args.get("q")
    response = main.get_answer(question, sku)
    return jsonify(response)

@app.route("/vote")
def vote():
    """
    Save up/down voting data to the database.
    """
    question = request.args.get("q")
    answer = request.args.get("a")
    sku = request.args.get("sku")
    vote = request.args.get("vote")
    main.vote_to_db(question, answer, sku, vote)
    return jsonify(request.args)

if __name__ == "__main__":
    app.run()