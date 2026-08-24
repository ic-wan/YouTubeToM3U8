import sys
import re
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

def get_live_video_id(url):
    """Mengekstrak Video ID unik dari halaman live channel YouTube."""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            match = re.search(r'href="https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"', res.text)
            if match:
                return match.group(1)
            match_json = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
            if match_json:
                return match_json.group(1)
    except Exception as e:
        print(f"Error fetching Video ID: {e}", file=sys.stderr)
    return None

def get_hls_url(video_id):
    """Mendapatkan link HLS m3u8 langsung menggunakan InnerTube TV HTML5 Embedded Client."""
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
            hls_manifest_url = streaming_data.get("hlsManifestUrl")
            if hls_manifest_url:
                return hls_manifest_url
    except Exception as e:
        print(f"Error extracting HLS for video {video_id}: {e}", file=sys.stderr)
    return None

def process_target(url):
    # Jika URL langsung berupa .m3u8
    if ".m3u8" in url and "youtube.com" not in url and "youtu.be" not in url:
        return url
        
    # Jika URL YouTube
    video_id = None
    if "watch?v=" in url:
        video_id = url.split("watch?v=")[1].split("&")[0]
    else:
        video_id = get_live_video_id(url)
        
    if video_id:
        return get_hls_url(video_id)
        
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
