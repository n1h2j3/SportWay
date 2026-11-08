# -*- coding: utf-8 -*-
"""
تحميل الخطوط تلقائياً من Google Fonts إلى مجلد fonts/
التشغيل (من نفس مجلد المشروع):   python download_fonts.py
"""
import os
import re
import urllib.parse
import urllib.request

from fonts_config import FONT_SPECS, FONTS_DIR

os.makedirs(FONTS_DIR, exist_ok=True)
# Google يرجع روابط TTF للمتصفحات القديمة / الأدوات (بدل woff2)
USER_AGENTS = ["Wget/1.21", "Mozilla/4.0", "curl/8.4.0"]


def http_get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def find_ttf_url(family, weight):
    css_url = "https://fonts.googleapis.com/css2?family=%s:wght@%d" % (urllib.parse.quote_plus(family), weight)
    for ua in USER_AGENTS:
        try:
            css = http_get(css_url, ua).decode("utf-8", "ignore")
        except Exception:
            continue
        urls = re.findall(r"url\((https://[^)]+?\.ttf)\)", css)
        if urls:
            return urls[-1]
    return None


def is_font(data):
    return data[:4] in (b"\x00\x01\x00\x00", b"true", b"OTTO")


ok, failed = 0, []
for key, (gname, weight, fname, _) in FONT_SPECS.items():
    dest = os.path.join(FONTS_DIR, fname)
    if os.path.exists(dest):
        print("✔ موجود:", fname)
        ok += 1
        continue
    try:
        url = find_ttf_url(gname, weight)
        if not url:
            raise RuntimeError("لم يتم العثور على رابط الخط")
        data = http_get(url, USER_AGENTS[0])
        if not is_font(data):
            raise RuntimeError("الملف المحمّل ليس خطاً صالحاً")
        with open(dest, "wb") as f:
            f.write(data)
        print("⬇ تم تحميل:", fname)
        ok += 1
    except Exception as e:
        print("✘ فشل:", fname, "-", e)
        failed.append(fname)

print("\nالنتيجة: %d خط جاهز" % ok)
if failed:
    print("الخطوط التي فشلت (حمّلها يدوياً من fonts.google.com وضعها في مجلد fonts):")
    for f in failed:
        print("  -", f)