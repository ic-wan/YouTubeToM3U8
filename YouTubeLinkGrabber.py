import sys
import re
import xml.etree.ElementTree as ET
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

def get_latest_video_id_from_rss(channel_id):
    """Mendapatkan Video ID terbaru (termasuk Live) via RSS Feed resmi YouTube."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            # Namespace XML YouTube RSS
            ns = {'yt': 'http://www.youtube.com/xml/xmlns/ns/2015', 'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            if entries:
                # Ambil video ID dari entry paling pertama (terbaru)
                yt_vid = entries[0].find('yt:videoId', ns)
                if yt_vid is not None:
                    return yt_vid.text
    except Exception as e:
        print(f"Error RSS for {channel_id}: {e}", file=sys.stderr)
    return None

def get_hls_from_innertube(video_id):
    """Mengekstrak HLS manifest m3u8 menggunakan InnerTube API Client Android."""
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

def process_target(target_entry):
    # Jika baris adalah URL direct M3U8
    if ".m3u8" in target_entry and "youtube.com" not in target_entry:
        return target_entry

    video_id = None
    # Jika baris adalah ID Channel YouTube (dimulai dengan UC)
    if target_entry.startswith("UC"):
        video_id = get_latest_video_id_from_rss(target_entry)
    # Jika baris adalah URL watch video langsung
    elif "watch?v=" in target_entry:
        video_id = target_entry.split("watch?v=")[1].split("&")[0]
    # Jika URL channel lama/handle, ekstrak UC ID via oembed
    elif "youtube.com" in target_entry:
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={target_entry}&format=json"
            res = requests.get(oembed_url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                author_url = res.json().get("author_url", "")
                if "/channel/" in author_url:
                    uc_id = author_url.split("/channel/")[1]
                    video_id = get_latest_video_id_from_rss(uc_id)
        except Exception:
            pass

    if video_id:
        return get_hls_from_innertube(video_id)

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
