# -*- coding: utf-8 -*-
"""
SportWay - خادم الطباعة المتجهية
- يحافظ على أبعاد الباترون الأصلية (الصفحة تُنسخ كما هي من ملف المصنع)
- النصوص تُكتب كمتجهات (Vector) بخط مدمج، والشعارات تُدرج بدقتها الأصلية بدون أي ضغط
- تشغيل:  python print_server.py
"""
import os
import re
import glob
import json
import uuid
import unicodedata
from datetime import datetime
from urllib.parse import quote

try:
    import pymupdf as fitz  # الاسم الحديث للمكتبة
except ImportError:
    import fitz  # PyMuPDF القديمة
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import arabic_reshaper
from bidi.algorithm import get_display
from fonts_config import FONT_SPECS

# ---------------------------------------------------------------- الإعدادات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
for _d in (TEMPLATES_DIR, OUTPUT_DIR, ASSETS_DIR, FONTS_DIR):
    os.makedirs(_d, exist_ok=True)

VALID_SIZES = ("S", "M", "L", "XL")

# معايرة موضع النص عمودياً: كسر من حجم الخط (+ ينزل النص للأسفل، - يرفعه للأعلى)
# إذا لاحظتم في الاختبار أن الطباعة أعلى/أخفض قليلاً من المعاينة عدّلوا هذا الرقم فقط.
BASELINE_ADJUST = 0.0

# إذا اضطر النظام لتصغير الخط أكثر من هذه النسبة ليحتوي الاسم، يظهر تنبيه للموظف
MIN_FIT_RATIO = 0.55

# أسماء ملفات الخطوط المتوقعة داخل مجلد fonts/ (تُعرَّف في fonts_config.py، وتُحمَّل بـ download_fonts.py)
FONT_CANDIDATES = {fam: [spec[2]] for fam, spec in FONT_SPECS.items()}
FONT_CANDIDATES["Cairo"] += ["Cairo.ttf", "cairo.ttf"]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # باترونات الرول قد تكون ثقيلة
CORS(app, expose_headers=["X-Print-Warnings", "X-Print-Count", "Content-Disposition"])


# ---------------------------------------------------------------- أدوات مساعدة
def norm_size(v):
    return str(v or "M").strip().upper()


def has_arabic(text):
    return bool(re.search(r"[\u0600-\u06FF]", str(text)))


def _make_reshaper(**cfg):
    try:
        return arabic_reshaper.ArabicReshaper(configuration=cfg)
    except Exception:
        return arabic_reshaper  # يرجع للإعداد الافتراضي إذا فشل الإعداد المخصص


# خطوط Google العربية غالباً لا تحتوي الأشكال المنفصلة (Isolated) في ترميز Presentation Forms،
# لذلك نطلب من المشكّل استخدام الحرف الأساسي بدلها (وإلا تظهر مربعات فارغة مثل ا / د / ر / و)
_RESHAPER_LIG = _make_reshaper(use_unshaped_instead_of_isolated=True)
_RESHAPER_NOLIG = _make_reshaper(use_unshaped_instead_of_isolated=True, support_ligatures=False)


def repair(text, font):
    """أي حرف غير موجود في الخط نستبدله بالحرف الأساسي المكافئ له (NFKC) إن كان موجوداً."""
    out = []
    for ch in text:
        if ch.isspace() or font.has_glyph(ord(ch)):
            out.append(ch)
            continue
        base = unicodedata.normalize("NFKC", ch)
        if base != ch and all(font.has_glyph(ord(c)) for c in base):
            out.append(base[::-1])  # النص هنا بترتيب العرض (يسار->يمين) فنعكس التوسعات مثل لا
        else:
            out.append(ch)
    return "".join(out)


def shape_for_font(raw, font):
    """تشكيل الحروف العربية + ترتيب الاتجاه، مضبوط على الحروف المتوفرة في هذا الخط بالذات."""
    t = str(raw if raw is not None else "").strip()
    if not t or not has_arabic(t):
        return t
    reshaper = _RESHAPER_LIG if font.has_glyph(0xFEFB) else _RESHAPER_NOLIG  # FEFB = ligature لا
    try:
        shaped = get_display(reshaper.reshape(t))
    except Exception:
        shaped = t
    return repair(shaped, font)


