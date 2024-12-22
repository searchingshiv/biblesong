from pyrogram import Client, filters
from pytube import YouTube
import os
import time
from google.generativeai import configure, GenerativeModel
from googleapiclient.discovery import build

# Bot Configuration
API_ID = os.getenv("API_ID", "25833520")
API_HASH = os.getenv("API_HASH", "7d012a6cbfabc2d0436d7a09d8362af7e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7821411247:AAG13LY43DJnAp51TtlXUlivuuh76lu2H7E")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Add your YouTube Data API v3 key

# Initialize Google Generative AI
configure(api_key=os.getenv("GENAI_KEY", "AIzaSyCsdHIafdTkws9PaPn3jrCzp13pBNqGvT4"))
model = GenerativeModel("gemini-1.5-flash")

# Default Mode (File or VC)
MODE = "file"  # Default mode is to send audio files

# Initialize YouTube Data API client
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Function to fetch song suggestion
def get_song_for_feelings(feeling_description):
    prompt = (f"A user described their feelings as follows: '{feeling_description}'. "
              f"Suggest a Christian worship song with its artist that matches this situation. Response should be *[song name] by [artist]* nothing else or extra.")
    response = model.generate_content(prompt)
    return response.text.strip()

# Function to search for a YouTube video using the YouTube Data API
def search_youtube_video(query):
    try:
        print(f"Searching YouTube for: {query}")
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
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"Found YouTube video: {video_url}")
            return video_url
        else:
            raise Exception("No video found for the given query.")
    except Exception as e:
        print(f"Error while searching YouTube: {e}")
        raise

# Function to download audio from YouTube using Pytube
def download_audio_from_youtube(search_query, retries=3, delay=5):
    for attempt in range(retries):
        try:
            print(f"Attempt {attempt + 1}: Searching and downloading audio for query: {search_query}")

            video_url = search_youtube_video(search_query)
            yt = YouTube(video_url)
            stream = yt.streams.filter(only_audio=True, file_extension="mp4").first()

            if not stream:
                raise Exception("No audio stream found for the video.")

            audio_file = f"downloads/{yt.title}.mp3"
            stream.download(output_path="downloads", filename=yt.title)
            os.rename(f"downloads/{yt.title}.mp4", audio_file)

            print(f"Audio downloaded and saved as: {audio_file}")
            return audio_file
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
