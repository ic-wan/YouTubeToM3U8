import sys
import streamlink

def get_stream_url(youtube_url):
    try:
        # Menarik stream langsung dari library streamlink
        streams = streamlink.streams(youtube_url)
        if "best" in streams:
            return streams["best"].to_url()
        elif "live" in streams:
            return streams["live"].to_url()
        elif "worst" in streams:
            return streams["worst"].to_url()
    except Exception as e:
        print(f"Error streamlink [{youtube_url}]: {e}", file=sys.stderr)
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
                
                # Kasus 1: Direct Link M3U8
                if ".m3u8" in target_url and "youtube.com" not in target_url and "youtu.be" not in target_url:
                    print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{group}", {name}')
                    print(target_url)
                
                # Kasus 2: Link YouTube Live
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
