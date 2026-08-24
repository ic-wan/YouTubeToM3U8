import sys
import subprocess
import re
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

def get_live_video_id(channel_id):
    """Mendapatkan Video ID dari tayangan live yang sedang aktif tanpa kena blokir IP."""
    # Cara 1: Cek halaman embed channel
    embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
    try:
        res = requests.get(embed_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            match = re.search(r'link rel="canonical" href="https://www\.youtube\.com/watch\?v=([^"]+)"', res.text)
            if match:
                return match.group(1)
    except Exception:
        pass

    # Cara 2: Fallback ke RSS Feed jika cara 1 gagal
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            matches = re.findall(r'<yt:videoId>([^<]+)</yt:videoId>', res.text)
            if matches:
                return matches[0]
    except Exception:
        pass

    return None

def extract_m3u8_with_ytdlp(video_id):
    """Mengekstrak URL .m3u8 dari Video ID menggunakan client tv_embedded / ios."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    cmd = [
        "yt-dlp",
        "--get-url",
        "-f", "b/bestpass/best",
        "--extractor-args", "youtube:player_client=tv_embedded,ios",
        "--no-warnings",
        "--geo-bypass",
        "--socket-timeout", "10",
        video_url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = result.stdout.strip()
        if output and ("m3u8" in output or "manifest" in output):
            return output.splitlines()[0]
    except Exception:
        pass
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    video_id = None
    if target.startswith("UC"):
        video_id = get_live_video_id(target)
    elif "watch?v=" in target:
        video_id = target.split("watch?v=")[1].split("&")[0]

    if video_id:
        return extract_m3u8_with_ytdlp(video_id)

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
