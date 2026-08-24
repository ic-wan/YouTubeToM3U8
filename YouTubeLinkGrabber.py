import sys
import re
import json
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

INVIDIOUS_INSTANCES = [
    "https://inv.hostux.net",
    "https://invidious.nerdvpn.de",
    "https://yewtu.be",
    "https://invidious.drgns.space"
]

def get_live_video_id(channel_id):
    """Mencari Video ID live dari Channel ID menggunakan beberapa metode bypass."""
    
    # 1. Cek via Invidious API (Tahan blokir IP GitHub)
    for instance in INVIDIOUS_INSTANCES:
        try:
            url = f"{instance}/api/v1/channels/{channel_id}"
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                # Cari video yang statusnya live
                for video in data.get('latestVideos', []):
                    if video.get('isLive', False):
                        return video.get('videoId')
        except Exception:
            continue

    # 2. Cek via Canonical Embed YouTube
    try:
        embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
        res = requests.get(embed_url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            match = re.search(r'link rel="canonical" href="https://www\.youtube\.com/watch\?v=([^"]+)"', res.text)
            if match and match.group(1) != channel_id:
                return match.group(1)
    except Exception:
        pass

    # 3. Cek via RSS Feed
    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        res = requests.get(rss_url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            matches = re.findall(r'<yt:videoId>([^<]+)</yt:videoId>', res.text)
            if matches:
                return matches[0]
    except Exception:
        pass

    return None

def get_hls_from_innertube(video_id):
    """Mengambil langsung URL .m3u8 via YouTube InnerTube API (No yt-dlp dependency)."""
    url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "context": {
            "client": {
                "clientName": "WEB_EMBEDDED_PLAYER",
                "clientVersion": "1.20240815.01.00"
            }
        },
        "videoId": video_id
    }
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            data = res.json()
            streaming_data = data.get("streamingData", {})
            hls_manifest = streaming_data.get("hlsManifestUrl")
            if hls_manifest:
                return hls_manifest
    except Exception:
        pass
    return None

def get_hls_from_invidious(video_id):
    """Fallback alternatif mengambil m3u8 dari Invidious API jika YouTube API menolak IP."""
    for instance in INVIDIOUS_INSTANCES:
        try:
            url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                hls_url = data.get("hlsUrl")
                if hls_url:
                    return hls_url
        except Exception:
            continue
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    video_id = None
    if target.startswith("UC"):
        video_id = get_live_video_id(target)
    elif "watch?v=" in target:
        video_id = target.split("watch?v=")[1].split("&")[0]
    elif len(target) == 11 and not target.startswith("http"):
        video_id = target

    if video_id:
        # Coba ambil via InnerTube API dulu
        m3u8_url = get_hls_from_innertube(video_id)
        if not m3u8_url:
            # Fallback ke Invidious API
            m3u8_url = get_hls_from_invidious(video_id)
        return m3u8_url

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
