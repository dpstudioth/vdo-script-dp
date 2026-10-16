# -*- coding: utf-8 -*-
"""เช็คว่าเครื่องพร้อมใช้ VDO Script DP Studio หรือยัง"""
import importlib, io, json, os, shutil, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
missing_bin = [b for b in ('ffmpeg', 'ffprobe', 'yt-dlp') if not shutil.which(b)]
missing_py = []
for m in ('requests', 'openpyxl', 'PIL'):
    try:
        importlib.import_module(m)
    except ImportError:
        missing_py.append('pillow' if m == 'PIL' else m)
try:
    importlib.import_module('playwright'); playwright = True
except ImportError:
    playwright = False

key = bool(os.environ.get('ELEVENLABS_API_KEY'))
for p in (os.path.join(SKILL_DIR, '.env'), os.path.expanduser('~/.config/elevenlabs/.env')):
    if not key and os.path.exists(p):
        key = any(l.strip().startswith('ELEVENLABS_API_KEY=') and len(l.strip()) > 20 for l in io.open(p, encoding='utf-8'))

print(json.dumps({
    'can_proceed': not missing_bin and not missing_py,
    'missing_binaries': missing_bin,
    'missing_python': missing_py,
    'pip_command': ('%s -m pip install %s' % (os.path.basename(sys.executable), ' '.join(missing_py))) if missing_py else '',
    'elevenlabs_key': key,
    'meta_ad_library_support': playwright,
    'python': sys.executable,
}, ensure_ascii=False, indent=1))