def hex_to_rgb(h, default=(1, 1, 1)):
    if not h or not isinstance(h, str):
        return default
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return default
    try:
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return default


def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def find_template(size):
    candidates = [
        f"current_{size}.pdf",
        f"{size}- T SHIRT.pdf",
        f"{size}.pdf",
    ]
    for name in candidates:
        p = os.path.join(TEMPLATES_DIR, name)
        if os.path.exists(p):
            return p
    return None


def find_asset(asset_id):
    if not re.fullmatch(r"[0-9a-f]{32}", str(asset_id or "")):
        return None
    hits = glob.glob(os.path.join(ASSETS_DIR, asset_id + ".*"))
    return hits[0] if hits else None


# ---------------------------------------------------------------- الخطوط
_font_cache = {}


def _load_font(path):
    if path not in _font_cache:
        _font_cache[path] = fitz.Font(fontfile=path)
    return _font_cache[path]


def find_font_file(family):
    for fname in FONT_CANDIDATES.get(family, []):
        for d in (FONTS_DIR, BASE_DIR):
            p = os.path.join(d, fname)
            if os.path.exists(p):
                return p
    return None


def _covers(font, text):
    return all(font.has_glyph(ord(c)) for c in text if not c.isspace())


def _warn(warnings, msg):
    if msg not in warnings:
        warnings.append(msg)


def resolve_font(family, raw, warnings):
    """يرجع (tag, path, Font, النص_المشكّل). يتراجع لـ Cairo إذا الخط غير موجود أو لا يدعم حروف النص."""
    tried = []
    for fam in (family, "Cairo"):
        if fam in tried:
            continue
        tried.append(fam)
        path = find_font_file(fam)
        if path is None:
            _warn(warnings, f"الخط «{fam}» غير موجود في مجلد fonts — شغّلوا: python download_fonts.py")
            continue
        font = _load_font(path)
        shaped = shape_for_font(raw, font)
        if _covers(font, shaped):
            if fam != family:
                _warn(warnings, f"الخط «{family}» لا يدعم بعض حروف «{raw}» — تم استخدام Cairo لهذه الكتابة")
            tag = "F" + re.sub(r"\W", "", os.path.splitext(os.path.basename(path))[0])
            return tag, path, font, shaped
    _warn(warnings, "لا يوجد خط مناسب في مجلد fonts — الكتابة العربية لن تظهر. شغّلوا: python download_fonts.py")
    return "helv", None, fitz.Font("helv"), str(raw)


# ---------------------------------------------------------------- الرسم
def draw_text(page, text, box, cfg, warnings, scale=1.0, dx=0.0, dy=0.0):
    raw = str(text if text is not None else "").strip()
    if not raw:
        return
    ph = page.rect.height
    tag, path, font, shaped = resolve_font(cfg.get("fontFamily", "Cairo"), raw, warnings)

    fs = num(cfg.get("relativeFontSize"), 0.04) * ph
    tw = font.text_length(shaped, fontsize=fs)

    # احتواء تلقائي: يصغّر الخط فقط إذا تجاوز النص عرض الصندوق المحدد في المحرر
    if box.width > 0 and tw > box.width:
        ratio = box.width / tw
        fs *= ratio
        tw = box.width
        if ratio < MIN_FIT_RATIO:
            warnings.append(f"«{text}»: النص طويل جداً وتم تصغيره إلى {int(ratio * 100)}% — راجعوه")

    # التعديل الفردي من المعاينة (يُطبّق بعد الاحتواء)
    fs *= scale
    tw *= scale

    cx = (box.x0 + box.x1) / 2.0
    cy = (box.y0 + box.y1) / 2.0
    x = cx - tw / 2.0 + dx
    # توسيط عمودي بحسب مقاييس الخط (ascender/descender) مثل ما يفعل المتصفح
    y = cy + (font.ascender + font.descender) / 2.0 * fs + BASELINE_ADJUST * fs + dy

    fill = hex_to_rgb(cfg.get("fill"), (1, 1, 1))
    stroke_w = num(cfg.get("strokeRel"), 0.0) * ph * scale

    kw = {"fontsize": fs, "fontname": tag}
    if path:
        page.insert_font(fontname=tag, fontfile=path)

    pt = fitz.Point(x, y)
    if stroke_w > 0:
        stroke = hex_to_rgb(cfg.get("stroke"), (0, 0, 0))
        page.insert_text(pt, shaped, color=stroke, fill=fill, render_mode=2, border_width=stroke_w, **kw)
    else:
        page.insert_text(pt, shaped, color=fill, fill=fill, **kw)


