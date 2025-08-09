# Cherry Voting

A web application for voting on Twitch clips, categorized by different moments.

## Setup and Running

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   ```

2. **Install dependencies:**
   Make sure you have `uv` installed. You can install it with `pip install uv`.
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Configure the application:**
   - Rename the `config.example.toml` to `config.toml`.
   - Add your Twitch clips to the `config.toml` file, under the appropriate categories.

4. **Configure Environment Variables:**

   For local development, it's recommended to use a `.flaskenv` file to manage your environment variables. Create a file named `.flaskenv` in the root of the project with the following content:

   ```
   FLASK_APP=flask_app.py
   FLASK_ENV=development
   ```

   To fetch clip information, you also need to set your Twitch API credentials as environment variables. You can add them to your `.flaskenv` file as well:

   ```
   TWITCH_CLIENT_ID="your-client-id"
   TWITCH_CLIENT_SECRET="your-client-secret"
   ```

   For production, you should set these environment variables directly on your deployment platform.

5. **Run the application:**
   ```bash
   flask run
   ```

## Technologies Used

- Python
- Flask
- Toml
- Bootstrap
- Jupyter Notebook (for clip fetching)
