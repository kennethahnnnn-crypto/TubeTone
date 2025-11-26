import os
import subprocess
import uuid
import shutil
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

    # --- COOKIE FIX START ---
    # We copy the secret cookie file to a writable location
    secret_cookie_path = '/etc/secrets/cookies.txt'
    writable_cookie_path = 'cookies_writable.txt'
    
    use_cookies = False
    
    # Check if we are on Render (Secret exists)
    if os.path.exists(secret_cookie_path):
        try:
            shutil.copyfile(secret_cookie_path, writable_cookie_path)
            use_cookies = True
            print("Using Render secret cookies")
        except Exception as e:
            print(f"Cookie copy failed: {e}")
            
    # Fallback: Check if local cookies.txt exists (for testing on Mac)
    elif os.path.exists('cookies.txt'):
        shutil.copyfile('cookies.txt', writable_cookie_path)
        use_cookies = True
        print("Using local cookies")
    # --- COOKIE FIX END ---

    try:
        # 1. Download Audio using yt-dlp
        print(f"Downloading: {url}")
        
        # ... inside the convert() function ...

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/{unique_id}.%(ext)s',
            # NEW: Camouflage as an iOS device to bypass bot checks
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android']
                }
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'nocheckcertificate': True,
        }
        
        # Attach cookie file if we have it (Still good to have as backup)
        if use_cookies:
            ydl_opts['cookiefile'] = writable_cookie_path
        
        # Only add cookiefile if we successfully copied it
        if use_cookies:
            ydl_opts['cookiefile'] = writable_cookie_path

        title = "ringtone"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'ringtone')
            # Sanitize title
            title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()

        # 2. Process Audio using FFmpeg DIRECTLY
        output_filename = f"{DOWNLOAD_FOLDER}/{title[:20]}_ringtone.m4r"
        
        print("Trimming and converting...")
        command = [
            'ffmpeg', 
            '-i', temp_mp3,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:a', 'aac',
            '-b:a', '128k',
            '-f', 'ipod',
            output_filename,
            '-y'
        ]
        
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Clean up the original mp3
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)

        # 4. Schedule cleanup of the ringtone AND the temp cookie file
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
        if os.path.exists(temp_mp3): os.remove(temp_mp3)
        return f"Error processing video: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)