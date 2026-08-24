import sys
import re
import xml.etree.ElementTree as ET
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

def get_video_id_from_rss(channel_id):
    """Metode 1: Ambil Video ID via RSS Feed resmi YouTube."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            ns = {'yt': 'http://www.youtube.com/xml/xmlns/ns/2015', 'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            if entries:
                yt_vid = entries[0].find('yt:videoId', ns)
                if yt_vid is not None:
                    return yt_vid.text
    except Exception:
        pass
    return None

def get_video_id_from_invidious(target_str):
    """Metode 2: Fallback pencarian Video ID via Invidious public API."""
    instances = ["https://inv.tux.pizza", "https://invidious.nerdvpn.de", "https://yt.drgnz.club"]
    for instance in instances:
        try:
            if target_str.startswith("UC"):
                url = f"{instance}/api/v1/channels/{target_str}/videos"
            else:
                clean_name = target_str.replace("https://www.youtube.com/", "").replace("/live", "").replace("@", "")
                url = f"{instance}/api/v1/channels/search?q={clean_name}"
            
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("videoId")
                elif isinstance(data, dict):
                    videos = data.get("videos", [])
                    if videos:
                        return videos[0].get("videoId")
        except Exception:
            continue
    return None

def get_hls_stream(video_id):
    """Mengekstrak URL .m3u8 langsung menggunakan InnerTube TV HTML5 Client."""
    api_url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "context": {
            "client": {
                "clientName": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
                "clientVersion": "2.0",
                "clientScreen": "WATCH"
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
        print(f"Error InnerTube [{video_id}]: {e}", file=sys.stderr)
    return None

def process_target(target):
    # Kasus Direct Stream M3U8
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    video_id = None
    
    # 1. Jika berupa Channel ID (UC...)
    if target.startswith("UC"):
        video_id = get_video_id_from_rss(target)
        if not video_id:
            video_id = get_video_id_from_invidious(target)
            
    # 2. Jika berupa URL Watch langsung
    elif "watch?v=" in target:
        video_id = target.split("watch?v=")[1].split("&")[0]
        
    # 3. Fallback Handle YouTube (@channel)
    elif "youtube.com" in target or target.startswith("@"):
        video_id = get_video_id_from_invidious(target)

    if video_id:
        return get_hls_stream(video_id)

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
