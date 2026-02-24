import io
import asyncio
import json
import re
import gc
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from faster_whisper import WhisperModel
import torch
from transformers import pipeline
import tensorflow as tf
import numpy as np
import cv2

# --- MEMORY MANAGEMENT ---
whisper_model = None
llm_model = None
emotion_resources = None

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
            llm_model = Llama.from_pretrained(
                repo_id="bartowski/Phi-3-mini-4k-instruct-GGUF",
                filename="*Q4_K_M.gguf",
                verbose=True,
                n_ctx=4096,
                n_gpu_layers=-1
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
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        print("✅ Whisper Loaded.")
    return whisper_model

def unload_emotion():
    global emotion_resources
    if emotion_resources is not None:
        print("🧹 Unloading Emotion Model to free RAM...")
        del emotion_resources
        emotion_resources = None
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        print("✅ Emotion Model Unloaded.")

def load_emotion():
    global emotion_resources
    if emotion_resources is None:
        try:
            print("⏳ Loading RAF-DB Emotion Model (best_model.h5)...")
            
            # Load Keras Model
            model = tf.keras.models.load_model('best_model.h5')
            
            emotion_resources = model
            print("✅ RAF-DB Emotion Model Loaded!")
        except Exception as e:
             print(f"⚠️ Emotion Model Load Failed: {e}")
             return None
             
    return emotion_resources

class AudioProcessor:
    def __init__(self):
        self.buffer = []
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def process_audio(self, audio_chunk: bytes) -> str:
        self.buffer.append(audio_chunk)
        if len(self.buffer) >= 1:
            full_audio = b''.join(self.buffer)
            self.buffer = []
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(self.executor, self._transcribe_sync, full_audio)
            return text
        return ""

    async def flush(self) -> str:
        """Process any remaining audio in the buffer."""
        if not self.buffer:
            return ""
        print(f"🧹 Flushing {len(self.buffer)} remaining chunks...")
        full_audio = b''.join(self.buffer)
        self.buffer = []
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(self.executor, self._transcribe_sync, full_audio)
        return text

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
        self.model = None

    async def generate_interview_questions(self, cv_text: str, job_description: str) -> list[dict]:
        """
        Generate interview questions WITH recommended answers.
        Returns list of dicts: [{"question": "...", "recommended_answer": "..."}]
        """
        loop = asyncio.get_running_loop()
        questions_with_answers = await loop.run_in_executor(
            self.executor,
            self._generate_questions_with_answers_sync,
            cv_text,
            job_description
        )
        unload_llm()
        return questions_with_answers

    def _generate_questions_with_answers_sync(self, cv_text: str, job_description: str) -> list[dict]:
        model = load_llm()
        if model is None:
            return [{"question": "Error: AI Model failed to load.", "recommended_answer": ""}]

        try:
            # Step 1: Generate questions
            questions_prompt = f"""<|user|>
You are an expert HR Manager. Generate 10 interview questions based on the provided Context.
Rules:
1. 4 Easy, 3 Medium, 3 Difficult.
2. Output ONLY a numbered list. No intro/outro text.

CANDIDATE CV: {cv_text[:2000]}

JOB CONTEXT: {job_description[:2500]}
<|end|>
<|assistant|>"""

            output = model(questions_prompt, max_tokens=1024, stop=["<|end|>"], echo=False)
            questions_text = output['choices'][0]['text'].strip()

            # Parse questions
            questions_list = []
            for line in questions_text.split('\n'):
                clean_line = line.strip()
                if re.match(r'^\d+\.', clean_line):
                    q_text = re.sub(r'^\d+\.\s*', '', clean_line)
                    if q_text:
                        questions_list.append(q_text)

            if not questions_list:
                questions_list = [questions_text] if questions_text else ["No questions generated"]

            print(f"✅ Generated {len(questions_list)} questions, now generating recommended answers...")

            # Step 2: Generate recommended answer for each question
            questions_with_answers = []
            for i, question in enumerate(questions_list):
                print(f"📝 Generating answer for Q{i+1}/{len(questions_list)}...")

                answer_prompt = f"""<|user|>
You are an expert interview coach. Provide an ideal answer for this interview question.
The answer should be:
1. Concise (3-5 sentences)
2. Professional and relevant to the candidate's background
3. Include specific examples or achievements from the CV where relevant
4. Use STAR method (Situation, Task, Action, Result) for behavioral questions

CANDIDATE CV SUMMARY: {cv_text[:1500]}
JOB CONTEXT: {job_description[:1000]}
QUESTION: {question}

Provide ONLY the recommended answer, no intro or labels.
<|end|>
<|assistant|>"""

                try:
                    answer_output = model(answer_prompt, max_tokens=350, stop=["<|end|>"], echo=False)
                    recommended_answer = answer_output['choices'][0]['text'].strip()
                    
                    # Clean up the answer
                    recommended_answer = re.sub(
                        r'^(Answer:|Recommended Answer:|Ideal Answer:|Response:)\s*',
                        '',
                        recommended_answer,
                        flags=re.IGNORECASE
                    )
                    print(f"   ✅ Answer generated ({len(recommended_answer)} chars)")

                except Exception as e:
                    print(f"   ⚠️ Error generating answer for Q{i+1}: {e}")
                    recommended_answer = "Answer generation failed."

                questions_with_answers.append({
                    "question": question,
                    "recommended_answer": recommended_answer
                })

            print(f"✅ Generated {len(questions_with_answers)} questions with recommended answers")
            return questions_with_answers

        except Exception as e:
            print(f"❌ Error generating questions: {e}")
            return [{"question": "Error generating questions.", "recommended_answer": ""}]
   
    def install_model (self,instruction):
        """Utility function to pre-install models to avoid latency during actual use."""
        if instruction == "llm":
            print("🚀 Pre-installing models...")
            self.model =load_llm()
        elif instruction == "unload":
            unload_llm()
        print("✅ All models pre-installed and ready!")

    async def evaluate_candidate_response( # don't need it for  now can be used later
        self,
        q_id:int,
        question: str,
        recommended_answer: str,
        candidate_response: str,
        cv_text: str
    ) -> dict:
        """
        Evaluate candidate's response against the recommended answer.
        Returns: {"score": 0-100, "feedback": "...", "strengths": [...], "improvements": [...]}
        """
        loop = asyncio.get_running_loop()
        evaluation = await loop.run_in_executor(
            self.executor,
            self._evaluate_response_sync,
            q_id,
            question,
            recommended_answer,
            candidate_response,
            cv_text
        )
        return evaluation

    def _evaluate_response_sync(
        self,
        q_id:int,
        question: str,
        recommended_answer: str,
        candidate_response: str,
        cv_text: str
    ) -> dict:
        #model = load_llm() # bottle neck is here, we can optimize by keeping the model loaded and reusing it for multiple evaluations instead of loading/unloading every time
                #this can be done by loading llm from session.py before calling evaluate but will loading the llm in session.py work for this file?
        if self.model is None:
            return {"score": 0, "feedback": "AI Model failed to load.", "strengths": [], "improvements": []}

        try:
            prompt = f"""<|user|>
You are an expert interview evaluator. Compare the candidate's response with the ideal answer.

QUESTION: {question}

IDEAL ANSWER: {recommended_answer}

CANDIDATE'S RESPONSE: {candidate_response}

CANDIDATE BACKGROUND: {cv_text[:800]}

Evaluate and respond in this EXACT format (no other text):
SCORE: [number 0-100]
FEEDBACK: [2-3 sentences of constructive feedback]
STRENGTHS: [comma-separated list of what was done well]
IMPROVEMENTS: [comma-separated list of areas to improve]
<|end|>
<|assistant|>"""

            output = self.model(prompt, max_tokens=400, stop=["<|end|>"], echo=False)
            eval_text = output['choices'][0]['text'].strip()

            # Parse evaluation
            score = 50
            feedback = "Evaluation completed."
            strengths = []
            improvements = []

            for line in eval_text.split('\n'):
                line = line.strip()
                if line.upper().startswith('SCORE:'):
                    try:
                        score_match = re.search(r'\d+', line)
                        if score_match:
                            score = min(100, max(0, int(score_match.group())))
                    except:
                        pass
                elif line.upper().startswith('FEEDBACK:'):
                    feedback = line.split(':', 1)[1].strip() if ':' in line else feedback
                elif line.upper().startswith('STRENGTHS:'):
                    strengths_str = line.split(':', 1)[1].strip() if ':' in line else ""
                    strengths = [s.strip() for s in strengths_str.split(',') if s.strip()]
                elif line.upper().startswith('IMPROVEMENTS:'):
                    improvements_str = line.split(':', 1)[1].strip() if ':' in line else ""
                    improvements = [i.strip() for i in improvements_str.split(',') if i.strip()]

            return {
                "question_id": q_id ,
                "score": score,
                "feedback": feedback,
                "strengths": strengths,
                "improvements": improvements
            }

        except Exception as e:
            print(f"❌ Error evaluating response: {e}")
            return {"score": 0, "feedback": f"Evaluation error: {e}", "strengths": [], "improvements": []}

    def evaluate_emotion(self, emotion_label: list, confidence_score:list):
        if self.model is None:
            return {"error": "AI Model failed to load."}
        try:
            prompt = f"""<|user|>
You are an expert interview coach. Evaluate the candidate's emotional state during the interview based on the detected emotion and confidence score.
EMOTION LABEL: {emotion_label}
CONFIDENCE SCORE: {confidence_score}
Provide feedback on how this emotional state might be perceived by interviewers and any recommendations for improvement and respond in this EXACT format (no other text):
PERCEPTION: [2-3 sentences on how this emotion might be perceived]
RECOMMENDATIONS: [2-3 actionable recommendations for the candidate to manage their emotions better]
CONFIDENCE: [Your confidence in this analysis, 0-100%]
<|end|>
<|assistant|>"""
            
            output = self.model(prompt, max_tokens=300, stop=["<|end|>"], echo=False)
            analysis_text = output['choices'][0]['text'].strip()

            perception = "Analysis completed."
            recommendations = []
            confidence = "N/A"

            for line in analysis_text.split('\n'):
                line = line.strip()
                if line.upper().startswith('PERCEPTION:'):
                    perception = line.split(':', 1)[1].strip() if ':' in line else perception
                elif line.upper().startswith('RECOMMENDATIONS:'):
                    recommendations_str = line.split(':', 1)[1].strip() if ':' in line else ""
                    recommendations = [r.strip() for r in recommendations_str.split(',') if r.strip()]
                elif line.upper().startswith('CONFIDENCE:'):
                    confidence = line.split(':', 1)[1].strip() if ':' in line else confidence
            return {
                "perception": perception,
                "recommendations": recommendations,
                "confidence": confidence
            }
        except Exception as e:
            print(f"❌ Error evaluating emotion: {e}")
            return {"error": f"Emotion evaluation error: {e}"}
        

class EmotionDetector:
    def __init__(self):
        # We don't load here to save RAM; we load on the first call to analyze
        print("EmotionDetector initialized (lazy load mode)")
        
        # RAF-DB Specific Labels (based on user info)
        self.labels = ['Surprise', 'Fear', 'Disgust', 'Happy', 'Sad', 'Angry', 'Neutral']

        # Load Haar Cascade
        # We need the path to the XML file. cv2.data.haarcascades helps find it.
        try:
             self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception:
             print("⚠️ Warning: Could not load Haar Cascade. Face detection will be skipped.")
             self.face_cascade = None

    def analyze(self, image_input: Image.Image):
        """
        Input: PIL Image or bytes
        Output: Top emotion classification result from cropped face area
        """
        model = load_emotion()
        if not model:
            return {"error": "Emotion Model not available"}

        try:
            # 1. Convert Input to OpenCV Format (BGR)
            if isinstance(image_input, bytes):
                # If raw bytes from file upload
                nparr = np.frombuffer(image_input, np.uint8)
                image_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif isinstance(image_input, Image.Image):
                # If PIL Image
                image_cv = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
            else:
                 return {"error": "Unsupported image format"}
            
            if image_cv is None:
                return {"error": "Could not decode image"}

            # 2. Face Detection
            # Convert to grayscale for Haar Cascade
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
            
            faces = []
            if self.face_cascade:
                faces = self.face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=1.1, 
                    minNeighbors=5, 
                    minSize=(30, 30)
                )

            # 3. Crop Face (or use full image)
            if len(faces) > 0:
                # Use the largest face found
                (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
                print(f"✅ Face Detected at: x={x}, y={y}, w={w}, h={h}")
                
                # Crop logic
                face_roi = image_cv[y:y+h, x:x+w]
                face_rgb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
            else:
                print("⚠️ No face detected. Using full image.")
                face_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)

            # 4. Preprocess for Model (100x100, Normalized)
            target_size = (100, 100)
            img_resized = cv2.resize(face_rgb, target_size)
            
            img_array = img_resized.astype('float32') / 255.0  # Normalize [0,1]
            img_array = np.expand_dims(img_array, axis=0)      # Add batch dimension -> (1, 100, 100, 3)

            # 5. Predict
            predictions = model.predict(img_array, verbose=0)
            predicted_class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_idx])
            
            label = self.labels[predicted_class_idx] if predicted_class_idx < len(self.labels) else "Unknown"

            print(f"✅ Emotion Detected: {label} (conf: {confidence:.4f})")
            
            return {
                "label": label,
                "score": confidence,
                "all_scores": {self.labels[i]: float(predictions[0][i]) for i in range(len(self.labels))}
            }
                
        except Exception as e:
            print(f"❌ Emotion Prediction Failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

            # 2. Run Prediction
            predictions = model.predict(img_array, verbose=0)
            predicted_class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_idx])
            
            label = self.labels[predicted_class_idx] if predicted_class_idx < len(self.labels) else "Unknown"

            print(f"✅ Emotion Detected: {label} (conf: {confidence:.4f})")
            
            # Format result
            return {
                "label": label,
                "score": confidence,
                "all_scores": {self.labels[i]: float(predictions[0][i]) for i in range(len(self.labels))}
            }
                
        except Exception as e:
            print(f"❌ Emotion Prediction Failed: {e}")
            # Fallback for debugging if shape mismatch
            if "shape" in str(e).lower():
                print("⚠️ Hint: Model input shape mismatch. Try changing target_size to (224, 224).")
            return {"error": str(e)}

# --- TEST IT ---
if __name__ == "__main__":
    try:
        # 1. Initialize
        detector = EmotionDetector()
        
        # 2. Load Local Image
        img_path = "/Users/manishsubedi/Documents/coding/Intraviewer/backend/difficulemotion1.jpg"
        print(f"📸 Loading local image: {img_path}")
        img = Image.open(img_path)
        
        # 3. Analyze
        print("🧠 Analyzing...")
        result = detector.analyze(img)
        
        # 4. Print
        print("\n--- Result ---")
        print(json.dumps(result, indent=2))
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{img_path}' in the current folder.")
    except Exception as e:
        print(f"❌ Error: {e}")