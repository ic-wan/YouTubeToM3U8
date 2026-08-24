import sys
import xml.etree.ElementTree as ET
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# Daftar instance Invidious publik yang stabil
INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
    "https://vid.puffyan.us",
    "https://invidious.flokinet.to"
]

def get_video_id_from_rss(channel_id):
    """Mendapatkan Video ID terbaru via RSS Feed YouTube."""
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

def get_hls_from_invidious(video_id):
    """Mengambil link stream m3u8 langsung via Invidious API."""
    for instance in INVIDIOUS_INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                # Coba ambil HLS Manifest URL
                hls_url = data.get("hlsUrl")
                if hls_url:
                    return hls_url
                
                # Alternate: cari format adaptive yang mengandung m3u8
                adaptive = data.get("adaptiveFormats", [])
                for fmt in adaptive:
                    if "type" in fmt and "m3u8" in fmt["type"]:
                        return fmt.get("url")
        except Exception:
            continue
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    video_id = None
    if target.startswith("UC"):
        video_id = get_video_id_from_rss(target)
    elif "watch?v=" in target:
        video_id = target.split("watch?v=")[1].split("&")[0]

    if video_id:
        return get_hls_from_invidious(video_id)

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
