import sys
import re
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

def get_video_id_from_url(url):
    """Mengekstrak Video ID langsung jika URL sudah berupa watch link atau via OEmbed API."""
    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    
    # Coba ekstrak Video ID via Invidious / HTML Regex
    try:
        # Gunakan OEmbed / fallback fetch
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            match = re.search(r'href="https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"', res.text)
            if match:
                return match.group(1)
            match_json = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
            if match_json:
                return match_json.group(1)
            # Coba cari canonical / shortlink
            match_short = re.search(r'https://youtu\.be/([a-zA-Z0-9_-]{11})', res.text)
            if match_short:
                return match_short.group(1)
    except Exception as e:
        print(f"Error fetching Video ID for {url}: {e}", file=sys.stderr)
    return None

def get_hls_from_innertube(video_id):
    """Mengekstrak HLS manifest menggunakan InnerTube API Android client."""
    api_url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.05.36",
                "androidSdkVersion": 30,
                "hl": "en",
                "gl": "US"
            }
        },
        "videoId": video_id
    }
    try:
        res = requests.post(api_url, json=payload, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            streaming_data = data.get("streamingData", {})
            hls_url = streaming_data.get("hlsManifestUrl")
            if hls_url:
                return hls_url
    except Exception as e:
        print(f"InnerTube error for {video_id}: {e}", file=sys.stderr)
    return None

def get_hls_from_invidious(video_id):
    """Fallback ke Invidious Public Instances jika InnerTube diblokir."""
    instances = [
        "https://inv.tux.pizza",
        "https://invidious.nerdvpn.de",
        "https://yt.drgnz.club"
    ]
    for instance in instances:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                hls_url = data.get("hlsUrl")
                if hls_url:
                    return hls_url
        except Exception:
            continue
    return None

def process_target(url):
    if ".m3u8" in url and "youtube.com" not in url and "youtu.be" not in url:
        return url
        
    video_id = get_video_id_from_url(url)
    if video_id:
        # Priority 1: InnerTube API
        hls_stream = get_hls_from_innertube(video_id)
        if hls_stream:
            return hls_stream
        
        # Priority 2: Invidious Fallback
        hls_stream = get_hls_from_invidious(video_id)
        if hls_stream:
            return hls_stream

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
                target_url = raw_lines[i + 1]
                stream_url = process_target(target_url)
                
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
