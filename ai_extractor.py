"""
Unified AI Extraction Engine for Job Scraping Pipeline
Supports:
1. Mistral API (pixtral-12b-2409 / mistral-small-latest) [PRIMARY]
2. Gemini Native API (Rotates across all active keys in config_gemini.json)
3. OpenRouter API (Fallback)

Includes:
- Truncation repair for incomplete JSON responses (repair_json)
- Multimodal Vision (Text + Single/Multiple Images)
- Dual/Triple contact channel preservation (Link + Email + Phone)
- QR payload integration
"""

import os
import sys
import json
import base64
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

def load_keys_from_env(multi_env, single_env=None, config_key=None):
    val = os.environ.get(multi_env, "") or (os.environ.get(single_env, "") if single_env else "")
    if val:
        return [k.strip() for k in val.split(",") if k.strip()]
    
    if config_key:
        possible_paths = [
            os.path.join(os.getcwd(), "config_keys.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_keys.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config_keys.json")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        keys = data.get(config_key, [])
                        if keys:
                            return keys
                except Exception:
                    pass
    return []

def get_mime_type(image_path):
    ext = os.path.splitext(image_path)[1].lower()
    if ext == '.png':
        return 'image/png'
    elif ext == '.webp':
        return 'image/webp'
    elif ext == '.bmp':
        return 'image/bmp'
    return 'image/jpeg'

def load_gemini_keys():
    env_keys = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY")
    if env_keys:
        return [k.strip() for k in env_keys.split(",") if k.strip()]
    
    possible_paths = [
        os.path.join(os.getcwd(), "config_gemini.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_gemini.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config_gemini.json")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    keys = data.get("api_keys", [])
                    if keys:
                        return keys
            except Exception:
                pass
    return []

SYSTEM_PROMPT = (
    "Extract all job postings from the provided flyer image or text.\n"
    "Return ONLY a valid JSON object in this exact format:\n"
    "{\n"
    '  "jobs": [\n'
    '    {\n'
    '      "company": "Company Name or null",\n'
    '      "role": "Job Role or null",\n'
    '      "experience": "Experience (e.g. Fresher, 1-5 Yrs) or null",\n'
    '      "location": "City Name ONLY (e.g. Bangalore, Hyderabad) or null",\n'
    '      "apply_link": "Web URL (https://...) or null",\n'
    '      "contact_email": "HR Email or null",\n'
    '      "contact_phone": "Mobile or WhatsApp number or null",\n'
    '      "is_walkin": true/false,\n'
    '      "walkin_date": "Date or null",\n'
    '      "walkin_time": "Time or null",\n'
    '      "walkin_venue": "Short area/city or null",\n'
    '      "reason": "Max 5 words note"\n'
    '    }\n'
    '  ]\n'
    "}\n"
    "If not a job posting, return: {\"none\": true}\n"
    "RULES:\n"
    "1. Extract EACH job role as a separate item in 'jobs' array.\n"
    "2. If multiple contact channels exist (Web Apply Link + Email + Mobile Phone), EXTRACT ALL OF THEM!\n"
    "3. Keep text concise to prevent truncation.\n"
)

def repair_json(raw_text):
    if not raw_text or not isinstance(raw_text, str):
        return None
    text = raw_text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    
    last_brace = text.rfind("}")
    if last_brace != -1:
        repaired = text[:last_brace+1] + "\n  ]\n}"
        try:
            return json.loads(repaired)
        except Exception:
            pass
    return None

def extract_job_data(text_input="", image_paths=None):
    """
    Unified extraction calling Mistral -> Gemini Native -> OpenRouter.
    Returns: dict with 'jobs' array or 'none': True
    """
    image_paths = image_paths or []
    if isinstance(image_paths, str):
        image_paths = [image_paths]

    valid_images = [p for p in image_paths if os.path.exists(p)]

    # ── 1. TRY MISTRAL API (PRIMARY - FAST & HIGH CAPACITY) ──
    mistral_keys = load_keys_from_env("MISTRAL_API_KEYS", "MISTRAL_API_KEY", "mistral_keys")
    for m_key in mistral_keys:
        try:
            url_m = "https://api.mistral.ai/v1/chat/completions"
            headers_m = {
                "Authorization": f"Bearer {m_key}",
                "Content-Type": "application/json"
            }
            
            content_list = []
            for img_path in valid_images:
                mime = get_mime_type(img_path)
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                content_list.append({
                    "type": "image_url",
                    "image_url": f"data:{mime};base64,{b64}"
                })
            
            user_text = SYSTEM_PROMPT
            if text_input:
                user_text += "\n\nINPUT TEXT TO PROCESS:\n" + text_input
            
            content_list.append({"type": "text", "text": user_text})

            model_m = "pixtral-12b-2409" if valid_images else "mistral-small-latest"
            payload_m = {
                "model": model_m,
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": content_list}],
                "response_format": {"type": "json_object"}
            }
            
            res_m = requests.post(url_m, headers=headers_m, json=payload_m, timeout=60)
            if res_m.status_code == 200:
                resp_text = res_m.json()["choices"][0]["message"]["content"].strip()
                parsed = repair_json(resp_text)
                if parsed:
                    return parsed
            elif res_m.status_code == 429:
                continue
        except Exception:
            continue

    # ── 2. TRY GEMINI NATIVE API (SECONDARY - KEY ROTATION) ──
    gemini_keys = load_gemini_keys()
    parts = []
    for img_path in valid_images:
        mime = get_mime_type(img_path)
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        parts.append({"inlineData": {"mimeType": mime, "data": b64}})
    
    prompt_str = SYSTEM_PROMPT
    if text_input:
        prompt_str += "\n\nINPUT TEXT TO PROCESS:\n" + text_input
    parts.append({"text": prompt_str})

    payload_g = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }

    for k_val in gemini_keys:
        for g_model in ["gemini-2.5-flash", "gemini-2.0-flash"]:
            url_g = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={k_val}"
            try:
                res_g = requests.post(url_g, json=payload_g, timeout=60)
                if res_g.status_code == 200:
                    text_resp = (
                        res_g.json().get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                        .strip()
                    )
                    parsed = repair_json(text_resp)
                    if parsed:
                        return parsed
                elif res_g.status_code == 429:
                    time.sleep(1)
                    continue
            except Exception:
                continue

    # ── 3. TRY GROQ API (FOR FAST TEXT MESSAGES) ──
    groq_keys = load_keys_from_env("GROQ_API_KEYS", "GROQ_API_KEY", "groq_keys")
    if text_input and not valid_images:
        for gr_key in groq_keys:
            try:
                url_gr = "https://api.groq.com/openai/v1/chat/completions"
                headers_gr = {
                    "Authorization": f"Bearer {gr_key}",
                    "Content-Type": "application/json"
                }
                payload_gr = {
                    "model": "qwen/qwen3.6-27b",
                    "max_tokens": 1500,
                    "messages": [{"role": "user", "content": SYSTEM_PROMPT + "\n\nINPUT TEXT TO PROCESS:\n" + text_input}],
                    "response_format": {"type": "json_object"}
                }
                res_gr = requests.post(url_gr, headers=headers_gr, json=payload_gr, timeout=30)
                if res_gr.status_code == 200:
                    resp_text = res_gr.json()["choices"][0]["message"]["content"].strip()
                    parsed = repair_json(resp_text)
                    if parsed:
                        return parsed
                elif res_gr.status_code == 429:
                    continue
            except Exception:
                continue

    # ── 4. TRY OPENROUTER API (TERTIARY FALLBACK) ──
    openrouter_keys = load_keys_from_env("OPENROUTER_API_KEYS", "OPENROUTER_API_KEY", "openrouter_keys")
    for or_key in openrouter_keys:
        try:
            url_or = "https://openrouter.ai/api/v1/chat/completions"
            headers_or = {
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json"
            }
            content_or = []
            for img_path in valid_images:
                mime = get_mime_type(img_path)
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                content_or.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
            content_or.append({"type": "text", "text": prompt_str})

            payload_or = {
                "model": "google/gemini-2.5-flash",
                "max_tokens": 800,
                "messages": [{"role": "user", "content": content_or}],
                "response_format": {"type": "json_object"}
            }
            res_or = requests.post(url_or, headers=headers_or, json=payload_or, timeout=60)
            if res_or.status_code == 200:
                resp_text = res_or.json()["choices"][0]["message"]["content"].strip()
                parsed = repair_json(resp_text)
                if parsed:
                    return parsed
            elif res_or.status_code in [402, 429]:
                continue
        except Exception:
            continue

    return {"none": True}
