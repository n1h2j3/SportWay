import os
import base64
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)
CORS(app)

OUTPUT_DIR = "factory_m_test"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fix_arabic(text):
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)

@app.route('/api/generate-m-sample', methods=['POST'])
def generate_m_sample():
    try:
        data = request.json or {}
        roster = data.get('roster', [])
        design_bg_data = data.get('designBg', '')

        # تصفية لاعبي مقاس M
        m_players = [
            p for p in roster
            if str(p.get('jerseySize', p.get('size', 'M'))).strip().upper() == 'M'
        ]

        if not m_players:
            return jsonify({'success': False, 'message': 'لا يوجد لاعبين بمقاس M في الكشف!'}), 400

        # حفظ صورة التصميم الأخضر لاستخدامها في الدمج
        temp_img_path = None
        if design_bg_data and ',' in design_bg_data:
            header, encoded = design_bg_data.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            temp_img_path = os.path.join(OUTPUT_DIR, "current_design_art.png")
            with open(temp_img_path, "wb") as f:
                f.write(img_bytes)

        template_path = "templates/M.pdf"
        if not os.path.exists(template_path):
            template_path = "templates/M- T SHIRT.pdf"

        output_pdf_path = os.path.join(OUTPUT_DIR, "FACTORY_TEST_M_ROLL.pdf")
        merged_doc = fitz.open()

        for player in m_players:
            doc = fitz.open(template_path)
            page = doc[0]
            page_rect = page.rect

            # 1. دمج خلفية التيشيرت الخضراء بكامل أبعاد الصفحة أولاً
            if temp_img_path and os.path.exists(temp_img_path):
                page.insert_image(page_rect, filename=temp_img_path, overlay=False)

            # 2. إحداثيات ظهر التيشيرت (الجهة اليسرى العلوية)
            back_center_x = page_rect.width * 0.245
            name_y = page_rect.height * 0.22
            num_y = page_rect.height * 0.35

            p_name = fix_arabic(player.get('name', ''))
            p_num = str(player.get('number', ''))

            name_size = page_rect.height * 0.028
            num_size = page_rect.height * 0.095

            # طباعة الاسم بلون أبيض وإطار واضح للطباعة
            name_len = fitz.get_text_length(p_name, fontname="helv", fontsize=name_size)
            page.insert_text(
                fitz.Point(back_center_x - (name_len / 2.0), name_y),
                p_name,
                fontname="helv",
                fontsize=name_size,
                color=(1, 1, 1)  # أبيض
            )

            # طباعة الرقم
            num_len = fitz.get_text_length(p_num, fontname="helv", fontsize=num_size)
            page.insert_text(
                fitz.Point(back_center_x - (num_len / 2.0), num_y),
                p_num,
                fontname="helv",
                fontsize=num_size,
                color=(1, 1, 1)  # أبيض
            )

            # شريط التتبع الصناعي في هامش الخياطة
            tag = f"SportWay | M | Player: {player.get('name', '')} #{p_num} | Short: {player.get('shortSize', 'M')}"
            page.insert_text(
                fitz.Point(20, page_rect.height - 20),
                tag,
                fontname="helv",
                fontsize=9,
                color=(0.1, 0.1, 0.1)
            )

            merged_doc.insert_pdf(doc)
            doc.close()

        merged_doc.save(output_pdf_path)
        merged_doc.close()

        return jsonify({'success': True, 'count': len(m_players)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-test-file', methods=['GET'])
def download_test_file():
    target = os.path.join(OUTPUT_DIR, "FACTORY_TEST_M_ROLL.pdf")
    if os.path.exists(target):
        return send_file(target, as_attachment=True)
    return "الملف غير جاهز بعد", 404

if __name__ == '__main__':
    print("🚀 تم تشغيل السيرفر مع خاصية دمج التصميم الكامل والألوان...")
    app.run(port=5000, debug=False)