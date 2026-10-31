import fitz  # PyMuPDF

# ثوابت التحويل الفيزيائي للطباعة الصناعية (1 cm = 28.3465 pt)
CM_TO_PT = 28.3465
MM_TO_PT = 2.83465

class PatternCalibrator:
    def __init__(self, pdf_path: str):
        """فتح ملف الباترون واستخراج أبعاد الصفحة الإجمالية"""
        self.doc = fitz.open(pdf_path)
        self.page = self.doc[0]
        self.rect = self.page.rect  # حدود وأبعاد الصفحة الإجمالية

    def get_back_jersey_anchor(self, safety_drop_cm=14.0, name_w_cm=26.0, name_h_cm=6.0, num_h_cm=20.0):
        """
        حساب إحداثيات ومستطيل الاسم والرقم بناءً على أبعاد التيشيرت الحقيقية
        - safety_drop_cm تم ضبطها على 14 سم لتبدأ الكتابة أسفل ياقة الرقبة مباشرة في منتصف الظهر
        """
        # منتصف التيشيرت الفعلي أفقياً (39.8 سم / 2 = 19.9 سم)
        jersey_actual_width_cm = 39.8
        center_x = (jersey_actual_width_cm / 2.0) * CM_TO_PT

        # نقطة البداية عمودياً (هبوط 14 سم من أعلى الكتف لتستقر تحت الرقبة)
        top_y = safety_drop_cm * CM_TO_PT

        name_w_pt = name_w_cm * CM_TO_PT
        name_h_pt = name_h_cm * CM_TO_PT
        num_h_pt = num_h_cm * CM_TO_PT

        # 1. مستطيل الاسم (متوسط في منتصف الظهر)
        name_box = fitz.Rect(
            center_x - (name_w_pt / 2.0),
            top_y,
            center_x + (name_w_pt / 2.0),
            top_y + name_h_pt
        )

        # 2. مستطيل الرقم أسفل الاسم بفارق 2.5 سم
        gap_pt = 2.5 * CM_TO_PT
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
    print("Pattern calibrator initialized successfully.")