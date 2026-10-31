import os
import fitz  # PyMuPDF

class FlexibleTextRenderer:
    def __init__(self, template_pdf_path: str):
        """تهيئة محرك الكتابة عبر قراءة الباترون الأصلي"""
        self.template_path = template_pdf_path

    def draw_box_text(self, page, text: str, rect: fitz.Rect, fontname="helv", max_fontsize=50, color=(0, 0, 0)):
        """
        كتابة نص متوسّط مع خاصية الاحتواء التلقائي (Auto-fit)
        بحيث يصغر الخط تلقائياً إذا كان النص طويلاً ليبقى داخل حدود المستطيل تماماً
        """
        text = str(text).strip()
        fontsize = max_fontsize

        # حلقة لتقليص حجم الخط تلقائياً ليناسب المربع
        while fontsize > 8:
            text_len = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
            text_height = fontsize * 0.85
            if text_len <= rect.width and text_height <= rect.height:
                break
            fontsize -= 1

        # توسيط النص أفقياً وعمودياً داخل أبعاد المربع
        text_len = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
        start_x = rect.x0 + (rect.width - text_len) / 2.0
        start_y = rect.y0 + (rect.height + (fontsize * 0.75)) / 2.0

        # رسم النص كمتجه نقي عالي الدقة (Vector)
        page.insert_text(
            fitz.Point(start_x, start_y),
            text,
            fontsize=fontsize,
            fontname=fontname,
            color=color
        )

    def render_boxes(self, text_boxes: list, output_path: str):
        """
        تطبيق قائمة مربعات النص (قابلة للإضافة والتعديل بدون حدود) وحفظ ملف PDF جاهز للطباعة
        """
        doc = fitz.open(self.template_path)
        page = doc[0]

        for box_item in text_boxes:
            # قراءة الإحداثيات المحددة لكل صندوق
            rect = fitz.Rect(
                box_item["x"],
                box_item["y"],
                box_item["x"] + box_item["width"],
                box_item["y"] + box_item["height"]
            )
            self.draw_box_text(
                page=page,
                text=box_item.get("text", ""),
                rect=rect,
                fontname=box_item.get("font", "helv"),
                max_fontsize=box_item.get("max_size", 40),
                color=box_item.get("color", (0, 0, 0))
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        doc.close()
        print(f"✅ تم بنجاح إنشاء الملف مع كافة مربعات النص: {output_path}")


if __name__ == "__main__":
    template = "templates/M.pdf"
    output_test = "output/M_test_player.pdf"

    # قائمة مربعات النص - مرنة تماماً وقابلة لإضافة أي مربع ترغبين به
    boxes = [
        # مربع 1: الاسم (مضبوط في منتصف الظهر العلوي)
        {"type": "name", "text": "AL-MOHAMMAD", "x": 180, "y": 280, "width": 200, "height": 50, "max_size": 36, "color": (0, 0, 0)},

        # مربع 2: الرقم (مضبوط في المنتصف تحت الاسم بحجم كبير)
        {"type": "number", "text": "10", "x": 180, "y": 360, "width": 200, "height": 180, "max_size": 130, "color": (0, 0, 0)},

        # مربع 3 (تجريبي إضافي): لإثبات إمكانية إضافة أي نص بمرونة (مثل اسم الراعي أو الفريق)
        # {"type": "sponsor", "text": "SPORTWAY", "x": 200, "y": 570, "width": 160, "height": 40, "max_size": 22, "color": (0.2, 0.2, 0.2)}
    ]

    try:
        renderer = FlexibleTextRenderer(template)
        renderer.render_boxes(boxes, output_test)
    except Exception as e:
        print(f"حدث خطأ: {e}")