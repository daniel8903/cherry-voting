from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session
import os
import json
from functools import wraps

# Prefer stdlib tomllib; fall back to 'toml' if needed (older Python)
try:
    import tomllib  # Python 3.11+
    _USE_TOMLLIB = True
except ModuleNotFoundError:
    import toml      # pip install toml
    _USE_TOMLLIB = False

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load config (absolute path, works on PythonAnywhere)
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.toml"
VOTES_PATH = BASE_DIR / "votes.json"

if _USE_TOMLLIB:
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
else:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = toml.load(f)

# --- Vote Data Functions ---
def get_all_votes():
    if not VOTES_PATH.exists():
        return {}
    with open(VOTES_PATH, "r") as f:
        return json.load(f)

def save_all_votes(votes):
    with open(VOTES_PATH, "w") as f:
        json.dump(votes, f, indent=4)

def record_vote(twitch_name, category_id, clip_id):
    votes = get_all_votes()
    if twitch_name not in votes:
        votes[twitch_name] = {}
    votes[twitch_name][category_id] = clip_id
    save_all_votes(votes)

def get_user_votes(twitch_name):
    votes = get_all_votes()
    return votes.get(twitch_name, {})

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'twitch_name' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session['twitch_name'] = request.form['twitch_name']
        return redirect(url_for('home'))
    return render_template("login.html")

@app.route("/home")
@login_required
def home():
    twitch_name = session['twitch_name']
    user_votes = get_user_votes(twitch_name)
    all_categories = config["categories"]

    voted_categories = {k: v for k, v in all_categories.items() if k in user_votes}
    todo_categories = {k: v for k, v in all_categories.items() if k not in user_votes}

    return render_template("home.html", voted_categories=voted_categories, todo_categories=todo_categories)

@app.route("/watch/<category_id>/<int:clip_index>")
@login_required
def watch_clip(category_id, clip_index):
    category = config["categories"][category_id]
    clip = category["clips"][clip_index]

    next_clip_index = clip_index + 1
    if next_clip_index >= len(category["clips"]):
        next_clip_index = None

    previous_clip_index = clip_index - 1
    if previous_clip_index < 0:
        previous_clip_index = None

    # Twitch parent = current domain without port
    parent_domain = request.host.split(":")[0]

    # Append parent param to existing embed URL
    separator = "&" if "?" in clip["url"] else "?"
    embed_url = f'{clip["url"]}{separator}parent={parent_domain}'

    return render_template(
        "watch.html",
        category_id=category_id,
        category=category,
        clip=clip,
        clip_index=clip_index,
        next_clip_index=next_clip_index,
        previous_clip_index=previous_clip_index,
        embed_url=embed_url
    )

@app.route("/vote/<category_id>")
@login_required
def vote(category_id):
    category = config["categories"][category_id]
    parent_domain = request.host.split(":")[0]
    return render_template("vote.html", category_id=category_id, category=category, parent_domain=parent_domain)

@app.route("/vote", methods=["POST"])
@login_required
def submit_vote():
    twitch_name = session['twitch_name']
    category_id = request.form.get("category_id")
    clip_id = int(request.form.get("vote"))

    record_vote(twitch_name, category_id, clip_id)

    voted_for_clip = config['categories'][category_id]['clips'][clip_id]
    print(f"Vote received from '{twitch_name}' for category '{category_id}': '{voted_for_clip['title']}'")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop('twitch_name', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)