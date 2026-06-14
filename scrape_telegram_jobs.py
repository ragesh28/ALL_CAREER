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
# OLLAMA EXTRACTION — with retry logic & walking interview detection
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are an AI assistant specialized in extracting job details from text. "
    "Analyze the provided text and return a valid JSON object.\n\n"
    "If the text is NOT a job posting (e.g., greetings, ads, memes, promotions, "
    "casual chat, motivational quotes, news), return exactly: {\"none\": true}\n\n"
    "If the text IS a job posting, return a JSON object with exactly these keys:\n"
    "\"company\", \"role\", \"qualification\", \"experience\", \"salary\", "
    "\"location\", \"apply_link\", \"walking_interview\", \"last_date\", \"other_details\".\n\n"
    "Rules:\n"
    "- If a key is missing or not mentioned, set its value to null.\n"
    "- \"walking_interview\" must be true if the text mentions walk-in, walkin, "
    "walk in interview, direct interview, spot interview, open drive, or spot offer. "
    "Otherwise set it to false.\n"
    "- Do not guess apply links. If none exists, set it to null.\n"
    "- Experience and salary should be short strings or null.\n"
    "- \"last_date\" is the application deadline if mentioned, otherwise null.\n"
    "- Do NOT add markdown formatting, backticks, explanation, or text outside the JSON."
)

def _call_ollama(text):
    """Single Ollama API call. Returns parsed JSON dict or None."""
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "qwen2.5:1.5b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            content = result.get("message", {}).get("content", "").strip()
            return json.loads(content)
        else:
            print(f"    Ollama status error {response.status_code}")
    except json.JSONDecodeError:
        print("    Ollama returned non-JSON response")
    except Exception as e:
        print(f"    Ollama extraction error: {e}")
    return None


def extract_job_with_ollama(text, max_retries=3):
    """
    Extract job data from text using Ollama with retry logic.
    Returns:
        dict  — valid job data
        "NONE" — AI determined this is not a job posting (do not retry)
        None — extraction failed after all retries
    """
    for attempt in range(max_retries):
        result = _call_ollama(text)

        if result is None:
            print(f"    ⚠️ Attempt {attempt+1}/{max_retries}: Ollama call failed, retrying...")
            time.sleep(2)
            continue

        # Non-job message detected — do NOT retry
        if isinstance(result, dict) and result.get("none") is True:
            return "NONE"

        # Valid job extracted — must have role AND company
        if isinstance(result, dict) and result.get("role") and result.get("company"):
            return result

        # AI returned JSON but missing required fields — retry
        print(f"    ⚠️ Attempt {attempt+1}/{max_retries}: AI returned incomplete JSON, retrying...")
        time.sleep(1)

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
                    if source == "telegram":
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

    today_cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    new_jobs_stored = 0
    messages_processed = 0
    messages_skipped_none = 0
    messages_failed = 0

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

                    # Check for image media to perform OCR
                    if msg.media:
                        try:
                            file_path = await client.download_media(msg, file=temp_media_dir)
                            if file_path:
                                ext = os.path.splitext(file_path)[1].lower()
                                if ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
                                    ocr_text = extract_text_from_image(file_path)
                                    if ocr_text:
                                        raw_text += "\n" + ocr_text
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

                    # Analyze text with local Ollama (with retry logic)
                    messages_processed += 1
                    print(f"  Analyzing message {msg.id} with Qwen2.5 1.5B...")
                    job_result = extract_job_with_ollama(raw_text)

                    # Handle non-job messages
                    if job_result == "NONE":
                        messages_skipped_none += 1
                        print(f"    🚫 Not a job posting — skipped.")
                        last_seen_ids[channel] = msg.id
                        save_last_seen()
                        continue

                    # Handle extraction failure
                    if job_result is None:
                        messages_failed += 1
                        print(f"    ❌ Failed to extract after retries — skipped.")
                        last_seen_ids[channel] = msg.id
                        save_last_seen()
                        continue

                    # Successfully extracted job
                    job_json = job_result
                    role = job_json.get("role")
                    company = job_json.get("company")
                    location = job_json.get("location") or "Remote"
                    apply_link = job_json.get("apply_link") or f"https://t.me/{channel}/{msg.id}"
                    walking = job_json.get("walking_interview", False)

                    walk_label = " 🚶 [Walking Interview]" if walking else ""
                    print(f"    🎉 Extracted: '{role}' @ '{company}' ({location}){walk_label}")

                    job_data = {
                        "title": role,
                        "company": company,
                        "location": location,
                        "date_posted": datetime.now().strftime("%Y-%m-%d"),
                        "url": apply_link,
                        "source": "telegram",
                        "walking_interview": walking,
                        "experience": job_json.get("experience"),
                        "salary": job_json.get("salary"),
                        "qualification": job_json.get("qualification"),
                        "last_date": job_json.get("last_date"),
                        "other_details": job_json.get("other_details"),
                        "role_search": "Telegram Alert"
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
                    time.sleep(0.5)

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

    print(f"\n{'='*60}")
    print(f"✅ Telegram Jobs Pipeline Summary")
    print(f"{'='*60}")
    print(f"  Messages processed:   {messages_processed}")
    print(f"  Jobs stored (new):    {new_jobs_stored}")
    print(f"  Non-job skipped:      {messages_skipped_none}")
    print(f"  Failed extractions:   {messages_failed}")
    print(f"  Runtime:              {(time.time() - PIPELINE_START_TIME)/60:.1f} minutes")
    print(f"{'='*60}")

def save_last_seen():
    with open(LAST_SEEN_FILE, "w") as f:
        json.dump(last_seen_ids, f, indent=4)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_pipeline())
