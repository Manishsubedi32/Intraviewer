import httpx
from typing import Dict, Any


async def parse_with_phi3(text: str, mode: str = "cv") -> Dict[str, Any]:
    """Call Ollama (phi3) to parse CV or job description into structured JSON."""
    if mode == "cv":
        prompt = (
            "Extract the following as a JSON object with EXACT keys: "
            '"name" (string), "email" (string or null), "skills" (array of strings), '
            '"experience_years" (integer or null). '
            "Do not add any other keys or explanations. Output ONLY valid JSON.\n\nCV:\n"
            f"{text}"
        )
    else:  # job
        prompt = (
            "Extract the following as a JSON object with EXACT keys: "
            '"role" (string), "required_skills" (array of strings), '
            '"preferred_skills" (array of strings or null), '
            '"min_experience_years" (integer or null). '
            "Do not add any other keys or explanations. Output ONLY valid JSON.\n\nJob:\n"
            f"{text}"
        )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://host.docker.internal:11434/api/generate",
            json={
                "model": "phi3:mini",           # Use faster mini model
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 2048,            # Reduce context length for speed
                    "num_predict": 512,         # Limit output tokens
                    "repeat_penalty": 1.1,
                    "top_k": 10,                # Reduce top-k for faster sampling
                    "top_p": 0.9
                }
            },
            timeout=30.0                        # Reduced timeout
        )
        resp.raise_for_status()
        result = resp.json()["response"]
        # Clean potential markdown
        if result.startswith("```json"):
            result = result[7:result.rfind("```")].strip()
        return eval(result)  # ⚠️ In prod, use json5 or strict JSON fix