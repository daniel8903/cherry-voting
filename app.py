import toml
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Load config
with open("config.toml") as f:
    config = toml.load(f)




# Routes

@app.route("/")
def home():
    return render_template("home.html", categories=config['categories'])

@app.route("/watch/<category_id>/<int:clip_index>")
def watch_clip(category_id, clip_index):
    category = config['categories'][category_id]
    clip = category['clips'][clip_index]
    
    next_clip_index = clip_index + 1
    if next_clip_index >= len(category['clips']):
        next_clip_index = None

    return render_template(
        "watch.html", 
        category_id=category_id,
        category=category, 
        clip=clip, 
        clip_index=clip_index,
        next_clip_index=next_clip_index
    )

@app.route("/vote/<category_id>")
def vote(category_id):
    category = config['categories'][category_id]
    return render_template("vote.html", category_id=category_id, category=category)

@app.route("/vote", methods=["POST"])
def submit_vote():
    category_id = request.form.get("category_id")
    voted_for = request.form.get("vote")
    print(f"Vote received for category '{category_id}': '{voted_for}'")
    return redirect(url_for('thanks'))

@app.route("/thanks")
def thanks():
    return render_template("thanks.html")