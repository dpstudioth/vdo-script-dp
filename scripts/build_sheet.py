# -*- coding: utf-8 -*-
"""VDO Script DP Studio: รวม shots.json + analysis.json เป็นตาราง Script (Markdown / Excel / CSV)

ใช้: python3 build_sheet.py <work_dir>
ต้องมี <work_dir>/shots.json (จาก extract.py) และ <work_dir>/analysis.json (Claude เขียน)
"""
import csv, io, json, os, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

COLS = [('n', '#'), ('time', 'Sequence / Time'), ('shot', 'Shot Size'), ('angle', 'Angle'),
        ('movement', 'Camera Movement'), ('description', 'Description (ภาพ)'),
        ('vo', 'Voiceover / Dialogue'), ('text_on_screen', 'Text on Screen'),
        ('audio', 'Music / SFX'), ('notes', 'Notes')]


def cell(v):
    return str(v or '').replace('|', '/').replace('\n', '<br>')


def main():
    work = sys.argv[1]
    S = json.load(io.open(os.path.join(work, 'shots.json'), encoding='utf-8'))
    A = json.load(io.open(os.path.join(work, 'analysis.json'), encoding='utf-8'))
    by_n = {int(x['n']): x for x in A.get('shots', [])}
    has_th = any(x.get('vo_th') for x in A.get('shots', []))
    cols = list(COLS)
    if has_th:
        cols.insert(7, ('vo_th', 'แปลไทย'))
    rows = []
    for s in S['shots']:
        a = by_n.get(s['n'], {})
        r = {'n': s['n'], 'time': s['time'], 'frame': s['frame'], 'dur': round(s['end'] - s['start'], 1)}
        for k, _ in cols[2:]:
            r[k] = a.get(k, '')
        if not r['vo']:
            r['vo'] = s.get('vo_auto', '')
        rows.append(r)

    title = A.get('title') or S['meta'].get('title') or 'Video'
    summ = A.get('summary', {})
    info = [('ชื่อวิดีโอ', title), ('ที่มา', S['source']), ('ความยาว', '%.1f วินาที' % S['duration']),
            ('สัดส่วนภาพ', '%s (%sx%s, %s fps)' % (S['aspect'], S['width'], S['height'], S['fps'])),
            ('จำนวนช็อต', '%d ช็อต (เฉลี่ย %.1f วินาที/ช็อต)' % (S['shot_count'], S['avg_shot'])),
            ('ถอดเสียงจาก', S['transcript_source'])]
    labels = {'hook': 'Hook (3 วินาทีแรก)', 'structure': 'โครงเรื่อง', 'style': 'สไตล์ภาพและการตัดต่อ',
              'cta': 'CTA', 'takeaways': 'เอาไปใช้ต่อได้', 'notes': 'หมายเหตุ'}
    info += [(labels.get(k, k), v) for k, v in summ.items() if v]

    # Markdown
    md = ['# VDO Script: %s' % title, '', '| หัวข้อ | รายละเอียด |', '|---|---|']
    md += ['| %s | %s |' % (k, cell(v)) for k, v in info]
    md += ['', '## Shot List', '', '| ' + ' | '.join(h for _, h in cols) + ' |', '|' + '---|' * len(cols)]
    for r in rows:
        md.append('| ' + ' | '.join(cell(r.get(k)) for k, _ in cols) + ' |')
    if S.get('full_transcript'):
        md += ['', '## Transcript ทั้งหมด', '', S['full_transcript']]
    md += ['', '_สร้างด้วย VDO Script DP Studio · ใช้เพื่อศึกษาและอ้างอิงเท่านั้น ลิขสิทธิ์วิดีโอเป็นของเจ้าของผลงาน_']
    io.open(os.path.join(work, 'script.md'), 'w', encoding='utf-8').write('\n'.join(md))

    # CSV (เปิดใน Excel / Google Sheets ภาษาไทยไม่เพี้ยน)
    with io.open(os.path.join(work, 'script.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow([h for _, h in cols])
        for r in rows:
            w.writerow([r.get(k, '') for k, _ in cols])

    # Excel พร้อมภาพตัวอย่างทุกช็อต
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XImg
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from PIL import Image
    wb = Workbook()
    ws = wb.active; ws.title = 'Shot List'
    head = PatternFill('solid', fgColor='111820')
    xcols = cols[:2] + [('frame', 'Frame')] + cols[2:]
    widths = {'n': 5, 'time': 14, 'frame': 26, 'shot': 11, 'angle': 13, 'movement': 14, 'description': 40,
              'vo': 40, 'vo_th': 36, 'text_on_screen': 28, 'audio': 20, 'notes': 24}
    for c, (k, h) in enumerate(xcols, 1):
        x = ws.cell(1, c, h); x.fill = head; x.font = Font(bold=True, color='F8B93E')
        x.alignment = Alignment(vertical='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(c)].width = widths.get(k, 16)
    thumbs = os.path.join(work, 'frames', '_xlsx'); os.makedirs(thumbs, exist_ok=True)
    for i, r in enumerate(rows, 2):
        ws.row_dimensions[i].height = 100
        for c, (k, _) in enumerate(xcols, 1):
            if k == 'frame':
                if os.path.exists(r['frame']):
                    im = Image.open(r['frame']); im.thumbnail((180, 128))
                    tp = os.path.join(thumbs, os.path.basename(r['frame']).replace('.jpg', '.png'))
                    im.save(tp)
                    ws.add_image(XImg(tp), '%s%d' % (get_column_letter(c), i))
                continue
            x = ws.cell(i, c, r.get(k, ''))
            x.alignment = Alignment(vertical='top', wrap_text=True)
    ws.freeze_panes = 'D2'
    ws2 = wb.create_sheet('Summary')
    ws2.column_dimensions['A'].width = 26; ws2.column_dimensions['B'].width = 100
    for i, (k, v) in enumerate(info, 1):
        ws2.cell(i, 1, k).font = Font(bold=True)
        ws2.cell(i, 2, v).alignment = Alignment(wrap_text=True, vertical='top')
    if S.get('full_transcript'):
        n = len(info) + 2
        ws2.cell(n, 1, 'Transcript ทั้งหมด').font = Font(bold=True)
        ws2.cell(n, 2, S['full_transcript']).alignment = Alignment(wrap_text=True, vertical='top')
    xp = os.path.join(work, 'script.xlsx')
    wb.save(xp)
    print(json.dumps({'markdown': os.path.join(work, 'script.md'), 'xlsx': xp,
                      'csv': os.path.join(work, 'script.csv'), 'rows': len(rows)}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
