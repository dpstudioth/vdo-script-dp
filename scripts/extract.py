# -*- coding: utf-8 -*-
"""VDO Script DP Studio: ดาวน์โหลดวิดีโอ แบ่งช็อต ดึงภาพตัวอย่าง และถอดเสียงพร้อมเวลา

ใช้: python3 extract.py <ลิงก์หรือไฟล์วิดีโอ> [--out โฟลเดอร์] [--threshold 0.3]
ผลลัพธ์: <out>/<ชื่องาน>/shots.json + frames/ + sheets/ (ภาพรวมช็อต)
"""
import argparse, glob, io, json, os, re, shutil, subprocess, sys, urllib.request
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)


def log(msg):
    print('[vdo-script] ' + msg, file=sys.stderr, flush=True)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', **kw)


def need(binary):
    if not shutil.which(binary):
        sys.exit('ไม่พบโปรแกรม %s กรุณาติดตั้งก่อน (ดู README.md)' % binary)


# ---------- 1. หาไฟล์วิดีโอ ----------
def slug_for(source):
    base = re.sub(r'https?://(www\.)?', '', source)
    base = re.sub(r'[^0-9A-Za-z]+', '-', base).strip('-')[:50] or 'video'
    return datetime.now().strftime('%Y%m%d-%H%M%S') + '_' + base


