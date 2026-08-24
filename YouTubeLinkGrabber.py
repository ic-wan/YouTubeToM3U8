import sys
import subprocess
import re
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

def resolve_to_video_id(target):
    """Mengekstrak Video ID (11 karakter) dari berbagai format URL YouTube."""
    target = target.strip()
    
    if len(target) == 11 and not target.startswith("http") and not target.startswith("UC"):
        return target
        
    if "watch?v=" in target:
        return target.split("watch?v=")[1].split("&")[0]

    if "youtu.be/" in target:
        return target.split("youtu.be/")[1].split("?")[0]

    url = ""
    if target.startswith("UC"):
        url = f"https://www.youtube.com/embed/live_stream?channel={target}"
    elif target.startswith("@"):
        url = f"https://www.youtube.com/{target}/live"
    elif "youtube.com" in target:
        url = target

    if url:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                match = re.search(r'link rel="canonical" href="https://www\.youtube\.com/watch\?v=([^"]+)"', res.text)
                if match:
                    return match.group(1)
                match_json = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
                if match_json:
                    return match_json.group(1)
        except Exception:
            pass

    return None

def extract_m3u8_innertube(video_id):
    """Metode 1: InnerTube API cepat untuk Live Stream."""
    url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "context": {
            "client": {
                "clientName": "ANDROID_VR",
                "clientVersion": "1.56.21"
            }
        },
        "videoId": video_id
    }
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            data = res.json()
            hls_url = data.get("streamingData", {}).get("hlsManifestUrl")
            if hls_url:
                return hls_url
    except Exception:
        pass
    return None

def extract_with_ytdlp(video_id):
    """Metode 2: Fallback yt-dlp untuk mengambil Judul dan Stream URL."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "--print", "%(title)s",
        "-g",
        "-f", "m3u8/best/b",
        "--extractor-args", "youtube:player_client=tv_embedded,ios",
        "--no-warnings",
        "--socket-timeout", "10",
        video_url
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        if len(lines) >= 2:
            title = lines[0]
            stream_url = lines[1]
            return title, stream_url
        elif len(lines) == 1:
            return None, lines[0]
    except Exception:
        pass
    return None, None

def process_target(target):
    """Memproses target URL direct m3u8 atau link YouTube."""
    if ".m3u8" in target and "youtube.com" not in target:
        return None, target

    video_id = resolve_to_video_id(target)
    if video_id:
        # Coba ekstrak live m3u8 via InnerTube lebih dulu (sangat cepat)
        stream_url = extract_m3u8_innertube(video_id)
        if stream_url:
            return None, stream_url
        
        # Fallback ke yt-dlp (mendapatkan judul asli & link stream)
        title, stream_url = extract_with_ytdlp(video_id)
        return title, stream_url

    return None, None

# Output Header M3U
print("#EXTM3U")

try:
    with open("youtubeLink.txt", "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("##")]

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        
        # Opsi 1: Format 2 baris (Metadata Header + URL)
        if "||" in line:
            parts = [p.strip() for p in line.split("||")]
            name = parts[0] if len(parts) > 0 else "YouTube Stream"
            tvg_id = parts[1] if len(parts) > 1 else "yt.stream"
            group = parts[2] if len(parts) > 2 else "Music"
            
            if i + 1 < len(raw_lines):
                target_entry = raw_lines[i + 1]
                auto_title, stream_url = process_target(target_entry)
                
                # Gunakan judul dari yt-dlp jika nama header default/kosong
                display_name = auto_title if (auto_title and name == "YouTube Stream") else name
                
                if stream_url:
                    print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{display_name}" group-title="{group}", {display_name}')
                    print(stream_url)
                else:
                    print(f"Gagal mengambil stream: {name}", file=sys.stderr)
                
                i += 2
            else:
                i += 1

        # Opsi 2: Baris Tunggal Berisi URL YouTube Langsung (Otomatis Ambil Judul & Kategori)
        elif "youtube.com" in line or "youtu.be" in line:
            auto_title, stream_url = process_target(line)
            if stream_url:
                title = auto_title if auto_title else "YouTube Track"
                print(f'#EXTINF:-1 tvg-id="yt.music" tvg-name="{title}" group-title="Musik", {title}')
                print(stream_url)
            else:
                print(f"Gagal mengambil stream: {line}", file=sys.stderr)
            i += 1
        else:
            i += 1

except Exception as e:
    print(f"Error reading youtubeLink.txt: {e}", file=sys.stderr)
