import httpx # we are tunneling to colab server using ngrok

class AudioProcessor:
    def __init__(self):
        self.buffer = []
        
        #self.COLAB_URL = "https://uncontemporary-jakobe-brumous.ngrok-free.dev"
        self.COLAB_URL = "https://kristian-waggish-underfoot.ngrok-free.dev"

    async def process_audio(self, audio_chunk: bytes) -> str:
        self.buffer.append(audio_chunk)
        

        if len(self.buffer) >= 15:
            full_audio = b''.join(self.buffer)
            self.buffer = []
            
            async with httpx.AsyncClient() as client:
                try:
                    
                    files = {'file': ('audio.wav', full_audio, 'audio/wav')}
                    response = await client.post(self.COLAB_URL, files=files, timeout=5.0)
                    
                    if response.status_code == 200:
                        return response.json().get("text", "")
                except Exception as e:
                    print(f"Colab Error: {e}")
                    return ""
        return ""