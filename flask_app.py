from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for
import os

# Prefer stdlib tomllib; fall back to 'toml' if needed (older Python)
try:
    import tomllib  # Python 3.11+
    _USE_TOMLLIB = True
except ModuleNotFoundError:
    import toml      # pip install toml
    _USE_TOMLLIB = False

app = Flask(__name__)

# Load config (absolute path, works on PythonAnywhere)
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.toml"

if _USE_TOMLLIB:
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
else:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = toml.load(f)

# Routes
@app.route("/")
def home():
    return render_template("home.html", categories=config["categories"])


@app.route("/watch/<category_id>/<int:clip_index>")
def watch_clip(category_id, clip_index):
    category = config["categories"][category_id]
    clip = category["clips"][clip_index]

    next_clip_index = clip_index + 1
    if next_clip_index >= len(category["clips"]):
        next_clip_index = None

    # Twitch parent = current domain without port
    parent_domain = request.host.split(":")[0]

    # Append parent param to existing embed URL
    separator = "&" if "?" in clip["url"] else "?"
    embed_url = f"{clip['url']}{separator}parent={parent_domain}"

    return render_template(
        "watch.html",
        category_id=category_id,
        category=category,
        clip=clip,
        clip_index=clip_index,
        next_clip_index=next_clip_index,
        embed_url=embed_url
    )


@app.route("/vote/<category_id>")
def vote(category_id):
    category = config["categories"][category_id]
    parent_domain = request.host.split(":")[0]
    return render_template("vote.html", category_id=category_id, category=category, parent_domain=parent_domain)


@app.route("/vote", methods=["POST"])
def submit_vote():
    category_id = request.form.get("category_id")
    voted_for = request.form.get("vote")
    print(f"Vote received for category '{category_id}': '{voted_for}'")
    return redirect(url_for("thanks"))


@app.route("/thanks")
def thanks():
    return render_template("thanks.html")


if __name__ == "__main__":
    app.run(debug=True)