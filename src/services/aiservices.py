import io
import asyncio
import re
import gc
from concurrent.futures import ThreadPoolExecutor
from faster_whisper import WhisperModel

# --- MEMORY MANAGEMENT ---
whisper_model = None
llm_model = None

def unload_llm():
    global llm_model
    if llm_model is not None:
        print("🧹 Unloading LLM to free RAM...")
        del llm_model
        llm_model = None
        gc.collect()
        print("✅ LLM Unloaded.")

def load_llm():
    global llm_model
    if llm_model is None:
        unload_whisper()
        try:
            print("🚀 Loading LLM Model (Phi-3 Mini)...")
            from llama_cpp import Llama
            # Phi-3 Mini fits easily in 8GB RAM alongside Docker & macOS
            llm_model = Llama.from_pretrained(
                repo_id="bartowski/Phi-3-mini-4k-instruct-GGUF",
                filename="*Q4_K_M.gguf",
                verbose=True,
                n_ctx=4096,
                n_gpu_layers=-1 # Uses Mac Metal GPU
            )
            print("✅ LLM Loaded.")
        except Exception as e:
            print(f"⚠️ LLM Load Failed: {e}")
            return None
    return llm_model

def unload_whisper():
    global whisper_model
    if whisper_model is not None:
        print("🧹 Unloading Whisper to free RAM...")
        del whisper_model
        whisper_model = None
        gc.collect()
        print("✅ Whisper Unloaded.")

def load_whisper():
    global whisper_model
    if whisper_model is None:
        unload_llm()
        print("🎤 Loading Whisper Model...")
        # 'base' is fast on CPU. If you want higher accuracy, try 'small'
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        print("✅ Whisper Loaded.")
    return whisper_model

class AudioProcessor:
    def __init__(self):
        self.buffer = []
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def process_audio(self, audio_chunk: bytes) -> str:
        self.buffer.append(audio_chunk)
        if len(self.buffer) >= 15:
            full_audio = b''.join(self.buffer)
            self.buffer = [] 
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(self.executor, self._transcribe_sync, full_audio)
            return text
        return ""

    def _transcribe_sync(self, audio_bytes: bytes) -> str:
        try:
            model = load_whisper()
            audio_file = io.BytesIO(audio_bytes)
            segments, _ = model.transcribe(audio_file, beam_size=5)
            return "".join([segment.text for segment in segments])
        except Exception as e:
            print(f"Local Transcription Error: {e}")
            return ""

class LLMService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def generate_interview_questions(self, cv_text: str, job_description: str) -> list[str]:
        loop = asyncio.get_running_loop()
        questions = await loop.run_in_executor(self.executor, self._generate_questions_sync, cv_text, job_description)
        unload_llm()
        return questions

    def _generate_questions_sync(self, cv_text: str, job_description: str) -> list[str]:
        model = load_llm()
        if model is None:
            return ["Error: AI Model failed to load."]

        try:
            # Phi-3 Prompt Format
            prompt = f"""<|user|>
You are an expert HR Manager. Generate 10 interview questions based on the provided Context.
Rules:
1. 4 Technical, 3 Behavioral, 3 Situational.
2. Output ONLY a numbered list. No intro/outro text.

CANDIDATE CV: {cv_text[:2000]}

JOB CONTEXT: 
{job_description[:3000]}
<|end|>
<|assistant|>"""

            output = model(prompt, max_tokens=1024, stop=["<|end|>"], echo=False)
            generated_text = output['choices'][0]['text'].strip()
            
            questions = []
            for line in generated_text.split('\n'):
                clean_line = line.strip()
                if re.match(r'^\d+\.', clean_line):
                    q_text = re.sub(r'^\d+\.\s*', '', clean_line)
                    questions.append(q_text)
            
            return questions if questions else [generated_text]

        except Exception as e:
            print(f"Error generating questions: {e}")
            return ["Error generating questions."]