import sys
import subprocess
import re
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

def resolve_to_video_id(target):
    target = target.strip()
    
    # Direct Video ID (11 Karakter)
    if len(target) == 11 and not target.startswith("http") and not target.startswith("UC"):
        return target
        
    # Standard URL watch?v=
    if "watch?v=" in target:
        return target.split("watch?v=")[1].split("&")[0]

    # Scrape Video ID dari Embed Page
    url = ""
    if target.startswith("UC"):
        url = f"https://www.youtube.com/embed/live_stream?channel={target}"
    elif target.startswith("@"):
        url = f"https://www.youtube.com/{target}/live"
    elif "youtube.com" in target or "youtu.be" in target:
        url = target

    if url:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                match = re.search(r'link rel="canonical" href="https://www\.youtube\.com/watch\?v=([^"]+)"', res.text)
                if match:
                    return match.group(1)
                match_json = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
                if match_json:
                    return match_json.group(1)
        except Exception:
            pass

    return None

def extract_m3u8_innertube(video_id):
    """Metode 1: High-speed InnerTube API (Bypass Client Protection)"""
    url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "context": {
            "client": {
                "clientName": "ANDROID_VR",
                "clientVersion": "1.56.21"
            }
        },
        "videoId": video_id
    }
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            data = res.json()
            hls_url = data.get("streamingData", {}).get("hlsManifestUrl")
            if hls_url:
                return hls_url
    except Exception:
        pass
    return None

def extract_m3u8_ytdlp(video_id):
    """Metode 2: Fallback via yt-dlp menggunakan client tv_embedded"""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "-g",
        "-f", "m3u8/best/b",
        "--extractor-args", "youtube:player_client=tv_embedded,ios",
        "--no-warnings",
        "--socket-timeout", "10",
        video_url
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        out = res.stdout.strip()
        if out and ("m3u8" in out or "googlevideo.com" in out):
            return out.splitlines()[0]
    except Exception:
        pass
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    video_id = resolve_to_video_id(target)
    if video_id:
        stream_url = extract_m3u8_innertube(video_id)
        if not stream_url:
            stream_url = extract_m3u8_ytdlp(video_id)
        return stream_url

    return None

print("#EXTM3U")

try:
    with open("youtubeLink.txt", "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("##")]

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        
        if "||" in line:
            parts = [p.strip() for p in line.split("||")]
            name = parts[0] if len(parts) > 0 else "Live TV"
            tvg_id = parts[1] if len(parts) > 1 else "tv.live"
            group = parts[2] if len(parts) > 2 else "General"
            
            if i + 1 < len(raw_lines):
                target_entry = raw_lines[i + 1]
                stream_url = process_target(target_entry)
                
                if stream_url:
                    print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{group}", {name}')
                    print(stream_url)
                else:
                    print(f"Gagal mengambil stream: {name}", file=sys.stderr)
                
                i += 2
            else:
                i += 1
        else:
            i += 1

except Exception as e:
    print(f"Error reading youtubeLink.txt: {e}", file=sys.stderr)
