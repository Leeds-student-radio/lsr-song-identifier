import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shazamio import Shazam

app = FastAPI()

# This is CRITICAL. It allows your GitHub Pages site to talk to this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In the future, you can change "*" to your actual website URL for security
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
            return {
                "success": True, 
                "title": out['track']['title'], 
                "artist": out['track']['subtitle']
            }
        else:
            return {"success": False, "message": "Song not recognized."}

    except Exception as e:
        return {"success": False, "message": str(e)}
