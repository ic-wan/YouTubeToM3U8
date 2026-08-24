import sys
import re
import requests
import streamlink

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def resolve_youtube_url(url):
    """Mendapatkan canonical video URL dari channel /live untuk menghindari bot detection."""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            # Cari video ID live dari tag canonical link HTML YouTube
            match = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([^"]+)"', res.text)
            if match:
                video_id = match.group(1)
                return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print(f"Error resolving {url}: {e}", file=sys.stderr)
    return url

def get_stream_url(target_url):
    try:
        final_url = resolve_youtube_url(target_url)
        streams = streamlink.streams(final_url)
        if "best" in streams:
            return streams["best"].to_url()
        elif "live" in streams:
            return streams["live"].to_url()
        elif "worst" in streams:
            return streams["worst"].to_url()
    except Exception as e:
        print(f"Error Streamlink [{target_url}]: {e}", file=sys.stderr)
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
                
                # Kasus 1: Direct M3U8 Link
                if ".m3u8" in target_url and "youtube.com" not in target_url and "youtu.be" not in target_url:
                    print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{group}", {name}')
                    print(target_url)
                
                # Kasus 2: YouTube Link
                else:
                    stream_url = get_stream_url(target_url)
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
