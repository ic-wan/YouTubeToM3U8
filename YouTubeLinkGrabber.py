import sys
import re
import json
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Android 14; Mobile; rv:128.0) Gecko/128.0 Firefox/128.0',
    'Accept-Language': 'en-US,en;q=0.9',
}

def get_live_video_id(channel_id):
    """Mendapatkan Video ID siaran langsung dari Channel ID."""
    # 1. Cek via Live Embed URL
    try:
        url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            match = re.search(r'link rel="canonical" href="https://www\.youtube\.com/watch\?v=([^"]+)"', res.text)
            if match and match.group(1) != channel_id:
                return match.group(1)
            # Fallback regex untuk videoId dari HTML script
            vid_match = re.search(r'"videoId":"([^"]+)"', res.text)
            if vid_match:
                return vid_match.group(1)
    except Exception:
        pass

    # 2. Cek via RSS Feed Canonical
    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        res = requests.get(rss_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            matches = re.findall(r'<yt:videoId>([^<]+)</yt:videoId>', res.text)
            if matches:
                return matches[0]
    except Exception:
        pass

    return None

def extract_m3u8(video_id):
    """Mengambil link .m3u8 menggunakan InnerTube API client ANDROID_VR (Lolos IP Block)."""
    url = "https://www.youtube.com/youtubei/v1/player"
    
    # Client ANDROID_VR & TVHTML5 jarang dikenakan rate limit / bot challenge di IP cloud
    payloads = [
        {
            "context": {
                "client": {
                    "clientName": "ANDROID_VR",
                    "clientVersion": "1.56.21",
                    "deviceModel": "Quest 3"
                }
            },
            "videoId": video_id
        },
        {
            "context": {
                "client": {
                    "clientName": "TVHTML5",
                    "clientVersion": "7.20240815.00.00"
                }
            },
            "videoId": video_id
        }
    ]

    for payload in payloads:
        try:
            res = requests.post(url, json=payload, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                streaming_data = data.get("streamingData", {})
                
                # Cek manifest m3u8 langsung
                hls_manifest = streaming_data.get("hlsManifestUrl")
                if hls_manifest:
                    return hls_manifest
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
        return extract_m3u8(video_id)

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
