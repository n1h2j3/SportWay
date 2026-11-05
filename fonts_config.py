# -*- coding: utf-8 -*-
"""قائمة الخطوط المعتمدة (يستخدمها السيرفر وسكربت التحميل). لإضافة خط جديد أضيفوه هنا + في editor.html"""
import os

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# الاسم في المحرر: (اسم Google Fonts, الوزن, اسم الملف المحفوظ, يدعم العربي؟)
FONT_SPECS = {
    "Cairo":            ("Cairo", 700, "Cairo-Bold.ttf", True),
    "Almarai":          ("Almarai", 700, "Almarai-Bold.ttf", True),
    "Tajawal":          ("Tajawal", 700, "Tajawal-Bold.ttf", True),
    "Changa":           ("Changa", 700, "Changa-Bold.ttf", True),
    "Readex Pro":       ("Readex Pro", 700, "ReadexPro-Bold.ttf", True),
    "Teko":             ("Teko", 700, "Teko-Bold.ttf", False),
    "Bebas Neue":       ("Bebas Neue", 400, "BebasNeue-Regular.ttf", False),
    "Anton":            ("Anton", 400, "Anton-Regular.ttf", False),
    "Montserrat":       ("Montserrat", 800, "Montserrat-ExtraBold.ttf", False),
    "Russo One":        ("Russo One", 400, "RussoOne-Regular.ttf", False),
    "Barlow Condensed": ("Barlow Condensed", 700, "BarlowCondensed-Bold.ttf", False),
}
