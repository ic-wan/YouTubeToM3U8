import sys
import re
import xml.etree.ElementTree as ET
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1'
}

def get_video_id_from_rss(channel_id):
    """Mendapatkan Video ID terbaru dari RSS Feed YouTube resmi."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            ns = {'yt': 'http://www.youtube.com/xml/xmlns/ns/2015', 'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            if entries:
                # Ambil video_id paling baru di channel
                yt_vid = entries[0].find('yt:videoId', ns)
                if yt_vid is not None:
                    return yt_vid.text
    except Exception as e:
        print(f"Error RSS {channel_id}: {e}", file=sys.stderr)
    return None

def get_hls_stream_mweb(video_id):
    """Mengekstrak HLS manifest menggunakan Client Mobile Web (MWEB) InnerTube API."""
    api_url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "context": {
            "client": {
                "clientName": "MWEB",
                "clientVersion": "2.20240425.01.00",
                "hl": "id",
                "gl": "ID"
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
            
            # Fallback format jika hlsManifestUrl tidak langsung mengembalikan string
            formats = streaming_data.get("adaptiveFormats", [])
            for fmt in formats:
                if "url" in fmt and ("m3u8" in fmt["url"] or "index.m3u8" in fmt["url"]):
                    return fmt["url"]
    except Exception as e:
        print(f"Error InnerTube MWEB [{video_id}]: {e}", file=sys.stderr)
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
        return get_hls_stream_mweb(video_id)

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
