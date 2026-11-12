"""Read posts that Telegram exposes on a channel's anonymous web preview."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class PublicMessage:
    id: int
    date: datetime
    text: str
    photo_urls: tuple[str, ...]


def channel_handle(value):
    value = value.strip()
    if value.startswith("https://"):
        url = urlsplit(value)
        if url.netloc.lower() != "t.me":
            raise ValueError("Expected a t.me public channel link")
        value = url.path.strip("/").removeprefix("s/")
    value = value.removeprefix("@")
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError("Expected a public channel handle")
    return value


def _message_text(row):
    body = row.select_one(".tgme_widget_message_text")
    if body is None:
        return ""
    for line_break in body.find_all("br"):
        line_break.replace_with("\n")
    for link in body.select("a[href]"):
        target = link["href"]
        label = link.get_text()
        if target.startswith(("https://", "http://", "mailto:", "tel:")) and target not in label:
            link.replace_with(f"{label} {target}".strip())
    return body.get_text().strip()


def _parse_page(html, channel):
    soup = BeautifulSoup(html, "html.parser")
    messages = []
    for row in soup.select(".tgme_widget_message[data-post]"):
        handle, _, post_id = row["data-post"].partition("/")
        posted_at = row.select_one("time[datetime]")
        if handle.lower() != channel.lower() or not post_id.isdecimal() or posted_at is None:
            continue
        try:
            date = datetime.fromisoformat(posted_at["datetime"])
        except ValueError:
            continue
        if date.tzinfo is None:
            continue
        photo_urls = []
        for photo in row.select(".tgme_widget_message_photo_wrap"):
            match = re.search(r"""url\(\s*['"]?(https://[^'"\s)]+)['"]?\s*\)""", photo.get("style", ""))
            if match:
                photo_urls.append(match[1])
        messages.append(PublicMessage(int(post_id), date, _message_text(row), tuple(dict.fromkeys(photo_urls))))

    pager = soup.select_one("a[data-before]")
    before = pager["data-before"] if pager else ""
    messages.sort(key=lambda message: message.id, reverse=True)
    return messages, int(before) if before.isdecimal() else None


def read_public_messages(session, channel, last_id, cutoff, limit=50):
    """Return up to limit new messages, oldest first, with no checkpoint writes."""
    channel = channel_handle(channel)
    url = f"https://t.me/s/{channel}"
    before = None
    messages = {}
    while len(messages) < limit:
        response = session.get(url, params={"before": before} if before is not None else None, timeout=15)
        response.raise_for_status()
        page, next_before = _parse_page(response.text, channel)
        if not page:
            raise ValueError("No messages exposed in the public preview page")
        previous_count = len(messages)
        for message in page:
            if message.id <= last_id or message.date < cutoff:
                return list(reversed(messages.values()))
            messages.setdefault(message.id, message)
            if len(messages) == limit:
                return list(reversed(messages.values()))
        if not next_before:
            break
        if len(messages) == previous_count or (before is not None and next_before >= before):
            raise ValueError("Public preview pagination did not advance")
        before = next_before
    return list(reversed(messages.values()))


def download_public_photo(session, url, temp_dir):
    """Save a rendered preview photo for the existing OCR and QR readers."""
    suffixes = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/bmp": ".bmp"}
    with session.get(url, timeout=15, stream=True) as response:
        response.raise_for_status()
        suffix = suffixes.get(response.headers.get("Content-Type", "").split(";")[0].strip().lower())
        if not suffix:
            raise ValueError("Preview photo did not return a supported image")
        image = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            image.extend(chunk)
            if len(image) > 12 * 1024 * 1024:
                raise ValueError("Preview photo is too large for OCR")
    path = Path(temp_dir) / f"preview{suffix}"
    path.write_bytes(image)
    return str(path)
