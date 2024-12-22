from pyrogram import Client, filters
from y2mate import YouTube
import os
import time
from google.generativeai import configure, GenerativeModel
import requests
import argparse
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import threading

def start_fake_server(port):
    handler = SimpleHTTPRequestHandler
    with TCPServer(("0.0.0.0", port), handler) as httpd:
        print(f"Fake server running on port {port}")
        httpd.serve_forever()

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, help="Port to run the fake server", default=8080)
args = parser.parse_args()

# Start a fake server in a separate thread
server_thread = threading.Thread(target=start_fake_server, args=(args.port,))
server_thread.daemon = True
server_thread.start()

# Bot Configuration
API_ID = os.getenv("API_ID", "25833520")
API_HASH = os.getenv("API_HASH", "7d012a6cbfabc2d0436d7a09d8362af7e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7821411247:AAG13LY43DJnAp51TtlXUlivuuh76lu2H7E")
GENAI_KEY = os.getenv("GENAI_KEY", "AIzaSyCsdHIafdTkws9PaPn3jrCzp13pBNqGvT4")

# Initialize Google Generative AI
configure(api_key=GENAI_KEY)
model = GenerativeModel("gemini-1.5-flash")

# Initialize Y2Mate
y2mate = YouTube()

# Function to fetch song suggestion
def get_song_for_feelings(feeling_description):
    prompt = (f"A user described their feelings as follows: '{feeling_description}'. "
              f"Suggest a Christian worship song with its artist that matches this situation. Response should be *[song name] by [artist]* nothing else or extra.")
    response = model.generate_content(prompt)
    return response.text.strip()

# Function to search for a YouTube video using Y2Mate
def search_youtube_video(query):
    try:
        print(f"Searching YouTube for: {query}")
        search_results = y2mate.search(query, max_results=1)
        if search_results:
            video_url = search_results[0]["link"]
            print(f"Found YouTube video: {video_url}")
            return video_url
        else:
            raise Exception("No video found for the given query.")
    except Exception as e:
        print(f"Error while searching YouTube: {e}")
        raise

# Function to download audio from YouTube using Y2Mate
def download_audio_from_youtube(search_query, retries=3, delay=5):
    for attempt in range(retries):
        try:
            print(f"Attempt {attempt + 1}: Searching and downloading audio for query: {search_query}")
            video_url = search_youtube_video(search_query)
            print(f"Video URL: {video_url}")

            # Download the video audio using Y2Mate
            audio_file_path = y2mate.download_audio(video_url)

            print(f"Audio downloaded and saved as: {audio_file_path}")
            return audio_file_path
        except Exception as e:
            print(f"Error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
            if attempt == retries - 1:
                raise

# Initialize Pyrogram Client
app = Client("feelings_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Handle /start command
@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("Hello! Tell me about your feelings or situation, and I'll send you a worship song suggestion.")

# Handle user input for feelings
@app.on_message(filters.text & ~filters.regex("^/"))
def feelings_handler(client, message):
    user_feelings = message.text
    message.reply_text("Let me think of a song for you...")
    print(f"User feelings: {user_feelings}")

    try:
        song_suggestion = get_song_for_feelings(user_feelings)
        message.reply_text(f"I suggest: {song_suggestion}. Let me get the audio for you.")
        print(f"Suggested song: {song_suggestion}")

        audio_file = download_audio_from_youtube(song_suggestion)

        with open(audio_file, "rb") as f:
            client.send_audio(chat_id=message.chat.id, audio=f, title=song_suggestion)

        os.remove(audio_file)
        print(f"Audio sent and file deleted: {audio_file}")
    except Exception as e:
        error_message = f"Sorry, I couldn't fetch the song for you. Error: {str(e)}"
        message.reply_text(error_message)
        print(error_message)

# Run the bot
if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    print("Bot is running...")
    app.run()
