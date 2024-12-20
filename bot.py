from pyrogram import Client, filters
from yt_dlp import YoutubeDL
import os
from google.generativeai import configure, GenerativeModel

# Bot Configuration
API_ID = os.getenv("API_ID", "25833520")
API_HASH = os.getenv("API_HASH", "7d012a6cbfabc2d0436d7a09d8362af7")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7821411247:AAGepURB3e243eeOVDnDk2h6pPPLIO9C2o8")

# Initialize Google Generative AI
configure(api_key=os.getenv("GENAI_KEY", "AIzaSyCsdHIafdTkws9PaPn3jrCzp13pBNqGvT4"))
model = GenerativeModel("gemini-1.5-flash")

# Default Mode (File or VC)
MODE = "file"  # Default mode is to send audio files

# Function to fetch song suggestion
def get_song_for_feelings(feeling_description):
    prompt = (f"A user described their feelings as follows: '{feeling_description}'. "
              f"Suggest a Christian worship song with its artist that matches this situation. Response should be *[song name] by [artist]* nothing else or extra ")
    response = model.generate_content(prompt)
    return response.text.strip()

# Function to download audio from YouTube
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

    invidious_instance = "https://yewtu.be"  # Use an Invidious instance
    query_url = f"{invidious_instance}/search?q={search_query}"

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query_url, download=True)
        return ydl.prepare_filename(info['entries'][0]).replace(".webm", ".mp3")



# Initialize Pyrogram Client
app = Client("feelings_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Handle /start command
@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("Hello! Tell me about your feelings or situation, and I'll send you a worship song suggestion.")

# Handle user input for feelings
# Handle user input for feelings
@app.on_message(filters.text & ~filters.regex("^/"))
def feelings_handler(client, message):
    user_feelings = message.text
    message.reply_text("Let me think of a song for you...")

    # Fetch song suggestion
    try:
        song_suggestion = get_song_for_feelings(user_feelings)
        message.reply_text(f"I suggest: {song_suggestion}. Let me get the audio for you.")

        # Extract song name and download audio
        audio_file = download_audio_from_youtube(song_suggestion)

        # Send audio file to user
        with open(audio_file, "rb") as f:
            client.send_audio(chat_id=message.chat.id, audio=f, title=song_suggestion)

        # Clean up downloaded file
        os.remove(audio_file)
    except Exception as e:
        message.reply_text(f"Sorry, I couldn't fetch the song for you. Error: {str(e)}")


# Run the bot
if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run()
