from pyrogram import Client, filters
import os
import time
from google.generativeai import configure, GenerativeModel
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import yt_dlp
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
API_ID = os.getenv("API_ID", "")
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Initialize Google Generative AI
configure(api_key=os.getenv("GENAI_KEY", ""))
model = GenerativeModel("gemini-1.5-flash")

# Initialize YouTube Data API client
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Create downloads directory if not exists
os.makedirs("downloads", exist_ok=True)

# Function to sanitize filenames to avoid issues with special characters
def sanitize_filename(filename):
    return filename.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "").replace("'", "")

# Function to fetch multiple song suggestions
recent_suggestions = []

def get_song_for_feelings(feeling_description, count=10):
    songs = []
    for _ in range(count):
        prompt = (f"A user described their feelings as follows: '{feeling_description}'. "
                 f"Suggest a Christian worship song with its artist that matches this situation. "
                 f"Exclude songs from this list: {', '.join(recent_suggestions)}. "
                 f"Response should be *[song name] by [artist]*, nothing else.")
        response = model.generate_content(prompt)
        song = response.text.strip()
        songs.append(song)
        add_to_recent_suggestions(song)
    return songs

def add_to_recent_suggestions(song_suggestion):
    if len(recent_suggestions) >= 30:  # Allow up to 30 songs
        recent_suggestions.clear()
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

# Function to download audio from YouTube
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
    message.reply_text("🌟 Hello! Share your feelings or situation, and I'll suggest worship songs for you. 🙏")

# Handle document uploads to update cookies.txt
@app.on_message(filters.command("update") & filters.reply)
def update_cookies_reply(client, message):
    try:
        if message.reply_to_message and message.reply_to_message.document:
            document = message.reply_to_message.document
            if document.file_name.endswith(".txt"):
                file_path = client.download_media(message=document)
                os.rename(file_path, "cookies.txt")
                message.reply_text("✅ Cookies file updated successfully.")
            else:
                message.reply_text("❌ Please reply to a valid .txt file.")
        else:
            message.reply_text("❌ Reply to a valid .txt file with the /update command.")
    except Exception as e:
        message.reply_text(f"❌ Failed to update cookies file. Error: {str(e)}")

@app.on_message(filters.text & ~filters.regex("^/"))
def feelings_handler(client, message):
    user_feelings = message.text
    progress_message = message.reply_text("🤔 Let me find songs for you...")

    try:
        # Fetch multiple song suggestions (10)
        song_suggestions = get_song_for_feelings(user_feelings, count=10)

        # Send the list of songs to the user
        song_list = "\n".join([f"{idx + 1}. {song}" for idx, song in enumerate(song_suggestions)])
        progress_message.edit_text(f"🎶 Here are the songs I found for you:\n\n{song_list}\n\nStarting downloads...")

        # Clean downloads directory
        clean_downloads_directory()

        # Process each song one by one
        for idx, song in enumerate(song_suggestions, start=1):
            progress_message.edit_text(f"📥 Downloading song {idx}/{len(song_suggestions)}: {song}...")

            # Search and download the song
            video_url = search_youtube_video(song)
            audio_file = download_audio_from_youtube(video_url, song)

            # Upload the downloaded file
            mp3_file_path = audio_file + ".mp3"
            if os.path.exists(mp3_file_path):
                with open(mp3_file_path, "rb") as f:
                    client.send_audio(chat_id=message.chat.id, audio=f, title=song)
                os.remove(mp3_file_path)  # Clean up after sending
            else:
                raise Exception(f"Downloaded file not found: {mp3_file_path}")

        progress_message.edit_text("✅ All songs are ready! Enjoy. 🎧")

    except Exception as e:
        progress_message.edit_text(f"❌ Oops! Something went wrong. Error: {str(e)}")

# Handle /s <song name>
@app.on_message(filters.command("s"))
def song_handler(client, message):
    try:
        query = " ".join(message.command[1:])
        if not query:
            message.reply_text("❌ Please provide a song name after /s.")
            return

        video_url = search_youtube_video(query)
        video_details = youtube.videos().list(part="snippet", id=video_url.split("=")[1]).execute()["items"][0]
        title = video_details["snippet"]["title"]
        thumbnail_url = video_details["snippet"]["thumbnails"]["high"]["url"]

        message.reply_photo(photo=thumbnail_url, caption=f"🎵 **Title:** {title}\n🔗 **Link:** {video_url}\nReply with /l <YouTube link> to download this.")
    except Exception as e:
        message.reply_text(f"❌ Failed to fetch song details. Error: {str(e)}")

# Handle /l <YouTube link>
@app.on_message(filters.command("l"))
def link_handler(client, message):
    try:
        # Extract the YouTube link from the message
        link = " ".join(message.command[1:])
        if not link:
            message.reply_text("❌ Please provide a YouTube link after /l.")
            return

        # Notify user about the download progress
        progress_message = message.reply_text("🎥 Downloading your requested song...")

        # Fetch the video details for a sanitized title
        video_id = link.split("v=")[1] if "v=" in link else link.split("/")[-1]
        video_details = youtube.videos().list(part="snippet", id=video_id).execute()["items"][0]
        title = video_details["snippet"]["title"]
        sanitized_title = sanitize_filename(title)

        # Clean downloads directory before downloading
        clean_downloads_directory()

        # Download the audio using the sanitized title
        audio_file = download_audio_from_youtube(link, sanitized_title)

        # Construct the path for the downloaded MP3 file
        mp3_file_path = audio_file + ".mp3"
        if os.path.exists(mp3_file_path):
            # Send the audio file with the sanitized title
            with open(mp3_file_path, "rb") as f:
                client.send_audio(chat_id=message.chat.id, audio=f, title=sanitized_title)

            # Remove the file after sending
            os.remove(mp3_file_path)
        else:
            raise Exception(f"Downloaded file not found: {mp3_file_path}")

        # Notify the user upon successful upload
        progress_message.edit_text("✅ Your song is ready! 🎶")
    except Exception as e:
        # Notify the user about any errors
        message.reply_text(f"❌ Failed to download the song. Error: {str(e)}")


# Run the bot
if __name__ == "__main__":
    app.run()
