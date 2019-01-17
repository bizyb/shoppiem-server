from flask import Flask, request, jsonify
from flask_cors import CORS
# from flask_executor import Executor
import main
app = Flask(__name__)
CORS(app)
# executor = Executor(app)
url = "https://www.amazon.com/All-new-Kindle-Paperwhite-Waterproof-Storage/dp/B07CXG6C9W/ref=redir_mobile_desktop?_encoding=UTF8&ref_=ods_gw_ha_eink_ms_jan"

@app.route("/search")
def search():
    url = request.form.get('url')
    if not url: url = request.args.get('url')
    res = main.start(url)
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
    """
    response = main.get_answer()
    # response = {"confidence": 0.85,
    #             "question": "What is the meaning of life?",
    #             "answer": 42
    #         }
    return jsonify(response)

@app.route("/vote")
def vote():
    """
    extract the params here and save it to the db 
    """
    question = request.args.get("q")
    answer = request.args.get("a")
    sku = request.args.get("sku")
    vote = request.args.get("vote")
    main.vote_to_db(question, answer, sku, vote)
    return jsonify(request.args)

if __name__ == "__main__":
    app.run()