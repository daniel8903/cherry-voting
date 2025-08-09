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

4. **Set environment variables:**
   To fetch clip information, you need to set your Twitch API credentials as environment variables.
   ```bash
   export TWITCH_CLIENT_ID="your-client-id"
   export TWITCH_CLIENT_SECRET="your-client-secret"
   ```

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
