import os
import sys
import re
import json
import time
import base64
import shutil
import glob
from datetime import datetime, timezone, timedelta
import requests
from PIL import Image

# Force UTF-8 stdout on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Import our existing database storage & classification helpers
try:
    import storage
except ImportError:
    storage = None
    print("⚠️ Warning: storage.py not found in the current directory.")

try:
    import role_classifier
except ImportError:
    role_classifier = None
    print("⚠️ Warning: role_classifier.py not found in the current directory.")

# ---------------------------------------------------------------------------
# SECURE CONFIGURATION (Loads from Secrets/Environment Variables)
# ---------------------------------------------------------------------------
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. API Credentials (GitHub Secret / Env)
api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")

# Fallback to local config for local runs
if not api_id or not api_hash:
    config_paths = [
        os.path.join(WORKSPACE_DIR, "config_telegram.json"),
    ]
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    config_data = json.load(f)
                api_id = api_id or config_data.get("api_id")
                api_hash = api_hash or config_data.get("api_hash")
                break
            except Exception as e:
                print(f"⚠️ Failed to parse config file {path}: {e}")

if not api_id or not api_hash:
    raise ValueError(
        "❌ Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set as environment variables "
        "or provided in a local config_telegram.json file."
    )

# Convert api_id to int
try:
    api_id = int(api_id)
except Exception as e:
    raise ValueError(f"❌ Error: TELEGRAM_API_ID must be a valid integer: {e}")

# 2. Session Recovery (GitHub Secret - Base64 encoded string)
SESSION_NAME = "secure_telegram_session"
SESSION_FILE = os.path.join(WORKSPACE_DIR, f"{SESSION_NAME}.session")

base64_session = os.environ.get("TELEGRAM_SESSION_BASE64")

# Local fallback to base64_session.txt if env var is empty
base64_file = os.path.join(WORKSPACE_DIR, "base64_session.txt")
if not base64_session and os.path.exists(base64_file):
    try:
        with open(base64_file, "r") as f:
            base64_session = f.read().strip()
        print("✅ Loaded Base64 session string from local base64_session.txt file.")
    except Exception as e:
        print(f"⚠️ Failed to read local base64_session.txt: {e}")

if base64_session:
    try:
        # Pad base64 string if needed
        missing_padding = len(base64_session) % 4
        if missing_padding:
            base64_session += '=' * (4 - missing_padding)

        session_bytes = base64.b64decode(base64_session)
        with open(SESSION_FILE, "wb") as f:
            f.write(session_bytes)
        print("✅ Reconstructed Telegram session from Base64 string.")
    except Exception as e:
        print(f"❌ Failed to decode Base64 session: {e}")
else:
    # Local fallback: try copying from older project if running locally
    SESSION_SOURCE = os.path.join(WORKSPACE_DIR, "session_name.session")
    if not os.path.exists(SESSION_FILE) and os.path.exists(SESSION_SOURCE):
        shutil.copy(SESSION_SOURCE, SESSION_FILE)
        print("🔑 Copied local session file for development run.")

# 3. Target Channels List (GitHub Variable or Env)
channels_env = os.environ.get("TELEGRAM_CHANNELS")
if channels_env:
    channels_list = [c.strip() for c in channels_env.split(",") if c.strip()]
    print(f"📋 Loaded {len(channels_list)} channels from GitHub Variable.")
else:
    # Local fallback: load from file or defaults
    CHANNELS_FILE = os.path.join(WORKSPACE_DIR, "telegram_channels.json")
    default_channels = ["kickcharm", "itreferrals", "PLACEMENTLELO"]
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as f:
            channels_list = json.load(f).get("channels", default_channels)
    else:
        channels_list = default_channels
    print(f"📋 Loaded {len(channels_list)} channels from local configuration.")

# 4. Progress Files
LAST_SEEN_FILE = os.path.join(WORKSPACE_DIR, "last_seen_telegram.json")
PROGRESS_FILE = os.path.join(WORKSPACE_DIR, "telegram_progress.json")

if os.path.exists(LAST_SEEN_FILE):
    with open(LAST_SEEN_FILE, "r") as f:
        last_seen_ids = json.load(f)
else:
    last_seen_ids = {}

# 5. Runtime Guard — stop before GitHub Actions 6h limit
MAX_RUNTIME_SECONDS = 5 * 3600 + 50 * 60  # 5 hours 50 minutes
PIPELINE_START_TIME = time.time()

