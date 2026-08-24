import sys
import subprocess
import re
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

def get_live_videoid_from_target(target):
    """Mengubah Channel ID / Handle / URL menjadi Video ID 11 karakter."""
    target = target.strip()
    
    # 1. Jika sudah berupa Video ID 11 karakter
    if len(target) == 11 and not target.startswith("http") and not target.startswith("UC"):
        return target
        
    # 2. Jika berupa URL watch YouTube
    if "watch?v=" in target:
        return target.split("watch?v=")[1].split("&")[0]

    # 3. Parsing Embed Stream HTML (Lolos bot filter IP datacenter)
    url = ""
    if target.startswith("UC"):
        url = f"https://www.youtube.com/embed/live_stream?channel={target}"
    elif target.startswith("@"):
        url = f"https://www.youtube.com/{target}/live"
    elif "youtube.com" in target or "youtu.be" in target:
        url = target

    if url:
        try:
            res = requests.get(url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                # Cari tag canonical link
                match = re.search(r'link rel="canonical" href="https://www\.youtube\.com/watch\?v=([^"]+)"', res.text)
                if match:
                    return match.group(1)
                # Cari pattern videoId di JSON tersemat
                match_json = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
                if match_json:
                    return match_json.group(1)
        except Exception:
            pass

    # 4. Fallback RSS feed jika Channel ID
    if target.startswith("UC"):
        try:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={target}"
            res = requests.get(rss_url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                matches = re.findall(r'<yt:videoId>([^<]+)</yt:videoId>', res.text)
                if matches:
                    return matches[0]
        except Exception:
            pass

    return None

def extract_hls_stream(video_id):
    """Mengekstrak URL stream m3u8 via yt-dlp client tv_embedded."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    cmd = [
        "yt-dlp",
        "-g",
        "-f", "m3u8/best/b",
        "--extractor-args", "youtube:player_client=tv_embedded,ios,web_embedded",
        "--no-warnings",
        "--geo-bypass",
        "--socket-timeout", "10",
        video_url
    ]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        out = res.stdout.strip()
        if out and ("m3u8" in out or "googlevideo.com" in out):
            return out.splitlines()[0]
    except Exception:
        pass
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    video_id = get_live_videoid_from_target(target)
    if video_id:
        return extract_hls_stream(video_id)
        
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
