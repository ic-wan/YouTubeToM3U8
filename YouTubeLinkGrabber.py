import sys
import subprocess
import re
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

def resolve_target_to_videoid(target):
    """Mengubah Channel ID / Handle / URL menjadi Video ID live yang aktif."""
    # 1. Jika target sudah berupa Video ID 11 karakter
    if len(target) == 11 and not target.startswith("http") and not target.startswith("UC"):
        return target

    # 2. Jika target URL watch
    if "watch?v=" in target:
        return target.split("watch?v=")[1].split("&")[0]

    # 3. Kueri via yt-dlp untuk me-resolve URL / Channel ID / Handle ke Video ID
    url_to_fetch = target
    if target.startswith("UC"):
        url_to_fetch = f"https://www.youtube.com/channel/{target}/live"
    elif target.startswith("@"):
        url_to_fetch = f"https://www.youtube.com/{target}/live"

    cmd = [
        "yt-dlp",
        "--get-id",
        "--extractor-args", "youtube:player_client=ios,android",
        "--no-warnings",
        url_to_fetch
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        vid = res.stdout.strip()
        if len(vid) == 11:
            return vid
    except Exception:
        pass

    # 4. Fallback RSS jika channel ID
    if target.startswith("UC"):
        try:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={target}"
            res = requests.get(rss_url, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                vids = re.findall(r'<yt:videoId>([^<]+)</yt:videoId>', res.text)
                if vids:
                    return vids[0]
        except Exception:
            pass

    return None

def extract_m3u8_url(video_id):
    """Mengambil link m3u8 menggunakan yt-dlp client TV/iOS."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "-g",
        "-f", "best[ext=mp4]/best",
        "--extractor-args", "youtube:player_client=ios,tv_embedded",
        "--no-warnings",
        video_url
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        out = res.stdout.strip()
        if out:
            lines = out.splitlines()
            for line in lines:
                if "m3u8" in line or "manifest" in line or "googlevideo.com" in line:
                    return line
            return lines[0]
    except Exception:
        pass
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    video_id = resolve_target_to_videoid(target)
    if video_id:
        return extract_m3u8_url(video_id)
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
