from pyrogram import Client, filters
import os
import time
from google.generativeai import configure, GenerativeModel
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import yt_dlp

# Bot Configuration
API_ID = os.getenv("API_ID", "25833520")
API_HASH = os.getenv("API_HASH", "7d012a6cbfabc2d0436d7a09d8362af7e")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7821411247:AAG13LY43DJnAp51TtlXUlivuuh76lu2H7E")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Initialize Google Generative AI
configure(api_key=os.getenv("GENAI_KEY", "AIzaSyCsdHIafdTkws9PaPn3jrCzp13pBNqGvT4"))
model = GenerativeModel("gemini-1.5-flash")

# Initialize YouTube Data API client
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Create downloads directory if not exists
os.makedirs("downloads", exist_ok=True)




# Function to sanitize filenames to avoid issues with special characters
def sanitize_filename(filename):
    return filename.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "").replace("'", "")

# Function to fetch song suggestion
recent_suggestions = []

# Function to fetch song suggestion, modified to consider recent suggestions
def get_song_for_feelings(feeling_description):
    # Filter out songs that are already in the recent suggestions list
    # Passing a list of recent songs to the AI model's prompt
    prompt = (f"A user described their feelings as follows: '{feeling_description}'. "
              f"Suggest a Christian worship song with its artist that matches this situation. "
              f"Exclude songs from this list: {', '.join(recent_suggestions)}. "
              f"Response should be *[song name] by [artist]*, nothing else.")
    response = model.generate_content(prompt)
    return response.text.strip()

# Function to add the new song to the recent suggestions list
def add_to_recent_suggestions(song_suggestion):
    if len(recent_suggestions) >= 15:
        recent_suggestions.clear()  # Reset the list once it reaches 15 songs
    recent_suggestions.append(song_suggestion)

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

        if "items" in response and len(response["items"]) > 0:
            video_id = response["items"][0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={video_id}"
        else:
            raise Exception("No video found for the given query.")
    except HttpError as e:
        error_details = e.content.decode("utf-8")
        raise Exception(f"YouTube API error: {error_details}")
    except Exception as e:
        raise Exception(f"Error while searching YouTube: {str(e)}")

# Function to display download/upload progress
def progress_bar(current, total, prefix="Progress"): 
    percent = (current / total) * 100
    bar = "=" * int(percent / 5) + "-" * (20 - int(percent / 5))
    return f"{prefix}: [{bar}] {percent:.1f}%"

# Function to download audio from YouTube using yt_dlp
def download_audio_from_youtube(video_url, search_query):
    try:
        sanitized_search_query = sanitize_filename(search_query)
        audio_file = f"downloads/{sanitized_search_query}"

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_file + ".%(ext)s", 
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            ],
            "cookiefile": "cookies.txt",
            "rm-cache-dir": True, 
            "progress_hooks": [lambda d: print(progress_bar(d['downloaded_bytes'], d['total_bytes'], prefix="Download"))],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return audio_file
    except Exception as e:
        raise Exception(f"Error downloading audio: {str(e)}")

# Function to clean up the downloads directory (remove old files)
def clean_downloads_directory():
    for filename in os.listdir("downloads"):
        file_path = os.path.join("downloads", filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

# Initialize Pyrogram Client
app = Client("feelings_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Handle /start command
@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("Hello! Tell me about your feelings or situation, and I'll send you a worship song suggestion.")

# Handle document uploads to update cookies.txt
@app.on_message(filters.command("update") & filters.reply)
def update_cookies_reply(client, message):
    try:
        # Check if the replied message contains a document
        if message.reply_to_message and message.reply_to_message.document:
            document = message.reply_to_message.document

            # Ensure the file is a .txt file
            if document.file_name.endswith(".txt"):
                file_path = client.download_media(message=document)
                os.rename(file_path, "cookies.txt")
                message.reply_text("Cookies file updated successfully.")
            else:
                message.reply_text("The replied file is not a valid .txt file. Please reply to a .txt file.")
        else:
            message.reply_text("Please reply to a valid .txt file with the /update command.")
    except Exception as e:
        message.reply_text(f"Failed to update cookies file. Error: {str(e)}")

# Handle user input for feelings
@app.on_message(filters.text & ~filters.regex("^/"))
def feelings_handler(client, message):
    user_feelings = message.text
    message.reply_text("Let me think of a song for you...")

    try:
        song_suggestion = get_song_for_feelings(user_feelings)
        message.reply_text(f"I suggest: {song_suggestion}. Let me get the audio for you.")

        clean_downloads_directory()
        video_url = search_youtube_video(song_suggestion)
        audio_file = download_audio_from_youtube(video_url, song_suggestion)

        with open(audio_file + ".mp3", "rb") as f:
            client.send_audio(chat_id=message.chat.id, audio=f, title=song_suggestion)

        os.remove(audio_file)
    except Exception as e:
        message.reply_text(f"Sorry, I couldn't fetch the song for you. Error: {str(e)}")

# Handle /s <song name>
@app.on_message(filters.command("s"))
def song_handler(client, message):
    try:
        query = " ".join(message.command[1:])
        if not query:
            message.reply_text("Please provide a song name after /s.")
            return
        
        video_url = search_youtube_video(query)
        video_details = youtube.videos().list(part="snippet", id=video_url.split("=")[1]).execute()["items"][0]
        title = video_details["snippet"]["title"]
        thumbnail_url = video_details["snippet"]["thumbnails"]["high"]["url"]

        message.reply_photo(photo=thumbnail_url, caption=f"**Title:** {title}\n**Link:** {video_url}\nReply with /l <YouTube link> to download this.")
    except Exception as e:
        message.reply_text(f"Failed to process song details. Error: {str(e)}")

# Handle /l <YouTube link>
@app.on_message(filters.command("l"))
def link_handler(client, message):
    try:
        link = " ".join(message.command[1:])
        if not link:
            message.reply_text("Please provide a YouTube link after /l.")
            return

        message.reply_text("Downloading your requested song...")
        clean_downloads_directory()
        audio_file = download_audio_from_youtube(link, "Requested_Song")

        with open(audio_file + ".mp3", "rb") as f:
            client.send_audio(chat_id=message.chat.id, audio=f, title="Requested Song")

        os.remove(audio_file)
    except Exception as e:
        message.reply_text(f"Failed to download the song. Error: {str(e)}")

# Run the bot
if __name__ == "__main__":
    app.run()
