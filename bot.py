from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message
from py_tgcalls import PyTgCalls, StreamType
from py_tgcalls.types.input_stream import InputAudioStream
import yt_dlp
import google.generativeai as genai
import os
import requests
import threading

# Bot Configurations
API_ID = os.getenv("API_ID", "25833520")
API_HASH = os.getenv("API_HASH", "7d012a6cbfabc2d0436d7a09d8362af7")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7821411247:AAGepURB3e243eeOVDnDk2h6pPPLIO9C2o8")

# Flask app for Render (to keep alive)
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running!"

# Initialize Pyrogram Bot and PyTgCalls for VC
bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
vc_client = PyTgCalls(bot)

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GENAI_KEY", "AIzaSyCsdHIafdTkws9PaPn3jrCzp13pBNqGvT4"))
model = genai.GenerativeModel("gemini-1.5-flash")

# Default Mode (File or VC)
MODE = "file"  # Default mode is to send audio files

# Function to fetch worship song suggestion
def get_song_for_feelings(feeling_description):
    prompt = (f"A user described their feelings as follows: '{feeling_description}'. "
              f"Suggest a Christian worship song with its artist that matches this situation.")
    response = model.generate_content(prompt)
    return response.text.strip()

# Function to fetch YouTube audio URL
def get_youtube_audio_url(search_query):
    ydl_opts = {
        "format": "bestaudio",
        "noplaylist": True,
        "default_search": "ytsearch",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=False)
        return info["entries"][0]["url"], info["entries"][0]["title"]

# Function to download YouTube audio
def download_audio(audio_url, output_file="song.raw"):
    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": output_file,
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([audio_url])

# Function to fetch lyrics
def get_lyrics(song_name, artist):
    try:
        response = requests.get(f"https://api.lyrics.ovh/v1/{artist}/{song_name}")
        if response.status_code == 200:
            return response.json().get("lyrics", "Lyrics not found.")
        else:
            return "Lyrics not found."
    except Exception as e:
        return f"Error fetching lyrics: {str(e)}"

# Command to switch to file mode
@bot.on_message(filters.command("file"))
async def set_file_mode(client, message):
    global MODE
    MODE = "file"
    await message.reply("Switched to **File Mode**. Songs will be sent as audio files.")

# Command to switch to VC mode
@bot.on_message(filters.command("vc"))
async def set_vc_mode(client, message):
    global MODE
    MODE = "vc"
    await message.reply("Switched to **Voice Chat Mode**. Songs will be played live in the voice chat.")

# Respond to feelings and handle music
@bot.on_message(filters.text & ~filters.command)
async def respond_to_feeling(client, message: Message):
    feeling_description = message.text
    chat_id = message.chat.id

    await message.reply("Let me find a song for you based on your feelings...")
    try:
        # Suggest a song using Generative AI
        song_suggestion = get_song_for_feelings(feeling_description)
        song_name, artist = song_suggestion.split(" - ") if " - " in song_suggestion else (song_suggestion, "Unknown")

        await message.reply(f"Based on your feelings, I suggest:\n\n**{song_suggestion}**\n\nFetching the audio and lyrics...")

        # Fetch YouTube audio URL
        audio_url, title = get_youtube_audio_url(song_suggestion)

        # Fetch lyrics
        lyrics = get_lyrics(song_name, artist)

        if MODE == "file":
            # Send audio file mode
            download_audio(audio_url)
            await message.reply_audio("song.raw", caption=f"Here’s your song: **{title}**\n\n**Lyrics:**\n{lyrics}")
            os.remove("song.raw")  # Clean up the file after sending

        elif MODE == "vc":
            # Play in VC mode
            await message.reply(f"Joining the voice chat to play **{title}**...\n\n**Lyrics:**\n{lyrics}")
            download_audio(audio_url, output_file="song.raw")
            await vc_client.join_group_call(
                chat_id,
                InputAudioStream("song.raw"),
                stream_type=StreamType().local_stream,
            )
    except Exception as e:
        await message.reply(f"Sorry, I couldn't process your request. Error: {str(e)}")

# Cleanup after VC streaming ends
@vc_client.on_stream_end()
async def stream_end_handler(client, update: StreamType):
    if os.path.exists("song.raw"):
        os.remove("song.raw")

# Start Flask App and Pyrogram Bot concurrently
def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Run Flask in a separate thread
    threading.Thread(target=run_flask).start()
    # Start the bot
    bot.run()