# ---------------------------------------------------------------------------
# OCR ENGINE (PaddleOCR — lazy init)
# ---------------------------------------------------------------------------
ocr_engine = None

def get_ocr_engine():
    global ocr_engine
    if ocr_engine is None:
        print("🤖 Initializing PaddleOCR engine...")
        try:
            from paddleocr import PaddleOCR
            import logging
            logging.getLogger("ppocr").setLevel(logging.WARNING)
            # Disable MKLDNN to prevent NotImplementedError on Windows/CPU
            ocr_engine = PaddleOCR(use_textline_orientation=True, lang='en', enable_mkldnn=False)
        except Exception as e:
            print(f"❌ Failed to load PaddleOCR: {e}")
    return ocr_engine

def extract_text_from_image(image_path):
    engine = get_ocr_engine()
    if not engine:
        return ""
    try:
        print(f"📷 Running OCR on {os.path.basename(image_path)}...")
        result = engine.predict(image_path)
        if not result or not isinstance(result, list) or len(result) == 0:
            return ""

        first_res = result[0]
        # Handle new PaddleX list-of-dict format
        if isinstance(first_res, dict) and "rec_texts" in first_res:
            return "\n".join(first_res["rec_texts"])

        # Fallback to legacy list-of-list format
        text_lines = []
        if isinstance(first_res, list):
            for line in first_res:
                if isinstance(line, list) and len(line) > 1 and isinstance(line[1], (list, tuple)):
                    text_lines.append(line[1][0])
        return "\n".join(text_lines)
    except Exception as e:
        print(f"⚠️ OCR processing error: {e}")
        return ""

# ---------------------------------------------------------------------------
# GEMINI 2.5 FLASH EXTRACTION — 6-key round-robin rotation
# ---------------------------------------------------------------------------
GEMINI_API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEYS", "").split(",") if k.strip()]
GEMINI_MODEL = "gemini-2.5-flash"
_gemini_call_counter = 0

# Fallback for local dev: load from config file
if not GEMINI_API_KEYS:
    _gemini_config = os.path.join(WORKSPACE_DIR, "config_gemini.json")
    if os.path.exists(_gemini_config):
        try:
            with open(_gemini_config, "r") as f:
                GEMINI_API_KEYS = json.load(f).get("api_keys", [])
        except Exception:
            pass

if not GEMINI_API_KEYS:
    print("⚠️ Warning: No Gemini API keys found. Set GEMINI_API_KEYS env or config_gemini.json.")

SYSTEM_PROMPT = (
    "You are an AI assistant specialized in extracting job details from text or image flyers. "
    "Analyze the provided text. A single message MAY CONTAIN MULTIPLE JOB OPENINGS.\n\n"
    "If the text is NOT a job posting (e.g., greetings, ads, memes, promotions, "
    "casual chat, motivational quotes, news), return exactly: {\"none\": true}\n\n"
    "If the text IS or CONTAINS job postings, return a JSON object with a 'jobs' array:\n"
    "{\n"
    "  \"jobs\": [\n"
    "    {\n"
    "      \"company\": \"Company Name or null\",\n"
    "      \"role\": \"Job Role or null\",\n"
    "      \"qualification\": \"Qualification or null\",\n"
    "      \"experience\": \"Experience requirement or null\",\n"
    "      \"salary\": \"Salary or null\",\n"
    "      \"location\": \"City Name ONLY or null if not mentioned\",\n"
    "      \"apply_link\": \"Web URL (https://...) or null\",\n"
    "      \"contact_email\": \"HR Email address (e.g. hr@company.com) or null\",\n"
    "      \"contact_phone\": \"Mobile or WhatsApp number (e.g. +91 9876543210) or null\",\n"
    "      \"last_date\": \"Deadline or null\",\n"
    "      \"is_walkin\": true/false,\n"
    "      \"walkin_date\": \"Walk-in Date or null\"\n"
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- If a key is missing, set its value to null.\n"
    "- 'apply_link', 'contact_email', and 'contact_phone': If multiple channels exist (Web Apply Link + Email + Mobile Phone), YOU MUST EXTRACT ALL OF THEM! Never omit any contact channel.\n"
    "- Experience should be short strings like 'Fresher', '1-5 Yrs', '2+ Yrs' or null.\n"
    "- 'is_walkin' should be true if this is a physical walk-in interview / drive, otherwise false.\n"
    "- Do NOT add markdown formatting, backticks, explanation, or text outside the JSON."
)

