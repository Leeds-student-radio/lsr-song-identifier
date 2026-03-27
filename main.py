import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shazamio import Shazam

app = FastAPI()

# --- NEW: Dictionary to track the last song recognized per stream ---
last_seen_songs = {}

# This is CRITICAL. It allows your GitHub Pages site to talk to this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.thisislsr.com/"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

shazam = Shazam()

@app.get("/identify")
async def identify_song(stream_url: str):
    try:
        # 1. Grab a small chunk (~150KB) of the live stream
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', stream_url) as response:
                with open("temp_stream.mp3", "wb") as f:
                    bytes_read = 0
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                        bytes_read += len(chunk)
                        if bytes_read > 150000: # Roughly 5-10 seconds of audio
                            break
        
        # 2. Send that chunk to Shazam
        out = await shazam.recognize("temp_stream.mp3")
        
        # 3. Clean up the temp file
        if os.path.exists("temp_stream.mp3"):
            os.remove("temp_stream.mp3")

        # 4. Extract the song info
        if 'track' in out:
            track_info = out['track']
            
            title = track_info.get('title', 'Unknown Title')
            artist = track_info.get('subtitle', 'Unknown Artist')
            image_url = track_info.get('images', {}).get('coverart', '')
            
            # --- NEW LOGIC START ---
            # Create a unique identifier for the current song
            current_song_id = f"{title} - {artist}"
            
            # Check if this song is the exact same as the last one we heard on this stream
            if last_seen_songs.get(stream_url) == current_song_id:
                is_new_song = False
            else:
                is_new_song = True
                # Update our tracking dictionary with the new song
                last_seen_songs[stream_url] = current_song_id
            # --- NEW LOGIC END ---
            
            return {
                "success": True, 
                "is_new_song": is_new_song,  # Your frontend can check this flag!
                "title": title, 
                "artist": artist,
                "image": image_url
            }
        else:
            return {"success": False, "message": "Song not recognized."}

    except Exception as e:
        return {"success": False, "message": str(e)}
