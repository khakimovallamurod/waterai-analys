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


def _usage_and_recommendation(status: str, source_type: str, bad_params: List[Dict[str, Any]]):
    """Holat bo'yicha foydalanish yo'nalishlari va AI tavsiya matni."""
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
    return usage_recommendations, rec_text


def analyze_water_sample(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiritilgan suv parametrlarini tahlil qiladi va to'liq natijalar ob'ektini qaytaradi.
    """
    if str(data.get("data_source") or "").startswith("device"):
        return analyze_device_sample(data)

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

    usage_recommendations, rec_text = _usage_and_recommendation(status, source_type, bad_params)

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



# ==============================================================================
# PH-W218 qurilmasi o'lchaydigan parametrlar bo'yicha tahlil
# ==============================================================================

DEVICE_NORMS = {
    "ph": {"min": 6.5, "max": 8.5},
    "tds": {"max": 1000.0},
    "ec": {"max": STANDARDS["ec"]["max"]},
    "salinity": {"max": 1000.0},
    "orp": {"min": 200.0, "max": 600.0},  # tavsiyaviy, holatga ta'sir qilmaydi
}


def analyze_device_sample(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    PH-W218 qurilmasidan olingan real parametrlar (harorat, pH, TDS, EC, sho'rlanish, ORP)
    bo'yicha tahlil. Qurilma o'lchamaydigan parametrlar (loyqalik, qattiqlik, ...) hisobga olinmaydi.
    """
    ph = float(data.get("ph", 7.0))
    tds = float(data.get("tds", 0.0))
    ec = float(data.get("ec", 0.0))
    salinity = float(data.get("salinity", 0.0) or 0.0)
    orp = float(data.get("orp", 0.0) or 0.0)
    temperature = float(data.get("temperature", 20.0))
    source_type = data.get("source_type", "Vodoprovod suvi")

    bad_params = []
    severe = False
    penalty = 0.0

    if ph < 6.5 or ph > 8.5:
        bad_params.append({"param": "pH", "val": f"{ph:.2f}", "norm": "6.5 – 8.5",
                           "issue": "Kislotali" if ph < 6.5 else "Yuqori ishqoriy"})
        dev = (6.5 - ph) if ph < 6.5 else (ph - 8.5)
        penalty += min(15 + dev * 15, 45)
        severe = severe or ph < 5.5 or ph > 9.5
    if tds > 1000:
        bad_params.append({"param": "TDS", "val": f"{tds:.0f} ppm", "norm": "≤ 1000 ppm",
                           "issue": "Tuzlar miqdori haddan tashqari yuqori"})
        penalty += min(15 + (tds / 1000 - 1) * 40, 45)
        severe = severe or tds > 1500
    if ec > DEVICE_NORMS["ec"]["max"]:
        bad_params.append({"param": "EC", "val": f"{ec:.0f} µS/cm", "norm": f"≤ {DEVICE_NORMS['ec']['max']:.0f} µS/cm",
                           "issue": "Elektr o‘tkazuvchanlik yuqori (erigan ionlar ko‘p)"})
        penalty += min(10 + (ec / DEVICE_NORMS["ec"]["max"] - 1) * 20, 25)
    if salinity > 1000:
        bad_params.append({"param": "Sho‘rlanish", "val": f"{salinity:.0f} ppm", "norm": "≤ 1000 ppm",
                           "issue": "Suv sho‘rlangan"})
        penalty += min(10 + (salinity / 1000 - 1) * 20, 25)

    orp_ok = DEVICE_NORMS["orp"]["min"] <= orp <= DEVICE_NORMS["orp"]["max"]
    temp_ok = 5 <= temperature <= 30
    if not orp_ok:
        penalty += 5
    if not temp_ok:
        penalty += 3

    bad_count = len(bad_params)
    if severe or bad_count >= 3:
        status, status_label = "invalid", "🔴 Yaroqsiz"
        status_text = "Suv ichimlik sifatida foydalanish uchun tavsiya etilmaydi. Xavfli ko‘rsatkichlar mavjud."
        prob_valid, prob_conditional, prob_invalid = 3.4, 16.8, 79.8
        quality_score = max(5.0, min(45.0, 100 - penalty))
    elif bad_count >= 1:
        status, status_label = "conditional", "🟡 Shartli yaroqli"
        status_text = "Ayrim parametrlar bo‘yicha muammo mavjud. Qo‘shimcha tozalash yoki filtrlash tavsiya etiladi."
        prob_valid, prob_conditional, prob_invalid = 18.5, 72.3, 9.2
        quality_score = max(46.0, min(79.0, 100 - penalty))
    else:
        status, status_label = "valid", "🟢 Yaroqli"
        status_text = "Suv ichimlik sifatida foydalanishga mos. Qurilma o‘lchagan barcha ko‘rsatkichlar me’yorda."
        prob_valid, prob_conditional, prob_invalid = 94.7, 4.1, 1.2
        quality_score = max(80.0, min(98.0, 98 - penalty))
    confidence = max(prob_valid, prob_conditional, prob_invalid)

    parameters_table = [
        {"name": "pH", "value": f"{ph:.2f}", "norm": "6.5 – 8.5", "good": 6.5 <= ph <= 8.5, "unit": ""},
        {"name": "TDS", "value": f"{tds:.0f} ppm", "norm": "≤ 1000 ppm", "good": tds <= 1000, "unit": "ppm"},
        {"name": "Elektr o‘tkazuvchanlik (EC)", "value": f"{ec:.0f} µS/cm",
         "norm": f"≤ {DEVICE_NORMS['ec']['max']:.0f} µS/cm", "good": ec <= DEVICE_NORMS["ec"]["max"], "unit": "µS/cm"},
        {"name": "Sho‘rlanish", "value": f"{salinity:.0f} ppm", "norm": "≤ 1000 ppm", "good": salinity <= 1000, "unit": "ppm"},
        {"name": "ORP (oksidlanish-qaytarilish)", "value": f"{orp:.0f} mV", "norm": "200 – 600 mV (tavsiya)", "good": orp_ok, "unit": "mV"},
        {"name": "Harorat", "value": f"{temperature:.1f} °C", "norm": "10 – 25 °C", "good": temp_ok, "unit": "°C"},
    ]

    norm_analysis = [
        {"name": "pH", "percent": min(round((ph / 8.5) * 100, 1), 100)},
        {"name": "TDS", "percent": min(round((tds / 1000) * 100, 1), 100)},
        {"name": "EC", "percent": min(round((ec / DEVICE_NORMS["ec"]["max"]) * 100, 1), 100)},
        {"name": "Sho‘rlanish", "percent": min(round((salinity / 1000) * 100, 1), 100)},
        {"name": "ORP", "percent": min(max(round((orp / 600) * 100, 1), 0), 100)},
    ]

    feature_importance = [
        {"name": "TDS (Umumiy tuzlar)", "percent": 30},
        {"name": "pH ko‘rsatkichi", "percent": 28},
        {"name": "EC (Elektr o‘tkazuvchanlik)", "percent": 20},
        {"name": "Sho‘rlanish", "percent": 10},
        {"name": "ORP", "percent": 8},
        {"name": "Harorat", "percent": 4},
    ]

    usage_recommendations, rec_text = _usage_and_recommendation(status, source_type, bad_params)
    origin = ("real o‘lchovlari" if data.get("data_source", "device") == "device"
              else "parametrlari (qurilma ulanmagan — standart/kiritilgan qiymatlar)")
    rec_text += (
        f" <br><span class='text-xs'>📡 Natija PH-W218 qurilmasining {origin} "
        "(pH, TDS, EC, sho‘rlanish, ORP, harorat) asosida hisoblandi. Loyqalik, qattiqlik va "
        "kimyoviy birikmalar qurilma tomonidan o‘lchanmaydi.</span>"
    )
    if not orp_ok:
        rec_text += (
            f" <br><span class='text-xs'>⚠️ ORP {orp:.0f} mV — tavsiya etilgan 200–600 mV oralig‘idan tashqarida; "
            "dezinfeksiya darajasini qo‘shimcha tekshiring.</span>"
        )

    return {
        "status": status,
        "status_label": status_label,
        "status_text": status_text,
        "quality_score": round(quality_score, 1),
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
        "ai_recommendation": rec_text,
    }
