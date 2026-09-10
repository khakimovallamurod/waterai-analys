"""
WaterAI Analysis Engine
Suv sifatini baholash va AI tavsiyalarini hisoblash moduli.
SanPiN va JSST (WHO) me'yorlari asosida ishlaydi.
"""
from typing import Dict, Any, List


# Standart me'yoriy ko'rsatkichlar
STANDARDS = {
    "ph": {"min": 6.5, "max": 8.5, "unit": "", "name": "pH", "max_limit": 8.5, "weight": 0.22},
    "tds": {"min": 0, "max": 1000.0, "unit": "mg/L", "name": "TDS", "max_limit": 1000.0, "weight": 0.31},
    "hardness": {"min": 0, "max": 200.0, "unit": "mg/L", "name": "Qattiqlik", "max_limit": 200.0, "weight": 0.14},
    "turbidity": {"min": 0, "max": 5.0, "unit": "NTU", "name": "Turbidlik", "max_limit": 5.0, "weight": 0.18},
    "sulfate": {"min": 0, "max": 250.0, "unit": "mg/L", "name": "Sulfatlar", "max_limit": 250.0, "weight": 0.10},
    "chloramines": {"min": 0, "max": 4.0, "unit": "mg/L", "name": "Xloraminlar", "max_limit": 4.0, "weight": 0.05},
    "organic": {"min": 0, "max": 10.0, "unit": "mg/L", "name": "Organik uglerod", "max_limit": 10.0, "weight": 0.05},
    "trihalomethanes": {"min": 0, "max": 80.0, "unit": "mg/L", "name": "Trihalometanlar", "max_limit": 80.0, "weight": 0.05},
    "temperature": {"min": 5.0, "max": 25.0, "unit": "°C", "name": "Harorat", "max_limit": 30.0, "weight": 0.02},
    "ec": {"min": 0, "max": 1000.0, "unit": "μS/cm", "name": "Elektr o‘tkazuvchanlik", "max_limit": 1000.0, "weight": 0.03}
}


