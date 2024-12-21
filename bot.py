from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls_wrapper import Wrapper
from google.generativeai import configure, GenerativeModel
from googleapiclient.discovery import build
from yt_dlp import YoutubeDL
from pytube import YouTube
import os
import time
import logging

# Logging setup
logging.basicConfig(
    format="%(asctime)s || %(name)s [%(levelname)s] - %(message)s",
    level=logging.INFO,
    datefmt="%m/%d/%Y, %H:%M:%S",
)

logging.info("Starting...")

# Bot Configuration
API_ID = os.getenv("API_ID", "25833520")
API_HASH = os.getenv("API_HASH", "7d012a6cbfabc2d0436d7a09d8362af7")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7821411247:AAG13LY43DJnAp51TtlXUlivuuh76lu2H7E")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Your YouTube Data API v3 key

# Initialize Pyrogram Client and PyTgCalls
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytgcalls = PyTgCalls(app)
pycalls = Wrapper(pytgcalls, "raw")

# Initialize Google Generative AI
configure(api_key=os.getenv("GENAI_KEY", "AIzaSyCsdHIafdTkws9PaPn3jrCzp13pBNqGvT4"))
model = GenerativeModel("gemini-1.5-flash")

# YouTube API client
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Helper Function: Fetch song suggestion
def get_song_for_feelings(feeling_description):
    prompt = (f"A user described their feelings as follows: '{feeling_description}'. "
              f"Suggest a Christian worship song with its artist that matches this situation. Response should be *[song name] by [artist]* nothing else or extra.")
    response = model.generate_content(prompt)
    return response.text.strip()

# Helper Function: Search YouTube video
def search_youtube_video(query):
    try:
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=1,
            order="relevance"
        )
        response = request.execute()
        if "items" in response and len(response["items"]) > 0:
            video_id = response["items"][0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={video_id}"
        else:
            raise Exception("No video found for the given query.")
    except Exception as e:
        raise Exception(f"Error while searching YouTube: {e}")

# Helper Function: Download YouTube audio
def download_audio_from_youtube(search_query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'noplaylist': True,
    }
    try:
        video_url = search_youtube_video(search_query)
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            return ydl.prepare_filename(info).replace(".webm", ".mp3")
    except Exception as e:
        raise e

# Command: Start
@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("Hello! Use `/song <query>` to search for a song, or tell me how you're feeling, and I'll suggest a worship song!")

# Command: Feelings-based song suggestion
@app.on_message(filters.text & ~filters.regex("^/"))
def feelings_handler(client, message):
    user_feelings = message.text
    message.reply_text("Let me think of a song for you...")

    try:
        # Fetch song suggestion
        song_suggestion = get_song_for_feelings(user_feelings)
        message.reply_text(f"I suggest: {song_suggestion}. Let me get the audio for you.")

        # Download audio
        audio_file = download_audio_from_youtube(song_suggestion)

        # Send audio file
        with open(audio_file, "rb") as f:
            client.send_audio(chat_id=message.chat.id, audio=f, title=song_suggestion)

        # Clean up
        os.remove(audio_file)
    except Exception as e:
        message.reply_text(f"Sorry, I couldn't fetch the song for you. Error: {str(e)}")

# Command: Stream
@app.on_message(filters.command("stream"))
async def stream_command(_, message):
    txt = message.text.split(" ", 1)
    try:
        song_name = txt[1]
        await message.reply_text(f"Streaming {song_name}...")
        await play_a_song(pycalls, message, song_name)
    except IndexError:
        await message.reply_text("Please provide the name of the song to stream.")

# Command: Song (search YouTube and download)
@app.on_message(filters.command("song"))
def song_command(client, message):
    query = " ".join(message.command[1:])
    message.reply_text("Searching for the song...")
    try:
        # Download audio
        audio_file = download_audio_from_youtube(query)

        # Send audio
        with open(audio_file, "rb") as f:
            client.send_audio(chat_id=message.chat.id, audio=f, title=query)

        # Clean up
        os.remove(audio_file)
    except Exception as e:
        message.reply_text(f"Sorry, I couldn't fetch the song. Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    logging.info("Bot is running...")
    app.run()
