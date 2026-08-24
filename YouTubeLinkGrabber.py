import sys
import re
import xml.etree.ElementTree as ET
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

def get_video_id_from_embed(channel_id):
    """Mendapatkan Video ID live aktif via YouTube Embed Player (Bypass Bot Check)."""
    embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
    try:
        res = requests.get(embed_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            match = re.search(r'"video_id":"([a-zA-Z0-9_-]{11})"', res.text)
            if match:
                return match.group(1)
            match_canonical = re.search(r'link rel="canonical" href="https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"', res.text)
            if match_canonical:
                return match_canonical.group(1)
    except Exception as e:
        print(f"Error Embed ID [{channel_id}]: {e}", file=sys.stderr)
    return None

def get_video_id_from_rss(channel_id):
    """Fallback RSS Feed resmi jika Embed URL tidak mengembalikan video_id."""
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

def get_hls_stream_tv(video_id):
    """Mengekstrak HLS manifest (.m3u8) menggunakan InnerTube TV Client (Kebal blokir GitHub runner)."""
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
            streaming_data = data.get("streamingData", {})
            hls_url = streaming_data.get("hlsManifestUrl")
            if hls_url:
                return hls_url
    except Exception as e:
        print(f"Error InnerTube TV [{video_id}]: {e}", file=sys.stderr)
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    video_id = None
    if target.startswith("UC"):
        # Prioritas 1: Embed Player
        video_id = get_video_id_from_embed(target)
        # Prioritas 2: RSS Feed
        if not video_id:
            video_id = get_video_id_from_rss(target)
    elif "watch?v=" in target:
        video_id = target.split("watch?v=")[1].split("&")[0]

    if video_id:
        return get_hls_stream_tv(video_id)

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