def _call_gemini(text):
    """Single Gemini API call with round-robin key rotation. Returns parsed JSON dict or None."""
    global _gemini_call_counter

    if not GEMINI_API_KEYS:
        print("    ❌ No Gemini API keys available!")
        return None

    key = GEMINI_API_KEYS[_gemini_call_counter % len(GEMINI_API_KEYS)]
    key_idx = _gemini_call_counter % len(GEMINI_API_KEYS) + 1
    _gemini_call_counter += 1

    # Try primary model first, fall back to gemini-2.0-flash if 404
    models_to_try = [GEMINI_MODEL, "gemini-2.0-flash"]

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\nText to analyze:\n" + text}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                content = (
                    result.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                return json.loads(content)
            elif response.status_code == 404:
                # Model not available for this key — try fallback model
                continue
            elif response.status_code == 429:
                print(f"    ⚠️ Gemini key#{key_idx} rate-limited (429). Waiting 5s...")
                time.sleep(5)
            else:
                print(f"    Gemini status error {response.status_code} (key#{key_idx})")
        except json.JSONDecodeError:
            print(f"    Gemini returned non-JSON response (key#{key_idx})")
        except Exception as e:
            print(f"    Gemini extraction error: {e}")
    return None


def extract_job_with_gemini(text, image_paths=None, max_retries=3):
    """
    Extract job data using Unified AI Extractor (Mistral -> Gemini -> Groq -> OpenRouter).
    Returns:
        dict  — valid job data dict with 'jobs' array
        "NONE" — AI determined this is not a job posting
        None — extraction failed
    """
    try:
        from ai_extractor import extract_job_data
        result = extract_job_data(text_input=text, image_paths=image_paths)
        if isinstance(result, dict) and result.get("none") is True:
            return "NONE"
        if isinstance(result, dict) and "jobs" in result and isinstance(result["jobs"], list):
            valid_jobs = [j for j in result["jobs"] if isinstance(j, dict) and (j.get("role") or j.get("company"))]
            if valid_jobs:
                return {"jobs": valid_jobs}
        if isinstance(result, dict) and (result.get("role") or result.get("company")):
            return {"jobs": [result]}
    except Exception as e:
        print(f"    AI extraction error: {e}")
    return None

