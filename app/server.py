from flask import Flask, request, jsonify
from flask_cors import CORS
import main
app = Flask(__name__)
CORS(app)
#@app.route("/search", methods=["POST"])
@app.route("/search", methods=["GET"])
def search():
    """
    Perform an initial search on an input url or return the progress of 
    an ongoing query if applicable. The client will call this endpoint twice
    for every search query. This is because our original implementation 
    required a single call but launched a thread after calling main.start(). 
    Detaching the worker thread from the main thread seems to cause 
    a problem when deploying in docker. It's not clear why threading is an 
    issue but what is clear is that the first call to this endpoint needs 
    to be a blocking call (the client doesn't have to wait on it). While this
    thread is running the data processing (only scraping is done in separate 
    threads), another call to this endpoint should launch a new process
    or thread, depending on how uwsgi handles the call in production. That way,
    the client can set its progress flag and status message, which is is the 
    same information provided by the initial call to this endpoint in the 
    previous implementation. This way, we're letting the server itself handle
    the workers and manually launch threads only when it's logically imperative,
    as in the case of the scraping.
    """

    #json = request.json.get('url')
    q = request.args.get("q")
    p = request.args.get("p")
    json = q
    if not json: return jsonify({})
    
    res = main.start(q, progress=p)
    #res = main.start(json.get("q"))
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
    up_count = request.args.get("u")
    down_count = request.args.get("d")
    main.vote_to_db(question, answer, sku, up_count, down_count)
    return jsonify({"status": "vote received"})

if __name__ == "__main__":
    app.run()
