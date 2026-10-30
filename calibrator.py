import fitz  # PyMuPDF

# ثوابت التحويل الفيزيائي للطباعة الصناعية (1 cm = 28.3465 pt)
CM_TO_PT = 28.3465
MM_TO_PT = 2.83465

class PatternCalibrator:
    def __init__(self, pdf_path: str):
        """فتح ملف الباترون واستخراج أبعاد الصفحة الإجمالية"""
        self.doc = fitz.open(pdf_path)
        self.page = self.doc[0]
        self.rect = self.page.rect  # حدود وأبعاد الصفحة (pt)

    def get_back_jersey_anchor(self, safety_drop_cm=6.0, name_w_cm=28.0, name_h_cm=7.0, num_h_cm=22.0):
        """
        حساب إحداثيات ومستطيل الاسم والرقم على ظهر التيشيرت:
        - التوسيط الأفقي التلقائي (Center-X)
        - مسافة الهبوط الآمنة من أسفل العراقة/الرقبة
        """
        center_x = self.rect.width / 2.0

        drop_pt = safety_drop_cm * CM_TO_PT
        name_w_pt = name_w_cm * CM_TO_PT
        name_h_pt = name_h_cm * CM_TO_PT
        num_h_pt = num_h_cm * CM_TO_PT

        # مستطيل الاسم
        name_box = fitz.Rect(
            center_x - (name_w_pt / 2.0),
            drop_pt,
            center_x + (name_w_pt / 2.0),
            drop_pt + name_h_pt
        )

        # مستطيل الرقم أسفل الاسم بفارق 3 سم
        # مستطيل الرقم أسفل الاسم بفارق 3 سم
        gap_pt = 3.0 * CM_TO_PT
        num_top = name_box.y1 + gap_pt
        num_box = fitz.Rect(
            center_x - (name_w_pt / 2.0),
            num_top,
            center_x + (name_w_pt / 2.0),
            num_top + num_h_pt
        )

        return {
            "name_box": name_box,
            "number_box": num_box
        }

    def get_short_anchor(self, offset_x_cm=6.0, offset_y_cm=7.0, box_size_cm=8.0):
        """
        حساب إحداثيات رقم وشعار الشورت من الزاوية السفلية (6 سم أفقياً و 7 سم عمودياً)
        """
        x_pt = offset_x_cm * CM_TO_PT
        y_pt = offset_y_cm * CM_TO_PT
        box_size_pt = box_size_cm * CM_TO_PT

        target_box = fitz.Rect(
            self.rect.x0 + x_pt,
            self.rect.y1 - y_pt - box_size_pt,
            self.rect.x0 + x_pt + box_size_pt,
            self.rect.y1 - y_pt
        )
        return {
            "short_badge_box": target_box
        }

if __name__ == "__main__":
    # مسار باترون التيشيرت مقاس M الفعلي
    template_file = "templates/M.pdf"

    try:
        calibrator = PatternCalibrator(template_file)

        # تحويل أبعاد الصفحة من نقاط (pt) إلى سنتيمتر (cm)
        width_cm = calibrator.rect.width / CM_TO_PT
        height_cm = calibrator.rect.height / CM_TO_PT

        print("========================================")
        print(f" تم فتح ملف الباترون بنجاح: {template_file}")
        print(f"- العرض الإجمالي: {width_cm:.2f} سم")
        print(f"- الارتفاع الإجمالي: {height_cm:.2f} سم")
        print("========================================")

        # استخراج مستطيلات ومواقع الطباعة لظهر التيشيرت
        anchors = calibrator.get_back_jersey_anchor(safety_drop_cm=6.0)
        name_rect = anchors["name_box"]
        num_rect = anchors["number_box"]

        print("\n--- إحداثيات الطباعة الفيزيائية (بالسنتيمتر) ---")
        print(f"مستطيل الاسم: عرض {name_rect.width / CM_TO_PT:.1f} سم × ارتفاع {name_rect.height / CM_TO_PT:.1f} سم")
        print(f"مكان الاسم (أفقي: {name_rect.x0 / CM_TO_PT:.1f} سم، عمودي: {name_rect.y0 / CM_TO_PT:.1f} سم)")
        print(f"مستطيل الرقم: عرض {num_rect.width / CM_TO_PT:.1f} سم × ارتفاع {num_rect.height / CM_TO_PT:.1f} سم")
        print(f"مكان الرقم (أفقي: {num_rect.x0 / CM_TO_PT:.1f} سم، عمودي: {num_rect.y0 / CM_TO_PT:.1f} سم)")
        print("========================================")

    except Exception as error:
        print(f"خطأ أثناء قراءة الملف: {error}")