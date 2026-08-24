import sys
import yt_dlp

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'format': 'best',
}

print("#EXTM3U")

try:
    with open("youtubeLink.txt", "r", encoding="utf-8") as f:
        # Ambil semua baris yang bukan komentar ## dan bukan baris kosong
        raw_lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("##")]

    i = 0
    while i < len(raw_lines):
        meta_line = raw_lines[i]
        
        # Cari baris yang mengandung '||'
        if "||" in meta_line:
            parts = [p.strip() for p in meta_line.split("||")]
            name = parts[0] if len(parts) > 0 else "Live TV"
            tvg_id = parts[1] if len(parts) > 1 else "tv.live"
            group = parts[2] if len(parts) > 2 else "General"
            
            # Ambil baris persis di bawahnya sebagai URL
            if i + 1 < len(raw_lines):
                target_url = raw_lines[i + 1]
                
                # Kasus 1: Tautan langsung .m3u8 (bukan YouTube)
                if ".m3u8" in target_url and "youtube.com" not in target_url and "youtu.be" not in target_url:
                    print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{group}", {name}')
                    print(target_url)
                
                # Kasus 2: Tautan YouTube (Video Live / Channel)
                else:
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(target_url, download=False)
                            stream_url = info.get('url')
                            if stream_url:
                                print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{group}", {name}')
                                print(stream_url)
                            else:
                                print(f"URL stream tidak ditemukan: {name}", file=sys.stderr)
                    except Exception as err:
                        print(f"Error extracting {name}: {err}", file=sys.stderr)
                
                # Loncat 2 baris setelah berhasil memproses Header + URL
                i += 2
            else:
                i += 1
        else:
            i += 1

except Exception as e:
    print(f"Error reading file: {e}", file=sys.stderr)
