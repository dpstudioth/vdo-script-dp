# VDO Script DP Studio

Skill สำหรับ **Claude Code** ที่แกะสคริปต์วิดีโอจากลิงก์ ออกมาเป็นตาราง Shot List ทีละช็อต

| Sequence / Time | Shot Size | Angle | Camera Movement | Description | Voiceover / Dialogue | Text on Screen | Music / SFX | Notes |
|---|---|---|---|---|---|---|---|---|

พร้อมสรุป Hook โครงเรื่อง สไตล์การตัดต่อ และสิ่งที่เอาไปใช้ต่อได้

**ทำได้เพิ่ม**
- แกะแคปชันแอด (บรีฟ) แล้วแปลไทยแบบลื่นหู ไม่แปลทีละคำ
- ดัดแปลงบทเป็นของ DP Studio หรือแบรนด์อื่น ช็อตต่อช็อต พร้อมนับคำให้ใกล้ต้นฉบับ (ห่างไม่เกิน 2 คำต่อช็อต) จะได้พูดทันจังหวะเดิม

ส่งออกเป็น 5 ไฟล์
- `script.html` หน้าเว็บตารางเทียบต้นฉบับกับบทของเรา มีภาพทุกช็อต ปุ่มคัดลอกตารางไปวางใน Google Docs
- `script.docx` ไฟล์ Word มีภาพทุกช็อต อัปขึ้น Google Drive แล้วเปิดด้วย Google เอกสารได้
- `script.xlsx` Excel มีภาพตัวอย่างของทุกช็อต
- `script.md` ตารางสำหรับอ่านหรือวางใน Notion / Obsidian
- `script.csv` นำเข้า Google Sheets ได้ ภาษาไทยไม่เพี้ยน

รองรับ YouTube, TikTok, Instagram, Facebook, Meta Ad Library และไฟล์วิดีโอในเครื่อง (mp4, mov)

---

## วิธีใช้

เปิด Claude Code แล้วพิมพ์

```
/vdo-script https://www.tiktok.com/@xxx/video/123
```

หรือพิมพ์ธรรมดาก็ได้ เช่น "แกะสคริปต์คลิปนี้ให้หน่อย https://youtu.be/xxxx"

อยากได้เวอร์ชันของเรา พิมพ์ต่อท้ายได้เลย เช่น

```
/vdo-script https://www.facebook.com/ads/library/?id=xxx ช่วยแกะสคริปต์นี้ให้เข้ากับ DP Studio
```

ไฟล์ผลลัพธ์จะอยู่ในโฟลเดอร์ `vdo-script-output/` ของโปรเจกต์ที่เปิดอยู่

---

## ติดตั้ง (ทำครั้งเดียว)

### 1. ติดตั้งโปรแกรมพื้นฐาน

**Windows** (เปิด PowerShell)
```powershell
winget install Python.Python.3.12
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg
```

**Mac** (เปิด Terminal)
```bash
brew install python yt-dlp ffmpeg
```

ปิดแล้วเปิด Terminal ใหม่ จากนั้นติดตั้งไลบรารี Python

```bash
python -m pip install requests openpyxl pillow pythainlp python-docx
```

ถ้าต้องการแกะวิดีโอจาก **Meta Ad Library** ด้วย ให้ติดตั้งเพิ่ม

```bash
python -m pip install playwright
python -m playwright install chromium
```

### 2. ดาวน์โหลด Skill ลงเครื่อง

```bash
git clone <ลิงก์ GitHub ของ repo นี้> ~/.claude/skills/vdo-script
```

Windows ใช้ path นี้แทน: `%USERPROFILE%\.claude\skills\vdo-script`

ไม่มี git ก็ได้: กด **Code > Download ZIP** บน GitHub แล้วแตกไฟล์ไปไว้ที่โฟลเดอร์ด้านบน (ต้องเห็นไฟล์ `SKILL.md` อยู่ในโฟลเดอร์ `vdo-script` โดยตรง)

### 3. ใส่ API Key สำหรับถอดเสียง (แนะนำ)

ใช้ **ElevenLabs Scribe** ถอดเสียง แม่นมากกับภาษาไทย
1. สมัครที่ [elevenlabs.io](https://elevenlabs.io) แล้วสร้าง API Key
2. คัดลอกไฟล์ `.env.example` เป็นไฟล์ชื่อ `.env` ในโฟลเดอร์ Skill
3. ใส่คีย์ของตัวเอง: `ELEVENLABS_API_KEY=xxxxxxxx`

ไม่ใส่คีย์ก็ใช้ได้ แต่จะถอดเสียงได้เฉพาะวิดีโอที่มีซับในตัว (เช่น YouTube บางคลิป)

**ห้ามอัปโหลดไฟล์ `.env` ขึ้น GitHub** (ไฟล์ `.gitignore` กันไว้ให้แล้ว)

### 4. เช็คว่าพร้อมใช้

```bash
python ~/.claude/skills/vdo-script/scripts/setup_check.py
```

ต้องขึ้น `"can_proceed": true`

---

## ปรับการแบ่งช็อต

ถ้าช็อตถูกรวมกันมากไป หรือแตกถี่เกินจริง บอก Claude ได้เลย เช่น "แบ่งช็อตละเอียดขึ้น" Claude จะรันใหม่ด้วยค่า `--threshold` ที่ต่ำลง (ค่าเริ่มต้น 0.3 · ละเอียดขึ้น 0.2 · หยาบลง 0.45)

## โครงสร้างไฟล์

```
vdo-script/
  SKILL.md                    คำสั่งการทำงานของ Claude
  scripts/extract.py          ดาวน์โหลด แบ่งช็อต ดึงภาพ ถอดเสียง
  scripts/build_sheet.py      สร้างตาราง Excel / Markdown / CSV
  scripts/wordcount.py        นับคำต้นฉบับเทียบบทดัดแปลง
  scripts/setup_check.py      เช็คความพร้อมของเครื่อง
  assets/page.html            เทมเพลตหน้าเว็บ
  references/shot-glossary.md คำศัพท์ช็อตและมุมกล้อง
  references/adaptation-guide.md หลักการแปลและดัดแปลงบท
  references/dp-studio.md     ข้อมูลแบรนด์ DP Studio
```

## ข้อควรรู้

- ใช้เพื่อศึกษา วิเคราะห์ และอ้างอิงเท่านั้น ลิขสิทธิ์วิดีโอเป็นของเจ้าของผลงาน
- วิดีโอส่วนตัวหรือที่ต้องล็อกอิน ดาวน์โหลดไม่ได้ ให้ดาวน์โหลดไฟล์ mp4 เองแล้วส่ง path ให้ Claude แทน
- ค่าถอดเสียง ElevenLabs คิดตามความยาวเสียง วิดีโอสั้น 1 นาทีใช้เครดิตน้อยมาก

---

พัฒนาโดย **DP Studio** (บริษัท ดรีม พิกเจอร์ สตูดิโอ จำกัด) · dpstudio.th@gmail.com
