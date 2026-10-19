# -*- coding: utf-8 -*-
"""VDO Script DP Studio: นับคำบทพูดต้นฉบับเทียบกับบทดัดแปลง ทีละช็อต

ใช้: python3 wordcount.py <work_dir>
อ่าน shots.json + analysis.json แล้วพิมพ์จำนวนคำต่อช็อต ส่วนต่าง และช็อตที่ห่างเกิน 2 คำ
ภาษาไทยตัดคำด้วย PyThaiNLP (ถ้าไม่ได้ติดตั้งจะประมาณจากจำนวนตัวอักษร)
"""
import io, json, os, re, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

TOLERANCE = 2  # ส่วนต่างจำนวนคำต่อช็อตที่ยอมรับได้

try:
    from pythainlp.tokenize import word_tokenize
    EXACT = True
except ImportError:
    word_tokenize = None
    EXACT = False

THAI = re.compile(r'[ก-ฮ]')
EMPTY = ('', '-')


def _clean(t):
    t = (t or '').strip()
    return '' if t in EMPTY or (t.startswith('[') and t.endswith(']')) else re.sub(r'\[[^\]]*\]', ' ', t)


def count_words(text):
    """นับคำ ใช้ได้ทั้งไทยและอังกฤษ (ข้อความไทยที่มีคำอังกฤษปนก็นับรวมกัน)"""
    t = _clean(text)
    if not t:
        return 0
    if not THAI.search(t):
        return len([w for w in t.split() if re.search(r'[A-Za-z0-9]', w)])
    if EXACT:
        toks = word_tokenize(t, engine='newmm', keep_whitespace=False)
        return len([w for w in toks if re.search(r'[ก-ฮA-Za-z0-9]', w)])
    # ไม่มี PyThaiNLP: คำไทยเฉลี่ยประมาณ 4 ตัวอักษร
    latin = len(re.findall(r'[A-Za-z0-9]+', t))
    thai_chars = len(re.findall(r'[ก-ฮเ-ไ]', t))
    return latin + max(1, round(thai_chars / 4))


def badge_class(diff):
    return 'ok' if abs(diff) <= TOLERANCE else 'off'


def compare(S, A):
    """คืนรายการต่อช็อต: n, src, adapt, diff"""
    by_n = {int(x['n']): x for x in A.get('shots', [])}
    out = []
    for s in S['shots']:
        a = by_n.get(s['n'], {})
        src = count_words(a.get('vo') or s.get('vo_auto', ''))
        ad = count_words(a.get('adapt_vo', ''))
        out.append({'n': s['n'], 'src': src, 'adapt': ad, 'diff': ad - src, 'dur': round(s['end'] - s['start'], 1)})
    return out


def main():
    work = sys.argv[1]
    S = json.load(io.open(os.path.join(work, 'shots.json'), encoding='utf-8'))
    A = json.load(io.open(os.path.join(work, 'analysis.json'), encoding='utf-8'))
    rows = compare(S, A)
    off = [r['n'] for r in rows if r['src'] and abs(r['diff']) > TOLERANCE]
    print(json.dumps({
        'exact_thai_count': EXACT,
        'tolerance': TOLERANCE,
        'total_source': sum(r['src'] for r in rows),
        'total_adapt': sum(r['adapt'] for r in rows),
        'shots_off': off,
        'shots': rows,
    }, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