# ---------------------------------------------------------------------------
# 20-DAY CLEANUP — remove stale TELEGRAM jobs only from all_jobs_*.json
# ---------------------------------------------------------------------------
def cleanup_old_jobs(max_age_days=20):
    """Remove ONLY Telegram-sourced jobs older than max_age_days. Portal jobs are untouched."""
    print(f"\n🧹 Running cleanup: removing Telegram jobs older than {max_age_days} days...")

    cutoff_date = (datetime.now() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    chunk_files = storage.get_all_chunk_files() if storage else []

    if not chunk_files:
        print("  No chunk files found, skipping cleanup.")
        return

    total_before = 0
    telegram_removed = 0
    all_clean_jobs = []

    for f in chunk_files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                jobs = json.load(fh)
                total_before += len(jobs)
                for j in jobs:
                    source = (j.get("platform") or j.get("source") or "").lower()
                    # Only clean up Telegram jobs — keep ALL other sources
                    if source in ("telegram", "telegram_message", "telegram_post"):
                        date_str = storage.get_job_date(j)
                        if date_str and len(date_str) >= 10 and date_str[:10] < cutoff_date:
                            telegram_removed += 1
                            continue  # Skip this stale Telegram job
                    all_clean_jobs.append(j)
        except Exception as e:
            print(f"  Error reading {f}: {e}")

    if telegram_removed == 0:
        print(f"  No stale Telegram jobs found. All {total_before} jobs retained.")
        return

    # Rewrite chunk files
    for f in chunk_files:
        try:
            os.remove(f)
        except Exception:
            pass

    # Write cleaned jobs back using storage's MAX_FILE_SIZE chunking
    current_chunk = 1
    current_data = []
    current_bytes = 2  # for '[]'

    for j in all_clean_jobs:
        j_str = json.dumps(j, separators=(',', ':'))
        j_bytes = len(j_str.encode('utf-8'))
        comma = 1 if current_data else 0

        if current_bytes + j_bytes + comma > storage.MAX_FILE_SIZE:
            with open(f"all_jobs_{current_chunk}.json", 'w', encoding='utf-8') as fh:
                json.dump(current_data, fh, separators=(',', ':'))
            current_chunk += 1
            current_data = [j]
            current_bytes = 2 + j_bytes
        else:
            current_data.append(j)
            current_bytes += j_bytes + comma

    if current_data:
        with open(f"all_jobs_{current_chunk}.json", 'w', encoding='utf-8') as fh:
            json.dump(current_data, fh, separators=(',', ':'))

    # Rebuild jobs_by_role/
    role_dir = os.path.join(WORKSPACE_DIR, "jobs_by_role")
    if os.path.exists(role_dir):
        shutil.rmtree(role_dir)
    os.makedirs(role_dir, exist_ok=True)

    grouped = {}
    role_counts = {}
    for j in all_clean_jobs:
        cat = j.get('role_category', 'Other')
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(j)
        role_counts[cat] = role_counts.get(cat, 0) + 1

    for cat, cat_jobs in grouped.items():
        filename = storage.get_category_filename(cat)
        filepath = os.path.join(role_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as fh:
            json.dump(cat_jobs, fh, separators=(',', ':'))

    # Update role_index.json
    with open(os.path.join(WORKSPACE_DIR, "role_index.json"), 'w', encoding='utf-8') as fh:
        json.dump(role_counts, fh, indent=2)

    print(f"  ✅ Cleanup complete: removed {telegram_removed} stale Telegram jobs ({total_before} → {len(all_clean_jobs)})")

# ---------------------------------------------------------------------------
# PROGRESS TRACKING — for auto-restart
# ---------------------------------------------------------------------------
def save_progress(finished=False, current_channel_idx=0):
    """Save pipeline progress for auto-restart support."""
    progress = {
        "finished": finished,
        "current_channel_idx": current_channel_idx,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def load_progress():
    """Load pipeline progress. Returns starting channel index."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                data = json.load(f)
            if data.get("finished"):
                return 0  # Start fresh if last run finished
            return data.get("current_channel_idx", 0)
        except Exception:
            pass
    return 0

# ---------------------------------------------------------------------------
# MAIN SCRAPING RUNNER
# ---------------------------------------------------------------------------
async def run_pipeline():
    from telethon import TelegramClient

    # Use session path without .session suffix for telethon
    session_run_path = SESSION_FILE[:-8] if SESSION_FILE.endswith(".session") else SESSION_FILE
    print(f"🚀 Starting Telegram Jobs Pipeline using session: {session_run_path}")
    print(f"📋 Channels to scrape: {len(channels_list)}")
    print(f"⏰ Max runtime: {MAX_RUNTIME_SECONDS // 3600}h {(MAX_RUNTIME_SECONDS % 3600) // 60}m")

    # Run 20-day cleanup first
    if storage:
        cleanup_old_jobs(max_age_days=20)

    # Setup temp media dir
    temp_media_dir = os.path.join(WORKSPACE_DIR, "temp_telegram_media")
    os.makedirs(temp_media_dir, exist_ok=True)

    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    start_of_day_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    today_cutoff = start_of_day_ist - timedelta(hours=5, minutes=30)
    new_jobs_stored = 0
    messages_processed = 0
    messages_skipped_none = 0
    messages_failed = 0
    debug_messages = []  # Store most recent skipped/failed messages for debugging (FIFO)
    DEBUG_MAX = 20

    # Resume from last checkpoint if the previous run was interrupted
    start_channel_idx = load_progress()
    if start_channel_idx > 0:
        print(f"📍 Resuming from channel index {start_channel_idx} (skipping {start_channel_idx} already-processed channels)")

    try:
        async with TelegramClient(session_run_path, api_id, api_hash) as client:
            for ch_idx, channel in enumerate(channels_list):
                # Skip already-processed channels from previous run
                if ch_idx < start_channel_idx:
                    continue

                # Runtime guard
                elapsed = time.time() - PIPELINE_START_TIME
                if elapsed > MAX_RUNTIME_SECONDS:
                    print(f"\n⏰ Runtime limit reached ({elapsed/3600:.1f}h). Saving progress and stopping.")
                    save_progress(finished=False, current_channel_idx=ch_idx)
                    break

                print(f"\n📂 [{ch_idx+1}/{len(channels_list)}] Checking channel: @{channel} ...")
                try:
                    entity = await client.get_entity(channel)
                except Exception as ce:
                    print(f"  ❌ Could not resolve channel @{channel}: {ce}")
                    continue

                last_id = last_seen_ids.get(channel, 0)
                messages_to_process = []

                # Fetch up to 50 recent messages
                async for msg in client.iter_messages(entity, limit=50):
                    if msg.id <= last_id:
                        break
                    if msg.date < today_cutoff:
                        break
                    messages_to_process.append(msg)

                # Process oldest first to preserve timeline order
                messages_to_process.reverse()
                print(f"  Found {len(messages_to_process)} new messages.")

                for msg in messages_to_process:
                    # Runtime guard per-message
                    if time.time() - PIPELINE_START_TIME > MAX_RUNTIME_SECONDS:
                        print(f"  ⏰ Runtime limit reached mid-channel. Stopping.")
                        save_progress(finished=False, current_channel_idx=ch_idx)
                        break

                    raw_text = msg.text or ""
                    has_image = False  # Track if this message has image content

                    # Check for image media to perform OCR and QR Code extraction
                    qr_result = None
                    if msg.media:
                        try:
                            file_path = await client.download_media(msg, file=temp_media_dir)
                            if file_path:
                                ext = os.path.splitext(file_path)[1].lower()
                                if ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
                                    has_image = True
                                    
                                    # 1. Extract text from image via PaddleOCR
                                    ocr_text = extract_text_from_image(file_path)
                                    if ocr_text:
                                        raw_text += "\n" + ocr_text

                                    # 2. Extract QR code payload via cv2/pyzbar
                                    try:
                                        from qr_detector import detect_and_decode_qr
                                        qr_result = detect_and_decode_qr(file_path)
                                        if qr_result.get("qr_codes"):
                                            qr_text_payloads = [c["raw_data"] for c in qr_result["qr_codes"] if c.get("raw_data")]
                                            if qr_text_payloads:
                                                raw_text += "\n[Decoded QR Code Link/Payload]: " + " | ".join(qr_text_payloads)
                                                print(f"  📱 Decoded {len(qr_text_payloads)} QR Code payload(s) from flyer image.")
                                    except Exception as qr_err:
                                        print(f"  ⚠️ QR decoding error: {qr_err}")

                                try:
                                    os.remove(file_path)
                                except:
                                    pass
                        except Exception as dl_err:
                            print(f"  ⚠️ Media download error: {dl_err}")

                    if not raw_text.strip():
                        last_seen_ids[channel] = msg.id
                        save_last_seen()
                        continue

                    # Determine message type: post (image) or message (text)
                    telegram_type = "telegram_post" if has_image else "telegram_message"
                    telegram_post_url = f"https://t.me/{channel}/{msg.id}"

                    # Analyze text with Gemini 2.5 Flash (round-robin key rotation)
                    messages_processed += 1
                    print(f"  Analyzing {telegram_type.replace('telegram_', '')} {msg.id} with Gemini 2.5 Flash...")
                    job_result = extract_job_with_gemini(raw_text)

                    # Handle non-job messages
                    if job_result == "NONE":
                        messages_skipped_none += 1
                        print(f"    🚫 Not a job posting — skipped.")
                        debug_messages.append({
                            "type": "non_job_skipped",
                            "channel": channel,
                            "msg_id": msg.id,
                            "text": raw_text[:500],
                            "timestamp": msg.date.isoformat() if msg.date else None
                        })
                        if len(debug_messages) > DEBUG_MAX:
                            debug_messages.pop(0)
                        last_seen_ids[channel] = msg.id
                        save_last_seen()
                        continue

                    # Handle extraction failure
                    if job_result is None:
                        messages_failed += 1
                        print(f"    ❌ Failed to extract after retries — skipped.")
                        debug_messages.append({
                            "type": "failed_extraction",
                            "channel": channel,
                            "msg_id": msg.id,
                            "text": raw_text[:500],
                            "timestamp": msg.date.isoformat() if msg.date else None
                        })
                        if len(debug_messages) > DEBUG_MAX:
                            debug_messages.pop(0)
                        last_seen_ids[channel] = msg.id
                        save_last_seen()
                        continue

                    # Successfully extracted job(s)
                    jobs_list = job_result.get("jobs", [])
                    if not jobs_list and isinstance(job_result, dict) and job_result.get("role"):
                        jobs_list = [job_result]

                    for single_job in jobs_list:
                        role = single_job.get("role")
                        company = single_job.get("company")
                        location = single_job.get("location") or ""
                        raw_apply_link = single_job.get("apply_link")
                        contact_email = single_job.get("contact_email")
                        contact_phone = single_job.get("contact_phone")

                        # Fallback phone extraction if missing
                        if not contact_phone:
                            from extractor_utils import extract_phone_number
                            contact_phone = extract_phone_number(raw_text)

                        # Primary URL logic: web apply link > mailto:email > tel:phone > telegram post link
                        if raw_apply_link and raw_apply_link.startswith("http"):
                            apply_link = raw_apply_link
                        elif contact_email:
                            apply_link = f"mailto:{contact_email}"
                        elif contact_phone:
                            apply_link = f"tel:{contact_phone.replace(' ', '')}"
                        else:
                            apply_link = telegram_post_url

                        print(f"    🎉 Extracted Job: '{role}' @ '{company}' ({location or 'Not Specified'})")

                        # Extract fallback walk-in info using regex
                        from extractor_utils import extract_walkin_info
                        w_info = extract_walkin_info(title=role, description=raw_text)
                        is_walk = bool(single_job.get("is_walkin")) or w_info.get("is_walkin", False)
                        w_date = single_job.get("walkin_date") or w_info.get("walkin_date")
                        w_time = w_info.get("walkin_time")

                        job_data = {
                            "title": role,
                            "company": company,
                            "location": location,
                            "date_posted": datetime.now().strftime("%Y-%m-%d"),
                            "url": apply_link,
                            "telegram_url": telegram_post_url,
                            "contact_email": contact_email,
                            "contact_phone": contact_phone,
                            "source": telegram_type,  # "telegram_message" or "telegram_post"
                            "experience": single_job.get("experience"),
                            "salary": single_job.get("salary"),
                            "qualification": single_job.get("qualification"),
                            "last_date": single_job.get("last_date"),
                            "other_details": single_job.get("other_details"),
                            "role_search": "Telegram Alert",
                            "is_walkin": is_walk,
                            "walkin_date": w_date,
                            "walkin_time": w_time,
                            "qr_data": qr_result
                        }

                        # Store in unified database (runs classifier, deduplicates)
                        if storage:
                            stored_count = storage.store_jobs_batch([job_data])
                            if stored_count > 0:
                                new_jobs_stored += 1
                                print("      ✅ Stored in database.")
                            else:
                                print("      ⚠️ Duplicate — already exists.")
                        else:
                            print("      ❌ Storage module not available.")

                    last_seen_ids[channel] = msg.id
                    save_last_seen()
                    time.sleep(1)  # Rate limit between Gemini API calls

                # Save progress after each channel completes
                save_progress(finished=False, current_channel_idx=ch_idx + 1)
            else:
                # All channels processed without breaking
                save_progress(finished=True)

    finally:
        # Clean up temp folder
        try:
            shutil.rmtree(temp_media_dir)
        except:
            pass
        # Clean up temporary decrypted session file
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
                print("🧹 Removed decrypted temporary session file.")
            except:
                pass

    # Save debug messages to file
    debug_file = os.path.join(WORKSPACE_DIR, "telegram_debug_messages.json")
    with open(debug_file, "w", encoding="utf-8") as f:
        json.dump(debug_messages, f, indent=2, ensure_ascii=False)
    print(f"\n📝 Saved {len(debug_messages)} debug messages to telegram_debug_messages.json")

    print(f"\n{'='*60}")
    print(f"✅ Telegram Jobs Pipeline Summary")
    print(f"{'='*60}")
    print(f"  Messages processed:   {messages_processed}")
    print(f"  Jobs stored (new):    {new_jobs_stored}")
    print(f"  Non-job skipped:      {messages_skipped_none}")
    print(f"  Failed extractions:   {messages_failed}")
    print(f"  Debug samples saved:  {len(debug_messages)}")
    print(f"  Runtime:              {(time.time() - PIPELINE_START_TIME)/60:.1f} minutes")
    print(f"{'='*60}")

def save_last_seen():
    with open(LAST_SEEN_FILE, "w") as f:
        json.dump(last_seen_ids, f, indent=4)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_pipeline())