def box_from_cfg(page, cfg, default_w, default_h):
    r = page.rect
    cx = r.x0 + r.width * num(cfg.get("centerXPercent"), 50) / 100.0
    cy = r.y0 + r.height * num(cfg.get("centerYPercent"), 50) / 100.0
    w = r.width * num(cfg.get("widthPercent"), default_w) / 100.0
    h = r.height * num(cfg.get("heightPercent"), default_h) / 100.0
    return fitz.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def draw_static(page, el, image_xrefs, warnings):
    box = box_from_cfg(page, el, 15, 10)
    if el.get("type") == "image":
        aid = el.get("assetId")
        path = find_asset(aid)
        if not path:
            msg = "أحد الشعارات غير موجود في السيرفر — ارفعوه من جديد في المحرر"
            if msg not in warnings:
                warnings.append(msg)
            return
        if aid in image_xrefs:
            page.insert_image(box, xref=image_xrefs[aid], keep_proportion=True, overlay=True)
        else:
            # الصورة تُدرج بملفها الأصلي بدون إعادة ضغط (PNG يبقى PNG، JPG يبقى JPG)
            image_xrefs[aid] = page.insert_image(box, filename=path, keep_proportion=True, overlay=True)
    elif el.get("type") == "text":
        draw_text(page, el.get("text", ""), box, el, warnings)


# ---------------------------------------------------------------- المسارات
@app.route("/api/health")
def health():
    return jsonify({"success": True})


@app.route("/api/upload-template", methods=["POST"])
def upload_template():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "لا يوجد ملف"}), 400
        size = norm_size(request.form.get("size", "M"))
        if size not in VALID_SIZES:
            return jsonify({"success": False, "message": "مقاس غير معروف"}), 400
        save_path = os.path.join(TEMPLATES_DIR, f"current_{size}.pdf")
        request.files["file"].save(save_path)

        doc = fitz.open(save_path)
        page = doc[0]
        info = {
            "success": True,
            "size": size,
            "widthPt": page.rect.width,
            "heightPt": page.rect.height,
            "widthCm": round(page.rect.width / 72 * 2.54, 1),
            "heightCm": round(page.rect.height / 72 * 2.54, 1),
            "pages": len(doc),
            "rotation": page.rotation,
        }
        doc.close()
        print(f"✅ حُفظ الباترون {size}: {info['widthCm']} × {info['heightCm']} سم")
        return jsonify(info)
    except Exception as e:
        return jsonify({"success": False, "message": f"ملف PDF غير صالح: {e}"}), 400


@app.route("/api/template/<size>")
def get_template(size):
    path = find_template(norm_size(size))
    if not path:
        return jsonify({"success": False, "message": "لا يوجد باترون"}), 404
    return send_file(path, mimetype="application/pdf")


@app.route("/api/template-info/<size>")
def template_info(size):
    path = find_template(norm_size(size))
    if not path:
        return jsonify({"success": False, "message": "لا يوجد باترون"}), 404
    doc = fitz.open(path)
    r = doc[0].rect
    out = {"success": True, "widthPt": r.width, "heightPt": r.height,
           "widthCm": round(r.width / 72 * 2.54, 1), "heightCm": round(r.height / 72 * 2.54, 1)}
    doc.close()
    return jsonify(out)


@app.route("/api/template-preview/<size>")
def template_preview(size):
    """صورة PNG خفيفة للباترون تُستخدم في صفحة المعاينة فقط (ليست للطباعة)."""
    path = find_template(norm_size(size))
    if not path:
        return jsonify({"success": False, "message": "لا يوجد باترون"}), 404
    target_w = min(int(request.args.get("w", 900)), 2000)
    doc = fitz.open(path)
    page = doc[0]
    z = target_w / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
    data = pix.tobytes("png")
    doc.close()
    return Response(data, mimetype="image/png", headers={"Cache-Control": "no-store"})


