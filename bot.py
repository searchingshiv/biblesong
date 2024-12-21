
from pyrogram import Client, filters
from pytube import YouTube
import os
import time
from google.generativeai import configure, GenerativeModel
from googleapiclient.discovery import build

# Bot Configuration
API_ID = os.getenv("API_ID", "25833520")
API_HASH = os.getenv("API_HASH", "7d012a6cbfabc2d0436d7a09d8362af7")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7821411247:AAG13LY43DJnAp51TtlXUlivuuh76lu2H7E")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Make sure to add your YouTube Data API v3 key

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
              f"Suggest a Christian worship song with its artist that matches this situation. Response should be *[song name] by [artist]* nothing else or extra ")
    response = model.generate_content(prompt)
    return response.text.strip()

# Function to search for a YouTube video using the YouTube Data API
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
        
        # Extract video ID
        if "items" in response and len(response["items"]) > 0:
            video_id = response["items"][0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={video_id}"
        else:
            raise Exception("No video found for the given query.")
    except Exception as e:
        raise Exception(f"Error while searching YouTube: {e}")

# Function to download audio from YouTube using Pytube
def download_audio_from_youtube(search_query, retries=3, delay=5):
    for attempt in range(retries):
        try:
            # Fetch YouTube video URL using the search function
            video_url = search_youtube_video(search_query)
            
            if not video_url:
                raise Exception(f"Could not find a valid YouTube video for the query: {search_query}")
            
            yt = YouTube(video_url)
            stream = yt.streams.filter(only_audio=True, file_extension="mp4").first()
            
            # Download the audio and save as mp3
            audio_file = f"downloads/{yt.title}.mp3"
            stream.download(output_path="downloads", filename=yt.title)
            
            # Convert to mp3 (if necessary)
            os.rename(f"downloads/{yt.title}.mp4", audio_file)
            return audio_file
        except Exception as e:
            if attempt < retries - 1:
                print(f"Error: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise e



# Function to download audio from YouTube using Pytube
def download_audio_from_youtube(search_query, retries=3, delay=5):
    for attempt in range(retries):
        try:
            # Fetch YouTube video URL using the search function
            video_url = search_youtube_video(search_query)
            
            if not video_url:
                raise Exception(f"Could not find a valid YouTube video for the query: {search_query}")
            
            yt = YouTube(video_url)
            stream = yt.streams.filter(only_audio=True, file_extension="mp4").first()
            
            # Download the audio and save as mp3
            audio_file = f"downloads/{yt.title}.mp3"
            stream.download(output_path="downloads", filename=yt.title)
            
            # Convert to mp3 (if necessary)
            os.rename(f"downloads/{yt.title}.mp4", audio_file)
            return audio_file
        except Exception as e:
            if attempt < retries - 1:
                print(f"Error: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise e


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
