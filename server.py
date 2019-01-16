from flask import Flask, request, jsonify
from flask_cors import CORS
# from flask_executor import Executor
import main
app = Flask(__name__)
CORS(app)
# executor = Executor(app)
 
@app.route("/search")
def search():
    url = request.form.get('url')
    if not url: url = request.args.get('url')
    main.start(url)
    response = jsonify({ 
            "sku": "0972683275",
            "in_progress": True,
            })
    return response 

@app.route("/recent")
def recent():
    """
    Return the most recent three items that have been analyzed.
    """
    recent = {
        "img": "monitor.png", 
        "title": """Acer SB220Q bi 21.5" Full HD (1920 x 1080) IPS Ultra-Thin Zero Frame Monitor (HDMI & VGA Port)"""
    }
    recent = [recent for _ in range(3)]
    return jsonify({"recent": recent})

@app.route("/status")
def status():
    """
    Return the status of the current sku.
    """
    sku = request.form.get('sku')
    if not sku: sku = request.args.get('sku')
    status = main.get_status(sku)
    # print "in server status ==================: ", status
    msgs = {"done": ["Process 1", "Process 2", "Process 3"], "in_progress": "Process 4"}
    return jsonify({
                    "progress_msgs": msgs, 
                    "item_ready": False, 
                    "status": status,
                    }) 

@app.route("/question")
def question():
    """
    
    """
    main.get_answer()
    response = {"confidence": 0.85,
                "question": "What is the meaning of life?",
                "answer": 42
            }
    return jsonify(response)

@app.route("/vote")
def vote():
    """
    extract the params here
    """
    return jsonify(request.args)

if __name__ == "__main__":
    app.run()