@app.route("/api/upload-asset", methods=["POST"])
def upload_asset():
    """يحفظ الشعار بملفه الأصلي بالدقة الكاملة."""
    if "file" not in request.files:
        return jsonify({"success": False, "message": "لا يوجد ملف"}), 400
    f = request.files["file"]
    ext = os.path.splitext(f.filename or "")[1].lower().lstrip(".")
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ("png", "jpg"):
        return jsonify({"success": False, "message": "الصيغ المدعومة للشعارات: PNG أو JPG"}), 400
    asset_id = uuid.uuid4().hex
    f.save(os.path.join(ASSETS_DIR, f"{asset_id}.{ext}"))
    return jsonify({"success": True, "assetId": asset_id, "url": f"/api/asset/{asset_id}"})


@app.route("/api/asset/<asset_id>")
def get_asset(asset_id):
    path = find_asset(asset_id)
    if not path:
        return jsonify({"success": False}), 404
    return send_file(path)


@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json(silent=True) or {}
        size = norm_size(data.get("size", "M"))
        roster = data.get("roster", [])
        cfg = data.get("masterConfig", {}) or {}
        order_title = re.sub(r'[\\/:*?"<>|]', "", str(data.get("orderTitle") or "SportWay")).strip() or "SportWay"

        name_cfg = cfg.get("nameConfig") or {}
        num_cfg = cfg.get("numberConfig") or {}
        static_elements = cfg.get("staticElements") or []

        players = [p for p in roster if norm_size(p.get("jerseySize", p.get("size", "M"))) == size]
        if not players:
            return jsonify({"success": False, "message": f"لا يوجد لاعبين بمقاس {size}"}), 400

        template_path = find_template(size)
        if not template_path:
            return jsonify({"success": False, "message": f"ملف الباترون للمقاس {size} غير موجود — ارفعوه من المحرر"}), 404

        template = fitz.open(template_path)
        if template[0].rotation != 0:
            return jsonify({"success": False, "message": "الباترون مدوَّر (Rotation). صدّروه من برنامج التصميم بدون تدوير"}), 400

        warnings = []
        image_xrefs = {}
        out = fitz.open()

        for p in players:
            # نسخ صفحة الباترون الأولى كما هي (نفس الأبعاد تماماً)
            out.insert_pdf(template, from_page=0, to_page=0)
            page = out[out.page_count - 1]
            pw, ph = page.rect.width, page.rect.height

            for el in static_elements:
                draw_static(page, el, image_xrefs, warnings)

            edit = p.get("edit") or {}
            name = edit["name"] if edit.get("name") is not None else p.get("name", "")
            number = edit["number"] if edit.get("number") is not None else p.get("number", "")
            n_scale = min(max(num(edit.get("nameScale"), 100) / 100.0, 0.3), 3.0)
            m_scale = min(max(num(edit.get("numScale"), 100) / 100.0, 0.3), 3.0)

            # تعديل خاص بهذا التيشيرت فقط (مكان/حجم/خط/لون) يتغلب على التصميم العام
            n_cfg = {**name_cfg, **(edit.get("nameCfg") or {})}
            m_cfg = {**num_cfg, **(edit.get("numCfg") or {})}
            draw_text(page, name, box_from_cfg(page, n_cfg, 25, 8), n_cfg, warnings, scale=n_scale)
            draw_text(page, number, box_from_cfg(page, m_cfg, 20, 15), m_cfg, warnings, scale=m_scale)

        template.close()

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{order_title}_{size}_{stamp}.pdf"
        out_path = os.path.join(OUTPUT_DIR, filename)
        # garbage=4 يدمج الكائنات المتطابقة (الباترون/الخطوط/الشعارات) فيبقى الملف خفيفاً بدون أي خسارة جودة
        out.save(out_path, garbage=4, deflate=True)
        out.close()

        print(f"✅ {len(players)} تيشيرت مقاس {size} -> {out_path}")
        for w in warnings:
            print("⚠️", w)

        resp = send_file(out_path, mimetype="application/pdf", as_attachment=True, download_name=filename)
        resp.headers["X-Print-Count"] = str(len(players))
        resp.headers["X-Print-Warnings"] = quote(json.dumps(warnings, ensure_ascii=False))
        return resp

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    _missing = [f for f in FONT_CANDIDATES if not find_font_file(f)]
    if _missing:
        print("⚠️ خطوط ناقصة في مجلد fonts:", "، ".join(_missing))
        print("   شغّلوا في نافذة ثانية:  python download_fonts.py")
    print("🚀 خادم الطباعة المتجهية: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)