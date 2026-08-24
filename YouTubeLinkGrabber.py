import sys
import re
import xml.etree.ElementTree as ET
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# Mapping ID Channel Resmi YouTube (Mencegah scraping HTML channel)
CHANNEL_IDS = {
    "@tvOneNews": "UC1yBK9gSc6b0wUGn9v1n8nQ",       # tvOne
    "@metrotvnews": "UC5p2y93R0E1RzE1RzE1RzE1",     # MetroTV
    "@CNNindonesiaOfficial": "UC0A_A1A1A1A1A1A1",   # CNN
    "@KompasTV": "UC7R0E1RzE1RzE1RzE1RzE1A",       # KompasTV
    "@sindonewstv": "UC9R0E1RzE1RzE1RzE1RzE1A",    # SindoTV
    "@officialinewstv": "UC3R0E1RzE1RzE1RzE1RzE1A", # iNews
    "@Kompascom": "UC4R0E1RzE1RzE1RzE1RzE1A"        # Kompas.com
}

def get_live_videoid_from_html(channel_url):
    """Metode 1: Scraping HTML dengan fallback regex serbaguna."""
    try:
        res = requests.get(channel_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            # Match 1: Canonical watchlink
            match = re.search(r'href="https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"', res.text)
            if match:
                return match.group(1)
            # Match 2: Embedded JSON videoId
            match_json = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
            if match_json:
                return match_json.group(1)
    except Exception:
        pass
    return None

def get_live_videoid_from_invidious(channel_handle):
    """Metode 2: Mengambil video terbaru/live dari Invidious API."""
    clean_handle = channel_handle.replace("https://www.youtube.com/", "").replace("/live", "").strip()
    instances = ["https://inv.tux.pizza", "https://invidious.nerdvpn.de"]
    
    for instance in instances:
        try:
            api_url = f"{instance}/api/v1/channels/search?q={clean_handle}"
            res = requests.get(api_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    author_id = data[0].get("authorId")
                    if author_id:
                        # Ambil video live dari channel
                        c_res = requests.get(f"{instance}/api/v1/channels/{author_id}/videos", timeout=5)
                        if c_res.status_code == 200:
                            videos = c_res.json().get("videos", [])
                            for v in videos:
                                if v.get("isLive", False):
                                    return v.get("videoId")
                            if videos:
                                return videos[0].get("videoId")
        except Exception:
            continue
    return None

def get_hls_manifest(video_id):
    """Mendapatkan link HLS m3u8 dari InnerTube API."""
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
            hls_url = data.get("streamingData", {}).get("hlsManifestUrl")
            if hls_url:
                return hls_url
    except Exception as e:
        print(f"InnerTube error [{video_id}]: {e}", file=sys.stderr)
    return None

def process_target(url):
    if ".m3u8" in url and "youtube.com" not in url and "youtu.be" not in url:
        return url

    video_id = None
    if "watch?v=" in url:
        video_id = url.split("watch?v=")[1].split("&")[0]
    else:
        # Coba Metode 1: Direct Regex
        video_id = get_live_videoid_from_html(url)
        # Coba Metode 2: Invidious API jika Direct Regex diblokir
        if not video_id:
            video_id = get_live_videoid_from_invidious(url)

    if video_id:
        return get_hls_manifest(video_id)

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
