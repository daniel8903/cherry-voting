import toml
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# Load config
with open("config.toml") as f:
    config = toml.load(f)

# HTML Templates

HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Clip Voting</title>
</head>
<body>
    <h1>Choose a Category to Vote In</h1>
    <ul>
        {% for category_id, category in categories.items() %}
            <li><a href="{{ url_for('watch_clip', category_id=category_id, clip_index=0) }}">{{ category.name }}</a></li>
        {% endfor %}
    </ul>
</body>
</html>
"""

WATCH_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Watch Clip</title>
</head>
<body>
    <h1>{{ category.name }} - Clip {{ clip_index + 1 }} of {{ category.clips|length }}</h1>
    <h2>{{ clip.title }}</h2>
    <iframe
        src="{{ clip.url }}&parent=127.0.0.1"
        height="360"
        width="640"
        allowfullscreen="true">
    </iframe>
    <br>
    {% if next_clip_index is not none %}
        <a href="{{ url_for('watch_clip', category_id=category_id, clip_index=next_clip_index) }}">Next Clip</a>
    {% else %}
        <a href="{{ url_for('vote', category_id=category_id) }}">Proceed to Vote</a>
    {% endif %}
</body>
</html>
"""

VOTE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Vote</title>
</head>
<body>
    <h1>Vote for your favorite clip in {{ category.name }}</h1>
    <form action="{{ url_for('submit_vote') }}" method="post">
        <input type="hidden" name="category_id" value="{{ category_id }}">
        {% for clip in category.clips %}
            <input type="radio" id="{{ clip.title }}" name="vote" value="{{ clip.title }}" required>
            <label for="{{ clip.title }}">{{ clip.title }}</label><br>
        {% endfor %}
        <button type="submit">Submit Vote</button>
    </form>
</body>
</html>
"""

THANKS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Thanks!</title>
</head>
<body>
    <h1>Thank you for voting!</h1>
    <a href="{{ url_for('home') }}">Vote in another category</a>
</body>
</html>
"""


# Routes

@app.route("/")
def home():
    return render_template_string(HOME_TEMPLATE, categories=config['categories'])

@app.route("/watch/<category_id>/<int:clip_index>")
def watch_clip(category_id, clip_index):
    category = config['categories'][category_id]
    clip = category['clips'][clip_index]
    
    next_clip_index = clip_index + 1
    if next_clip_index >= len(category['clips']):
        next_clip_index = None

    return render_template_string(
        WATCH_TEMPLATE, 
        category_id=category_id,
        category=category, 
        clip=clip, 
        clip_index=clip_index,
        next_clip_index=next_clip_index
    )

@app.route("/vote/<category_id>")
def vote(category_id):
    category = config['categories'][category_id]
    return render_template_string(VOTE_TEMPLATE, category_id=category_id, category=category)

@app.route("/vote", methods=["POST"])
def submit_vote():
    category_id = request.form.get("category_id")
    voted_for = request.form.get("vote")
    print(f"Vote received for category '{category_id}': '{voted_for}'")
    return redirect(url_for('thanks'))

@app.route("/thanks")
def thanks():
    return render_template_string(THANKS_TEMPLATE)