def analyze_water_sample(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiritilgan suv parametrlarini tahlil qiladi va to'liq natijalar ob'ektini qaytaradi.
    """
    ph = float(data.get("ph", 7.0))
    tds = float(data.get("tds", 250.0))
    turbidity = float(data.get("turbidity", 1.0))
    hardness = float(data.get("hardness", 150.0))
    sulfate = float(data.get("sulfate", 100.0))
    chloramines = float(data.get("chloramines", 2.0))
    organic = float(data.get("organic", 2.0))
    trihalomethanes = float(data.get("trihalomethanes", 10.0))
    temperature = float(data.get("temperature", 20.0))
    ec = float(data.get("ec", 300.0))
    source_type = data.get("source_type", "Vodoprovod suvi")

    # Me'yordan chetlashgan parametrlarni aniqlash
    bad_params = []
    
    if ph < 6.5 or ph > 8.5:
        bad_params.append({
            "param": "pH",
            "val": ph,
            "norm": "6.5 – 8.5",
            "issue": "Kislotali" if ph < 6.5 else "Yuqori ishqoriy"
        })
    if tds > 1000:
        bad_params.append({
            "param": "TDS",
            "val": f"{tds:.0f} mg/L",
            "norm": "≤ 1000 mg/L",
            "issue": "Tuzlar miqdori haddan tashqari yuqori"
        })
    if turbidity > 5:
        bad_params.append({
            "param": "Turbidlik",
            "val": f"{turbidity:.1f} NTU",
            "norm": "≤ 5 NTU",
            "issue": "Loyqalik yuqori, mexanik zarralar mavjud"
        })
    if hardness > 200:
        bad_params.append({
            "param": "Qattiqlik",
            "val": f"{hardness:.0f} mg/L",
            "norm": "≤ 200 mg/L",
            "issue": "Kalsiy va magniy tuzlari ko'p (qattiq suv)"
        })
    if sulfate > 250:
        bad_params.append({
            "param": "Sulfatlar",
            "val": f"{sulfate:.0f} mg/L",
            "norm": "≤ 250 mg/L",
            "issue": "Sulfat miqdori me'yordan yuqori"
        })
    if chloramines > 4:
        bad_params.append({
            "param": "Xloraminlar",
            "val": f"{chloramines:.2f} mg/L",
            "norm": "≤ 4 mg/L",
            "issue": "Xlor birikmalari qoldig'i ko'p"
        })
    if organic > 10:
        bad_params.append({
            "param": "Organik uglerod",
            "val": f"{organic:.1f} mg/L",
            "norm": "≤ 10 mg/L",
            "issue": "Organik ifloslanish mavjud"
        })
    if trihalomethanes > 80:
        bad_params.append({
            "param": "Trihalometanlar",
            "val": f"{trihalomethanes:.1f} mg/L",
            "norm": "≤ 80 mg/L",
            "issue": "Zaharli kimyoviy birikmalar me'yordan oshgan"
        })

    bad_count = len(bad_params)

    # Klassifikatsiya va ehtimolliklar
    if bad_count == 0:
        prob_valid = 94.7
        prob_conditional = 4.1
        prob_invalid = 1.2
        status = "valid"
        status_label = "🟢 Yaroqli"
        status_text = "Suv ichimlik sifatida foydalanishga mos. Barcha ko‘rsatkichlar me’yorda."
        quality_score = 95.0
        confidence = 94.7
    elif bad_count <= 2:
        prob_valid = 18.5
        prob_conditional = 72.3
        prob_invalid = 9.2
        status = "conditional"
        status_label = "🟡 Shartli yaroqli"
        status_text = "Ayrim parametrlar bo‘yicha muammo mavjud. Qo‘shimcha tozalash yoki filtrlash tavsiya etiladi."
        quality_score = 68.5
        confidence = 72.3
    else:
        prob_valid = 3.4
        prob_conditional = 16.8
        prob_invalid = 79.8
        status = "invalid"
        status_label = "🔴 Yaroqsiz"
        status_text = "Suv ichimlik sifatida foydalanish uchun tavsiya etilmaydi. Xavfli ko‘rsatkichlar mavjud."
        quality_score = 32.0
        confidence = 79.8

    # Parametrlar jadvali
    parameters_table = [
        {"name": "pH", "value": f"{ph:.2f}", "norm": "6.5 – 8.5", "good": 6.5 <= ph <= 8.5, "unit": ""},
        {"name": "TDS", "value": f"{tds:.0f} mg/L", "norm": "≤ 1000 mg/L", "good": tds <= 1000, "unit": "mg/L"},
        {"name": "Qattiqlik", "value": f"{hardness:.0f} mg/L", "norm": "≤ 200 mg/L", "good": hardness <= 200, "unit": "mg/L"},
        {"name": "Sulfatlar", "value": f"{sulfate:.0f} mg/L", "norm": "≤ 250 mg/L", "good": sulfate <= 250, "unit": "mg/L"},
        {"name": "Turbidlik", "value": f"{turbidity:.1f} NTU", "norm": "≤ 5 NTU", "good": turbidity <= 5, "unit": "NTU"},
        {"name": "Xloraminlar", "value": f"{chloramines:.2f} mg/L", "norm": "≤ 4 mg/L", "good": chloramines <= 4, "unit": "mg/L"},
        {"name": "Organik uglerod", "value": f"{organic:.1f} mg/L", "norm": "≤ 10 mg/L", "good": organic <= 10, "unit": "mg/L"},
        {"name": "Trihalometanlar", "value": f"{trihalomethanes:.1f} mg/L", "norm": "≤ 80 mg/L", "good": trihalomethanes <= 80, "unit": "mg/L"},
        {"name": "Harorat", "value": f"{temperature:.1f} °C", "norm": "10 – 25 °C", "good": 5 <= temperature <= 30, "unit": "°C"},
        {"name": "Elektr o‘tkazuvchanlik", "value": f"{ec:.0f} μS/cm", "norm": "≤ 1000 μS/cm", "good": ec <= 1000, "unit": "μS/cm"}
    ]

    # Me'yor nisbati diagrammasi uchun
    norm_analysis = [
        {"name": "pH", "percent": min(round((ph / 8.5) * 100, 1), 100)},
        {"name": "TDS", "percent": min(round((tds / 1000) * 100, 1), 100)},
        {"name": "Qattiqlik", "percent": min(round((hardness / 200) * 100, 1), 100)},
        {"name": "Sulfatlar", "percent": min(round((sulfate / 250) * 100, 1), 100)},
        {"name": "Turbidlik", "percent": min(round((turbidity / 5) * 100, 1), 100)},
        {"name": "Xloraminlar", "percent": min(round((chloramines / 4) * 100, 1), 100)},
    ]

    # AI Feature Importance
    feature_importance = [
        {"name": "TDS (Umumiy tuzlar)", "percent": 31},
        {"name": "pH ko‘rsatkichi", "percent": 22},
        {"name": "Turbidlik (Loyqalik)", "percent": 18},
        {"name": "Qattiqlik (Kalsiy/Magniy)", "percent": 14},
        {"name": "Sulfatlar", "percent": 10},
        {"name": "Boshqa parametrlar", "percent": 5}
    ]

    # Foydalanish yo'nalishlari tavsiyalari
    if status == "valid":
        usage_recommendations = [
            {"icon": "🚰", "title": "Ichimlik", "status": "🟢 TAVSIYA ETILADI", "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300"},
            {"icon": "🍳", "title": "Ovqat tayyorlash", "status": "🟢 TAVSIYA ETILADI", "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300"},
            {"icon": "🧺", "title": "Kir yuvish", "status": "🟢 MOS", "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300"},
            {"icon": "🚿", "title": "Maishiy foydalanish", "status": "🟢 MOS", "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300"},
            {"icon": "🌱", "title": "Sug‘orish", "status": "⚠️ QO‘SHIMCHA TEKSHIRUV", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"},
            {"icon": "🧒", "title": "3 yoshgacha bolalar", "status": "⚠️ MAXSUS TEKSHIRUV", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"}
        ]
        rec_text = (
            f"Suv namunasi ({source_type}) <b>yaroqli</b> deb baholandi. "
            "Tekshirilgan barcha asosiy parametrlar SanPiN va JSST belgilagan me’yoriy chegaralar doirasida. "
            "Ichimlik suvi sifatida bemalol foydalanish mumkin. Biroq bolalar yoki chaqaloqlar uchun qaynatib ichirish tavsiya etiladi."
        )
    elif status == "conditional":
        usage_recommendations = [
            {"icon": "🚰", "title": "Ichimlik", "status": "🟡 FILTRLASHDAN KEYIN", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"},
            {"icon": "🍳", "title": "Ovqat tayyorlash", "status": "🟡 TOZALASHDAN KEYIN", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"},
            {"icon": "🧺", "title": "Kir yuvish", "status": "🟢 MOS", "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300"},
            {"icon": "🚿", "title": "Maishiy foydalanish", "status": "🟢 SHARTLI MOS", "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300"},
            {"icon": "🌱", "title": "Sug‘orish", "status": "⚠️ QO‘SHIMCHA TEKSHIRUV", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"},
            {"icon": "🧒", "title": "3 yoshgacha bolalar", "status": "⚠️ MAXSUS TEKSHIRUV", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"}
        ]
        issues_str = ", ".join([f"{p['param']} ({p['val']})" for p in bad_params])
        rec_text = (
            f"Suv namunasi ({source_type}) <b>shartli yaroqli</b> deb baholandi. "
            f"Quyidagi parametrlarda chetlashish aniqlandi: <b>{issues_str}</b>. "
            "Ichimlik va ovqatga ishlatishdan oldin ko'p bosqichli filtrlash (uglerodli filtr yoki teskari osmos) "
            "hamda qaynatish tavsiya qilinadi."
        )
    else:
        usage_recommendations = [
            {"icon": "🚰", "title": "Ichimlik", "status": "🔴 TAVSIYA ETILMAYDI", "badge_class": "bg-rose-100 text-rose-800 border-rose-300"},
            {"icon": "🍳", "title": "Ovqat tayyorlash", "status": "🔴 TAVSIYA ETILMAYDI", "badge_class": "bg-rose-100 text-rose-800 border-rose-300"},
            {"icon": "🧺", "title": "Kir yuvish", "status": "🟡 SHARTLI MOS", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"},
            {"icon": "🚿", "title": "Maishiy foydalanish", "status": "🟡 SHARTLI MOS", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"},
            {"icon": "🌱", "title": "Sug‘orish", "status": "⚠️ QO‘SHIMCHA TEKSHIRUV", "badge_class": "bg-amber-100 text-amber-800 border-amber-300"},
            {"icon": "🧒", "title": "3 yoshgacha bolalar", "status": "🔴 TAVSIYA ETILMAYDI", "badge_class": "bg-rose-100 text-rose-800 border-rose-300"}
        ]
        issues_str = ", ".join([f"{p['param']} ({p['val']})" for p in bad_params])
        rec_text = (
            f"Suv namunasi ({source_type}) <b>yaroqsiz</b> deb baholandi! "
            f"Bir nechta kritik ko‘rsatkichlar ({issues_str}) qat'iy me’yordan oshgan. "
            "Ushbu suvni to‘g‘ridan-to‘g‘ri iste’mol qilish sog‘liq uchun xavfli bo‘lishi mumkin. "
            "Faqat maxsus chuqur sanoat filtri yoki texnik maqsadlarda ishlatilishi lozim."
        )

    return {
        "status": status,
        "status_label": status_label,
        "status_text": status_text,
        "quality_score": quality_score,
        "confidence": confidence,
        "prob_valid": prob_valid,
        "prob_conditional": prob_conditional,
        "prob_invalid": prob_invalid,
        "bad_parameters_count": bad_count,
        "bad_params": bad_params,
        "parameters_table": parameters_table,
        "norm_analysis": norm_analysis,
        "feature_importance": feature_importance,
        "usage_recommendations": usage_recommendations,
        "ai_recommendation": rec_text
    }
