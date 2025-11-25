import os
import subprocess
import uuid
from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

# CONFIGURATION
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url')
    # Validate and convert inputs
    try:
        start_time = float(request.form.get('start_time', 0))
        duration = float(request.form.get('duration', 20))
    except ValueError:
        return "Invalid time format", 400

    if duration > 30: duration = 30 # Force max 30s
    
    unique_id = str(uuid.uuid4())
    temp_mp3 = f'{DOWNLOAD_FOLDER}/{unique_id}.mp3'
    output_filename = ""

    try:
        # 1. Download Audio using yt-dlp
        print(f"Downloading: {url}")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/{unique_id}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        title = "ringtone"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'ringtone')
            # Sanitize title
            title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()

        # 2. Process Audio using FFmpeg DIRECTLY (Bypassing pydub)
        # We use the system's ffmpeg command we installed via Homebrew
        output_filename = f"{DOWNLOAD_FOLDER}/{title[:20]}_ringtone.m4r"
        
        print("Trimming and converting...")
        # Command: ffmpeg -i input.mp3 -ss START -t DURATION -c:a aac -f ipod output.m4r -y
        command = [
            'ffmpeg', 
            '-i', temp_mp3,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:a', 'aac',      # Apple audio codec
            '-b:a', '128k',     # Quality
            '-f', 'ipod',       # Container format for m4r/m4a
            output_filename,
            '-y'                # Overwrite if exists
        ]
        
        # Run the command and hide the messy logs
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Clean up the original mp3
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)

        # 4. Schedule cleanup of the ringtone file
        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(output_filename):
                    os.remove(output_filename)
            except Exception as e:
                print(f"Error removing file: {e}")
            return response

        # 5. Send file
        return send_file(
            output_filename,
            as_attachment=True,
            download_name=f"{title}_ringtone.m4r",
            mimetype="audio/x-m4r"
        )

    except Exception as e:
        print(f"Error: {e}")
        # Clean up if something failed
        if os.path.exists(temp_mp3): os.remove(temp_mp3)
        return f"Error processing video: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)