def fetch_meta_ad(url, dest):
    """Meta Ad Library: เปิดหน้าด้วย Playwright แล้วดึงลิงก์ไฟล์วิดีโอ"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('ลิงก์ Meta Ad Library ต้องใช้ Playwright: pip install playwright แล้ว python -m playwright install chromium')
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(locale='en-US', user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/129.0 Safari/537.36')
        pg.goto(url, wait_until='domcontentloaded', timeout=60000)
        pg.wait_for_timeout(9000)
        src = pg.eval_on_selector('video', 'e => e.currentSrc || e.src') if pg.query_selector('video') else None
        text = pg.inner_text('body')
        b.close()
    if not src:
        sys.exit('ไม่พบวิดีโอในหน้า Ad Library นี้ (แอดอาจเป็นภาพนิ่ง หรือหมดอายุแล้ว)')
    req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
    with open(dest, 'wb') as f:
        f.write(urllib.request.urlopen(req, timeout=180).read())
    m = re.search(r'Sponsored\n(.+?)\n', text)
    return {'title': 'Meta Ad', 'ad_text': m.group(1) if m else ''}


def get_video(source, work):
    meta = {'title': os.path.basename(source)}
    dest = os.path.join(work, 'video.mp4')
    if os.path.isfile(source):
        shutil.copy(source, dest)
        return dest, meta
    if 'facebook.com/ads/library' in source:
        meta.update(fetch_meta_ad(source, dest))
        return dest, meta
    need('yt-dlp')
    log('กำลังดาวน์โหลดวิดีโอ ...')
    r = run(['yt-dlp', '--no-playlist', '-f', 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b',
             '--merge-output-format', 'mp4', '-o', os.path.join(work, 'video.%(ext)s'),
             '--write-info-json', '--write-auto-subs', '--write-subs', '--sub-langs', 'th.*,en.*',
             '--sub-format', 'vtt', source])
    vids = [f for f in glob.glob(os.path.join(work, 'video.*')) if f.endswith(('.mp4', '.mkv', '.webm', '.mov'))]
    if not vids:
        sys.exit('ดาวน์โหลดไม่สำเร็จ: ' + (r.stderr or r.stdout)[-600:])
    if vids[0] != dest:
        os.replace(vids[0], dest)
    info = glob.glob(os.path.join(work, '*.info.json'))
    if info:
        j = json.load(io.open(info[0], encoding='utf-8'))
        meta.update({'title': j.get('title') or meta['title'], 'uploader': j.get('uploader'),
                     'webpage_url': j.get('webpage_url'), 'description': (j.get('description') or '')[:1500]})
    return dest, meta


# ---------- 2. ข้อมูลวิดีโอ + แบ่งช็อต ----------
def probe(video):
    r = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
             'stream=width,height,r_frame_rate:format=duration', '-of', 'json', video])
    j = json.loads(r.stdout)
    st = j['streams'][0]
    num, den = st.get('r_frame_rate', '30/1').split('/')
    w, h = int(st['width']), int(st['height'])
    ratio = w / h
    aspect = '9:16' if abs(ratio - 9 / 16) < 0.05 else '16:9' if abs(ratio - 16 / 9) < 0.05 else \
        '1:1' if abs(ratio - 1) < 0.05 else '4:5' if abs(ratio - 0.8) < 0.04 else '%d:%d' % (w, h)
    return {'duration': float(j['format']['duration']), 'width': w, 'height': h,
            'fps': round(float(num) / float(den or 1), 2), 'aspect': aspect}


def scene_cuts(video, threshold):
    r = run(['ffmpeg', '-hide_banner', '-i', video, '-filter:v',
             "select='gt(scene,%s)',showinfo" % threshold, '-an', '-f', 'null', '-'])
    return [float(x) for x in re.findall(r'pts_time:([0-9.]+)', r.stderr)]


def build_shots(video, duration, threshold, min_shot, max_shots):
    t = threshold
    while True:
        cuts = scene_cuts(video, t)
        bounds = [0.0] + [c for c in cuts if 0.05 < c < duration - 0.05] + [duration]
        merged = [bounds[0]]
        for b in bounds[1:-1]:
            if b - merged[-1] >= min_shot:
                merged.append(b)
        if duration - merged[-1] < min_shot and len(merged) > 1:
            merged.pop()
        merged.append(duration)
        shots = list(zip(merged[:-1], merged[1:]))
        if len(shots) <= max_shots or t >= 0.6:
            return shots, t
        t = round(t + 0.1, 2)
        log('ช็อตเยอะเกิน %d ช็อต ลองค่า threshold %s' % (max_shots, t))


def grab_frames(video, shots, work):
    os.makedirs(os.path.join(work, 'frames'), exist_ok=True)
    out = []
    for i, (s, e) in enumerate(shots, 1):
        mid = s + (e - s) / 2
        f = os.path.join(work, 'frames', 'shot_%03d.jpg' % i)
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', '%.3f' % mid, '-i', video,
             '-frames:v', '1', '-vf', 'scale=480:-2', '-q:v', '3', f])
        out.append(f)
    return out


def fmt(t):
    return '%d:%04.1f' % (int(t // 60), t % 60)


def contact_sheets(frames, shots, work, per_sheet=12, cols=4):
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(os.path.join(work, 'sheets'), exist_ok=True)
    try:
        font = ImageFont.load_default(size=26)
    except TypeError:
        font = ImageFont.load_default()
    sheets = []
    for k in range(0, len(frames), per_sheet):
        chunk = [(i, frames[i]) for i in range(k, min(k + per_sheet, len(frames))) if os.path.exists(frames[i])]
        if not chunk:
            continue
        ims = [Image.open(f).convert('RGB') for _, f in chunk]
        tw = 360
        th = max(int(im.height * tw / im.width) for im in ims)
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * (tw + 12) + 12, rows * (th + 52) + 12), (17, 24, 32))
        d = ImageDraw.Draw(sheet)
        for j, ((i, _), im) in enumerate(zip(chunk, ims)):
            x, y = 12 + (j % cols) * (tw + 12), 12 + (j // cols) * (th + 52)
            im = im.resize((tw, int(im.height * tw / im.width)))
            sheet.paste(im, (x, y + 40))
            s, e = shots[i]
            d.text((x, y + 6), '#%d  %s-%s' % (i + 1, fmt(s), fmt(e)), fill=(248, 185, 62), font=font)
        p = os.path.join(work, 'sheets', 'sheet_%02d.jpg' % (len(sheets) + 1))
        sheet.save(p, quality=85)
        sheets.append(p)
    return sheets


# ---------- 3. ถอดเสียง ----------
def eleven_key():
    if os.environ.get('ELEVENLABS_API_KEY'):
        return os.environ['ELEVENLABS_API_KEY']
    for p in (os.path.join(SKILL_DIR, '.env'), os.path.expanduser('~/.config/elevenlabs/.env')):
        if os.path.exists(p):
            for line in io.open(p, encoding='utf-8'):
                if line.strip().startswith('ELEVENLABS_API_KEY='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    return None


def transcribe_elevenlabs(video, work, key):
    import requests
    audio = os.path.join(work, 'audio.mp3')
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', video, '-vn', '-ac', '1', '-ar', '16000', audio])
    if not os.path.exists(audio) or os.path.getsize(audio) < 2000:
        return None, None
    log('กำลังถอดเสียงด้วย ElevenLabs Scribe ...')
    with open(audio, 'rb') as f:
        r = requests.post('https://api.elevenlabs.io/v1/speech-to-text', headers={'xi-api-key': key},
                          data={'model_id': 'scribe_v1', 'diarize': 'true', 'tag_audio_events': 'true'},
                          files={'file': f}, timeout=600)
    if r.status_code != 200:
        log('ElevenLabs ตอบกลับ %s: %s' % (r.status_code, r.text[:300]))
        return None, None
    j = r.json()
    io.open(os.path.join(work, 'transcript_raw.json'), 'w', encoding='utf-8').write(json.dumps(j, ensure_ascii=False))
    words = [{'start': w.get('start', 0), 'end': w.get('end', 0), 'text': w.get('text', ''),
              'type': w.get('type'), 'speaker': w.get('speaker_id')} for w in j.get('words', [])]
    return words, j.get('language_code')


def parse_vtt(path):
    words = []
    text = io.open(path, encoding='utf-8').read()
    for m in re.finditer(r'(\d+:)?(\d+):(\d+\.\d+) --> (\d+:)?(\d+):(\d+\.\d+)[^\n]*\n(.+?)(?:\n\n|\Z)', text, re.S):
        st = int((m.group(1) or '0:')[:-1]) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        en = int((m.group(4) or '0:')[:-1]) * 3600 + int(m.group(5)) * 60 + float(m.group(6))
        line = re.sub(r'<[^>]+>', '', m.group(7)).replace('\n', ' ').strip()
        if line and (not words or words[-1]['text'] != line):
            words.append({'start': st, 'end': en, 'text': line + ' ', 'type': 'word', 'speaker': None})
    return words


def assign_vo(shots, words):
    out = []
    for s, e in shots:
        parts, speakers = [], []
        for w in words or []:
            mid = (w['start'] + w['end']) / 2
            if s <= mid < e:
                if w.get('type') == 'audio_event':
                    parts.append(' ' + w['text'] + ' ')
                    continue
                sp = w.get('speaker')
                if sp and (not speakers or speakers[-1] != sp):
                    speakers.append(sp)
                    if len(set(x.get('speaker') for x in words if x.get('speaker'))) > 1:
                        parts.append(' [%s] ' % sp)
                parts.append(w['text'])
        out.append({'vo': re.sub(r'\s+', ' ', ''.join(parts)).strip(), 'speakers': speakers})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('--out', default=os.path.join(os.getcwd(), 'vdo-script-output'))
    ap.add_argument('--threshold', type=float, default=0.3, help='ความไวในการจับการตัดช็อต (ต่ำ = จับได้มากขึ้น)')
    ap.add_argument('--min-shot', type=float, default=0.4)
    ap.add_argument('--max-shots', type=int, default=120)
    ap.add_argument('--no-transcribe', action='store_true')
    a = ap.parse_args()
    need('ffmpeg'); need('ffprobe')

    work = os.path.join(a.out, slug_for(a.source))
    os.makedirs(work, exist_ok=True)
    video, meta = get_video(a.source, work)
    info = probe(video)
    log('ความยาว %.1f วินาที %sx%s (%s)' % (info['duration'], info['width'], info['height'], info['aspect']))
    shots, used_t = build_shots(video, info['duration'], a.threshold, a.min_shot, a.max_shots)
    log('แบ่งได้ %d ช็อต' % len(shots))
    frames = grab_frames(video, shots, work)
    sheets = contact_sheets(frames, shots, work)

    words, lang, tsrc = None, None, 'none'
    if not a.no_transcribe:
        key = eleven_key()
        if key:
            words, lang = transcribe_elevenlabs(video, work, key)
            tsrc = 'elevenlabs' if words is not None else 'none'
        if words is None:
            vtts = sorted(glob.glob(os.path.join(work, '*.vtt')), key=lambda p: ('.th' not in p, p))
            if vtts:
                words, tsrc = parse_vtt(vtts[0]), 'captions:' + os.path.basename(vtts[0])
    vo = assign_vo(shots, words)
    full = re.sub(r'\s+', ' ', ''.join(w['text'] for w in (words or []) if w.get('type') != 'audio_event')).strip()

    data = dict(source=a.source, work_dir=work, video=video, created=datetime.now().isoformat(timespec='seconds'),
                meta=meta, **info, scene_threshold=used_t, shot_count=len(shots),
                avg_shot=round(info['duration'] / max(1, len(shots)), 2), transcript_source=tsrc,
                language=lang, full_transcript=full, sheets=sheets,
                shots=[{'n': i + 1, 'start': round(s, 2), 'end': round(e, 2), 'time': '%s-%s' % (fmt(s), fmt(e)),
                        'frame': frames[i], 'vo_auto': vo[i]['vo'], 'speakers': vo[i]['speakers']}
                       for i, (s, e) in enumerate(shots)])
    p = os.path.join(work, 'shots.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=1))
    print(json.dumps({'shots_json': p, 'work_dir': work, 'shot_count': len(shots), 'duration': info['duration'],
                      'aspect': info['aspect'], 'transcript_source': tsrc, 'language': lang, 'sheets': sheets},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
