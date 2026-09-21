"""
WaterAI Analysis — Asosiy Ilova
FastAPI, Jinja2, SQLAlchemy va AI Engine integratsiyasi.
"""
import os
import csv
import io
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import ai_engine
import auth
from database import engine, Base, get_db
from models import User, WaterAnalysis, ParameterNorm


# ==============================================================================
# Boshlang'ich Ma'lumotlarni Yuklash (Database Seeding)
# ==============================================================================

def seed_initial_data(db: Session):
    """
    Standart me'yorlar va ixtiyoriy dastlabki sozlamalarni yuklash.
    DIQQAT: Xavfsizlik qoidalariga muvofiq, login va parollar dastur kodida (source code)
    saqlanmaydi! Foydalanuvchilar SQLite bazasida saqlanadi.
    Agar zarur bo'lsa, bir martalik boshqaruvchi faqat .env yoki environment orqali kiritiladi.
    """
    # 2. Ixtiyoriy: Agar muhit o'zgaruvchilari (ENV) orqali admin ko'rsatilgan bo'lsa va u hali yo'q bo'lsa
    env_admin_phone = os.getenv("ADMIN_PHONE")
    env_admin_pass = os.getenv("ADMIN_PASSWORD")
    if env_admin_phone and env_admin_pass:
        norm_phone = auth.normalize_phone(env_admin_phone)
        admin_exists = db.query(User).filter(User.phone == norm_phone).first()
        if not admin_exists:
            new_admin = User(
                phone=norm_phone,
                full_name=os.getenv("ADMIN_NAME", "Bosh Administrator"),
                hashed_password=auth.hash_password(env_admin_pass),
                role="admin",
                is_active=True
            )
            db.add(new_admin)
            db.commit()

    # 2. Standart parametrlarni kiritish
    if db.query(ParameterNorm).count() == 0:
        for code, info in ai_engine.STANDARDS.items():
            norm_entry = ParameterNorm(
                code=code,
                name=info["name"],
                unit=info["unit"],
                norm_text=f"≤ {info['max']} {info['unit']}".strip() if info['min'] == 0 else f"{info['min']} - {info['max']} {info['unit']}".strip(),
                min_val=info.get("min"),
                max_val=info.get("max"),
                importance_pct=info.get("weight", 0.1) * 100,
                description=f"SanPiN 0211-06 standarti bo'yicha {info['name']}"
            )
            db.add(norm_entry)
        db.commit()

    # 3. Namunaviy tahlillarni yaratish
    if db.query(WaterAnalysis).count() == 0:
        samples = [
            {
                "sample_name": "Toshkent shahri vodoprovod suvi",
                "source_type": "Vodoprovod suvi",
                "location": "Toshkent, Yunusobod tumani",
                "data": {
                    "ph": 7.20, "tds": 240, "turbidity": 1.1, "ec": 310,
                    "hardness": 150, "sulfate": 95, "chloramines": 1.80,
                    "organic": 1.8, "trihalomethanes": 12.0, "temperature": 19.5,
                    "source_type": "Vodoprovod suvi"
                }
            },
            {
                "sample_name": "Chorvoq tog' buloq suvi",
                "source_type": "Artezian suvi",
                "location": "Toshkent viloyati, Bo'stonliq",
                "data": {
                    "ph": 7.55, "tds": 110, "turbidity": 0.4, "ec": 140,
                    "hardness": 80, "sulfate": 30, "chloramines": 0.10,
                    "organic": 0.5, "trihalomethanes": 1.5, "temperature": 12.0,
                    "source_type": "Artezian suvi"
                }
            },
            {
                "sample_name": "Farg'ona vodiysi yerosti quduq suvi",
                "source_type": "Quduq suvi",
                "location": "Farg'ona, Quva tumani",
                "data": {
                    "ph": 7.85, "tds": 780, "turbidity": 3.2, "ec": 890,
                    "hardness": 260, "sulfate": 210, "chloramines": 0.20,
                    "organic": 3.5, "trihalomethanes": 8.5, "temperature": 16.5,
                    "source_type": "Quduq suvi"
                }
            },
            {
                "sample_name": "Zarafshon daryosi namunalari",
                "source_type": "Daryo suvi",
                "location": "Samarqand viloyati",
                "data": {
                    "ph": 8.20, "tds": 850, "turbidity": 7.5, "ec": 920,
                    "hardness": 240, "sulfate": 280, "chloramines": 0.40,
                    "organic": 6.2, "trihalomethanes": 25.0, "temperature": 22.0,
                    "source_type": "Daryo suvi"
                }
            }
        ]

        creator = db.query(User).filter(User.role == "admin").first() or db.query(User).first()
        for s in samples:
            res = ai_engine.analyze_water_sample(s["data"])
            d = s["data"]
            analysis = WaterAnalysis(
                user_id=creator.id if creator else None,
                sample_name=s["sample_name"],
                source_type=s["source_type"],
                location=s["location"],
                temperature=d["temperature"],
                ph=d["ph"],
                tds=d["tds"],
                turbidity=d["turbidity"],
                ec=d["ec"],
                hardness=d["hardness"],
                sulfate=d["sulfate"],
                chloramines=d["chloramines"],
                organic=d["organic"],
                trihalomethanes=d["trihalomethanes"],
                extra_param="Tanlang",
                status=res["status"],
                status_label=res["status_label"],
                quality_score=res["quality_score"],
                confidence=res["confidence"],
                prob_valid=res["prob_valid"],
                prob_conditional=res["prob_conditional"],
                prob_invalid=res["prob_invalid"],
                bad_parameters_count=res["bad_parameters_count"],
                status_text=res["status_text"],
                ai_recommendation=res["ai_recommendation"]
            )
            db.add(analysis)
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dastur ishga tushganda jadvallarni yaratish va ma'lumotlarni kiritish
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        seed_initial_data(db)
    finally:
        db.close()
    yield


# ==============================================================================
# FastAPI Ilovasi va Konfiguratsiyasi
# ==============================================================================

app = FastAPI(
    title="WaterAI Analysis",
    description="Suv sifatini sun'iy intellekt va neyron tarmoqlar yordamida tahlil qilish platformasi",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ==============================================================================
# Helper Funksiyalar
# ==============================================================================

def get_base_context(
    request: Request,
    active_page: str = "",
    alert_message: Optional[str] = None,
    alert_type: str = "success",
    current_user: Optional[User] = None
) -> Dict[str, Any]:
    # Agar alert query parametrlar orqali berilgan bo'lsa
    if not alert_message and request.query_params.get("msg"):
        alert_message = request.query_params.get("msg")
        alert_type = request.query_params.get("type", "success")

    return {
        "request": request,
        "active_page": active_page,
        "alert_message": alert_message,
        "alert_type": alert_type,
        "current_user": current_user
    }


# ==============================================================================
# Foydalanuvchi Sahifalari (HTML Endpoints)
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Boshqaruv paneli (Dashboard)"""
    current_user = auth.get_current_user_optional(request, db)
    analyses = db.query(WaterAnalysis).order_by(WaterAnalysis.created_at.desc()).all()

    total_count = len(analyses)
    valid_count = sum(1 for a in analyses if a.status == "valid")
    conditional_count = sum(1 for a in analyses if a.status == "conditional")
    invalid_count = sum(1 for a in analyses if a.status == "invalid")

    ctx = get_base_context(request, active_page="home", current_user=current_user)
    ctx.update({
        "analyses": analyses,
        "total_count": total_count,
        "valid_count": valid_count,
        "conditional_count": conditional_count,
        "invalid_count": invalid_count
    })
    return templates.TemplateResponse(request=request, name="user/dashboard.html", context=ctx)


@app.get("/analyze", response_class=HTMLResponse)
def analyze_page(request: Request, db: Session = Depends(get_db)):
    """Suv parametrlarini kiritish sahifasi"""
    current_user = auth.get_current_user_optional(request, db)
    ctx = get_base_context(request, active_page="analyze", current_user=current_user)
    return templates.TemplateResponse(request=request, name="user/analyze.html", context=ctx)


@app.post("/analyze")
def handle_analyze(
    request: Request,
    sample_name: str = Form("Suv namunasi"),
    source_type: str = Form("Vodoprovod suvi"),
    location: Optional[str] = Form("Toshkent"),
    temperature: float = Form(20.0),
    ph: float = Form(7.0),
    tds: float = Form(250.0),
    turbidity: float = Form(1.0),
    ec: float = Form(300.0),
    hardness: float = Form(150.0),
    sulfate: float = Form(100.0),
    chloramines: float = Form(2.0),
    organic: float = Form(2.0),
    trihalomethanes: float = Form(10.0),
    extra_param: Optional[str] = Form("Tanlang"),
    db: Session = Depends(get_db)
):
    """Parametrlarni qabul qilib, AI orqali hisoblash va natijani saqlash"""
    current_user = auth.get_current_user_optional(request, db)

    input_data = {
        "ph": ph,
        "tds": tds,
        "turbidity": turbidity,
        "hardness": hardness,
        "sulfate": sulfate,
        "chloramines": chloramines,
        "organic": organic,
        "trihalomethanes": trihalomethanes,
        "temperature": temperature,
        "ec": ec,
        "source_type": source_type
    }

    results = ai_engine.analyze_water_sample(input_data)

    analysis = WaterAnalysis(
        user_id=current_user.id if current_user else None,
        sample_name=sample_name or "Suv namunasi",
        source_type=source_type or "Vodoprovod suvi",
        location=location or "O'zbekiston",
        temperature=temperature,
        ph=ph,
        tds=tds,
        turbidity=turbidity,
        ec=ec,
        hardness=hardness,
        sulfate=sulfate,
        chloramines=chloramines,
        organic=organic,
        trihalomethanes=trihalomethanes,
        extra_param=extra_param,
        status=results["status"],
        status_label=results["status_label"],
        quality_score=results["quality_score"],
        confidence=results["confidence"],
        prob_valid=results["prob_valid"],
        prob_conditional=results["prob_conditional"],
        prob_invalid=results["prob_invalid"],
        bad_parameters_count=results["bad_parameters_count"],
        status_text=results["status_text"],
        ai_recommendation=results["ai_recommendation"]
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return RedirectResponse(url=f"/result/{analysis.id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/result/{analysis_id}", response_class=HTMLResponse)
def view_result(request: Request, analysis_id: int, db: Session = Depends(get_db)):
    """Tahlil hisoboti sahifasi"""
    current_user = auth.get_current_user_optional(request, db)
    analysis = db.query(WaterAnalysis).filter(WaterAnalysis.id == analysis_id).first()
    if not analysis:
        return RedirectResponse(url="/history?msg=Tahlil+topilmadi&type=error", status_code=status.HTTP_303_SEE_OTHER)

    # Natija sahifasi uchun zarur bo'lgan grafik va taqqoslash jadvallarini hisoblash
    engine_details = ai_engine.analyze_water_sample({
        "ph": analysis.ph,
        "tds": analysis.tds,
        "turbidity": analysis.turbidity,
        "hardness": analysis.hardness,
        "sulfate": analysis.sulfate,
        "chloramines": analysis.chloramines,
        "organic": analysis.organic,
        "trihalomethanes": analysis.trihalomethanes,
        "temperature": analysis.temperature,
        "ec": analysis.ec,
        "source_type": analysis.source_type
    })

    ctx = get_base_context(request, active_page="analyze", current_user=current_user)
    ctx.update({
        "analysis": analysis,
        "usage_recommendations": engine_details["usage_recommendations"],
        "norm_analysis": engine_details["norm_analysis"],
        "feature_importance": engine_details["feature_importance"],
        "parameters_table": engine_details["parameters_table"]
    })
    return templates.TemplateResponse(request=request, name="user/result.html", context=ctx)


@app.get("/history", response_class=HTMLResponse)
def history_page(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    """Tahlillar tarixi sahifasi (filtrlash bilan)"""
    current_user = auth.get_current_user_optional(request, db)
    
    # Bazadagi barcha yozuvlar bo'yicha hisoblagichlar
    all_records = db.query(WaterAnalysis).all()
    total_count = len(all_records)
    valid_count = sum(1 for a in all_records if a.status == "valid")
    conditional_count = sum(1 for a in all_records if a.status == "conditional")
    invalid_count = sum(1 for a in all_records if a.status == "invalid")

    # Filtrlash
    query = db.query(WaterAnalysis).order_by(WaterAnalysis.created_at.desc())
    if status_filter in ["valid", "conditional", "invalid"]:
        query = query.filter(WaterAnalysis.status == status_filter)

    analyses = query.all()

    ctx = get_base_context(request, active_page="history", current_user=current_user)
    ctx.update({
        "analyses": analyses,
        "status_filter": status_filter,
        "total_count": total_count,
        "valid_count": valid_count,
        "conditional_count": conditional_count,
        "invalid_count": invalid_count
    })
    return templates.TemplateResponse(request=request, name="user/history.html", context=ctx)


@app.get("/export/csv/{analysis_id}")
def export_single_csv(analysis_id: int, db: Session = Depends(get_db)):
    """Bitta tahlil natijasini CSV formatida yuklab olish"""
    analysis = db.query(WaterAnalysis).filter(WaterAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Tahlil topilmadi")

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Parametr", "Qiymat", "Me'yor", "Holat"])
    writer.writerow(["ID", analysis.id, "", ""])
    writer.writerow(["Namuna nomi", analysis.sample_name, "", ""])
    writer.writerow(["Manba turi", analysis.source_type, "", ""])
    writer.writerow(["Hudud", analysis.location or "", "", ""])
    writer.writerow(["Sana", analysis.created_at.strftime("%d.%m.%Y %H:%M"), "", ""])
    writer.writerow(["WQI Indeksi", f"{analysis.quality_score:.1f}", "100", ""])
    writer.writerow(["Umumiy Baho", analysis.status_label, "", ""])
    writer.writerow([])
    writer.writerow(["Ko'rsatkichlar", "Kiritilgan", "SanPiN Me'yori", "Holat"])
    writer.writerow(["pH", f"{analysis.ph:.2f}", "6.5 - 8.5", "Normal" if 6.5 <= analysis.ph <= 8.5 else "Me'yordan chetlashgan"])
    writer.writerow(["TDS (mg/L)", f"{analysis.tds:.0f}", "<= 1000", "Normal" if analysis.tds <= 1000 else "Yuqori"])
    writer.writerow(["Turbidlik (NTU)", f"{analysis.turbidity:.1f}", "<= 5.0", "Normal" if analysis.turbidity <= 5.0 else "Yuqori"])
    writer.writerow(["Qattiqlik (mg/L)", f"{analysis.hardness:.0f}", "<= 200", "Normal" if analysis.hardness <= 200 else "Yuqori"])
    writer.writerow(["Sulfatlar (mg/L)", f"{analysis.sulfate:.0f}", "<= 250", "Normal" if analysis.sulfate <= 250 else "Yuqori"])
    writer.writerow(["Xloraminlar (mg/L)", f"{analysis.chloramines:.2f}", "<= 4.0", "Normal" if analysis.chloramines <= 4.0 else "Yuqori"])
    writer.writerow(["Organik uglerod (mg/L)", f"{analysis.organic:.1f}", "<= 10.0", "Normal" if analysis.organic <= 10.0 else "Yuqori"])
    writer.writerow(["Trihalometanlar (mg/L)", f"{analysis.trihalomethanes:.1f}", "<= 80.0", "Normal" if analysis.trihalomethanes <= 80.0 else "Yuqori"])
    writer.writerow(["Harorat (C)", f"{analysis.temperature:.1f}", "10 - 25", "Normal"])
    writer.writerow(["Elektr o'tkazuvchanlik (uS/cm)", f"{analysis.ec:.0f}", "<= 1000", "Normal" if analysis.ec <= 1000 else "Yuqori"])
    writer.writerow([])
    writer.writerow(["AI Tavsiyasi", analysis.ai_recommendation.replace("<b>", "").replace("</b>", ""), "", ""])

    content = output.getvalue()
    filename = f"water_analysis_{analysis.id}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/export/history/csv")
def export_all_history_csv(db: Session = Depends(get_db)):
    """Barcha tahlillar tarixini CSV ga eksport qilish"""
    analyses = db.query(WaterAnalysis).order_by(WaterAnalysis.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Namuna nomi", "Manba turi", "Hudud", "pH", "TDS (mg/L)",
        "Turbidlik (NTU)", "Qattiqlik (mg/L)", "Sulfatlar (mg/L)", "WQI Indeks",
        "Holat", "Sana"
    ])

    for a in analyses:
        writer.writerow([
            a.id, a.sample_name, a.source_type, a.location or "",
            f"{a.ph:.2f}", f"{a.tds:.0f}", f"{a.turbidity:.1f}", f"{a.hardness:.0f}",
            f"{a.sulfate:.0f}", f"{a.quality_score:.1f}", a.status_label,
            a.created_at.strftime("%d.%m.%Y %H:%M") if a.created_at else ""
        ])

    content = output.getvalue()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=water_analyses_history.csv"}
    )


@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, db: Session = Depends(get_db)):
    """Umumiy tahliliy statistika sahifasi"""
    current_user = auth.get_current_user_optional(request, db)
    analyses = db.query(WaterAnalysis).all()
    total_count = len(analyses)
    valid_count = sum(1 for a in analyses if a.status == "valid")
    conditional_count = sum(1 for a in analyses if a.status == "conditional")
    invalid_count = sum(1 for a in analyses if a.status == "invalid")

    # Manbalar bo'yicha guruhlash
    source_map = {}
    for a in analyses:
        s = a.source_type or "Boshqa"
        if s not in source_map:
            source_map[s] = {"count": 0, "scores": []}
        source_map[s]["count"] += 1
        source_map[s]["scores"].append(a.quality_score)

    icon_map = {
        "Vodoprovod suvi": "🚰",
        "Artezian suvi": "⛰️",
        "Quduq suvi": "🧱",
        "Daryo suvi": "🌊",
        "Ko‘l suvi": "🏞️",
        "Boshqa": "💧"
    }

    source_stats = []
    for s_name, s_data in source_map.items():
        avg_s = sum(s_data["scores"]) / len(s_data["scores"]) if s_data["scores"] else 0
        source_stats.append({
            "name": s_name,
            "icon": icon_map.get(s_name, "💧"),
            "count": s_data["count"],
            "avg_score": avg_s
        })

    # O'rtacha parametrlar foizi
    if total_count > 0:
        avg_ph_pct = min(round((sum(a.ph for a in analyses) / total_count / 8.5) * 100, 1), 100)
        avg_tds_pct = min(round((sum(a.tds for a in analyses) / total_count / 1000) * 100, 1), 100)
        avg_turbidity_pct = min(round((sum(a.turbidity for a in analyses) / total_count / 5) * 100, 1), 100)
        avg_hardness_pct = min(round((sum(a.hardness for a in analyses) / total_count / 200) * 100, 1), 100)
        avg_sulfate_pct = min(round((sum(a.sulfate for a in analyses) / total_count / 250) * 100, 1), 100)
    else:
        avg_ph_pct, avg_tds_pct, avg_turbidity_pct, avg_hardness_pct, avg_sulfate_pct = 82, 38, 35, 75, 44

    ctx = get_base_context(request, active_page="stats", current_user=current_user)
    ctx.update({
        "total_count": total_count,
        "valid_count": valid_count,
        "conditional_count": conditional_count,
        "invalid_count": invalid_count,
        "source_stats": source_stats,
        "avg_ph_pct": avg_ph_pct,
        "avg_tds_pct": avg_tds_pct,
        "avg_turbidity_pct": avg_turbidity_pct,
        "avg_hardness_pct": avg_hardness_pct,
        "avg_sulfate_pct": avg_sulfate_pct
    })
    return templates.TemplateResponse(request=request, name="user/stats.html", context=ctx)


@app.get("/profile", response_class=HTMLResponse)
def user_profile(request: Request, db: Session = Depends(get_db)):
    """Foydalanuvchi profili"""
    current_user = auth.get_current_user_optional(request, db)
    if not current_user:
        return RedirectResponse(url="/login?msg=Profilni+ko'rish+uchun+tizimga+kiring&type=warning", status_code=status.HTTP_303_SEE_OTHER)

    user_analyses = db.query(WaterAnalysis).filter(WaterAnalysis.user_id == current_user.id).all()
    user_analyses_count = len(user_analyses)
    user_valid_count = sum(1 for a in user_analyses if a.status == "valid")

    ctx = get_base_context(request, active_page="profile", current_user=current_user)
    ctx.update({
        "user_analyses_count": user_analyses_count,
        "user_valid_count": user_valid_count
    })
    return templates.TemplateResponse(request=request, name="user/profile.html", context=ctx)


@app.post("/profile/password")
def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Parolni yangilash"""
    current_user = auth.get_current_user_optional(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if not auth.verify_password(old_password, current_user.hashed_password):
        return RedirectResponse(url="/profile?msg=Joriy+parol+noto'g'ri&type=error", status_code=status.HTTP_303_SEE_OTHER)

    if len(new_password) < 6:
        return RedirectResponse(url="/profile?msg=Yangi+parol+kamida+6+ta+belgidan+iborat+bo'lishi+kerak&type=error", status_code=status.HTTP_303_SEE_OTHER)

    current_user.hashed_password = auth.hash_password(new_password)
    db.commit()

    return RedirectResponse(url="/profile?msg=Parol+muvaffaqiyatli+yangilandi&type=success", status_code=status.HTTP_303_SEE_OTHER)


# ==============================================================================
# Autentifikatsiya Marshrutlari (Login, Register, Logout)
# ==============================================================================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    current_user = auth.get_current_user_optional(request, db)
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    ctx = get_base_context(request, active_page="login")
    return templates.TemplateResponse(request=request, name="auth/login.html", context=ctx)


@app.post("/login", response_class=HTMLResponse)
def handle_login(
    request: Request,
    phone: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    clean_phone = auth.normalize_phone(phone)
    user = db.query(User).filter(User.phone == clean_phone).first()

    if not user or not auth.verify_password(password, user.hashed_password):
        ctx = get_base_context(request, active_page="login")
        ctx["error"] = "Telefon raqami yoki parol noto'g'ri kiritildi"
        ctx["phone"] = phone
        return templates.TemplateResponse(request=request, name="auth/login.html", context=ctx)

    if not user.is_active:
        ctx = get_base_context(request, active_page="login")
        ctx["error"] = "Sizning hisobingiz faol emas. Administratorga murojaat qiling."
        return templates.TemplateResponse(request=request, name="auth/login.html", context=ctx)

    token = auth.create_access_token(data={"sub": user.phone})
    response = RedirectResponse(url="/?msg=Tizimga+xush+kelibsiz!&type=success", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax"
    )
    return response


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    current_user = auth.get_current_user_optional(request, db)
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    ctx = get_base_context(request, active_page="register")
    return templates.TemplateResponse(request=request, name="auth/register.html", context=ctx)


@app.post("/register", response_class=HTMLResponse)
def handle_register(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    ctx = get_base_context(request, active_page="register")

    if password != confirm_password:
        ctx["error"] = "Kiritilgan parollar bir-biriga mos kelmadi"
        return templates.TemplateResponse(request=request, name="auth/register.html", context=ctx)

    if len(password) < 6:
        ctx["error"] = "Parol kamida 6 ta belgidan iborat bo'lishi lozim"
        return templates.TemplateResponse(request=request, name="auth/register.html", context=ctx)

    clean_phone = auth.normalize_phone(phone)
    if not clean_phone or len(clean_phone) < 9:
        ctx["error"] = "Telefon raqami to'g'ri kiritilmadi (+998 XX XXX-XX-XX)"
        return templates.TemplateResponse(request=request, name="auth/register.html", context=ctx)

    existing = db.query(User).filter(User.phone == clean_phone).first()
    if existing:
        ctx["error"] = "Ushbu telefon raqami allaqachon ro'yxatdan o'tgan"
        return templates.TemplateResponse(request=request, name="auth/register.html", context=ctx)

    new_user = User(
        full_name=full_name.strip(),
        phone=clean_phone,
        hashed_password=auth.hash_password(password),
        role="user",
        is_active=True
    )
    db.add(new_user)
    db.commit()

    token = auth.create_access_token(data={"sub": new_user.phone})
    response = RedirectResponse(url="/?msg=Hisob+muvaffaqiyatli+yaratildi!&type=success", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax"
    )
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login?msg=Tizimdan+muvaffaqiyatli+chiqildi&type=info", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


# ==============================================================================
# Administrator Paneli
# ==============================================================================

@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, db: Session = Depends(get_db)):
    """Admin boshqaruv paneli"""
    current_user = auth.get_current_user_optional(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/?msg=Ushbu+sahifaga+faqat+adminlar+kira+oladi&type=error", status_code=status.HTTP_303_SEE_OTHER)

    users = db.query(User).order_by(User.created_at.desc()).all()
    analyses = db.query(WaterAnalysis).order_by(WaterAnalysis.created_at.desc()).all()

    valid_count = sum(1 for a in analyses if a.status == "valid")
    invalid_count = sum(1 for a in analyses if a.status == "invalid")

    ctx = get_base_context(request, active_page="admin", current_user=current_user)
    ctx.update({
        "users": users,
        "analyses": analyses,
        "valid_count": valid_count,
        "invalid_count": invalid_count
    })
    return templates.TemplateResponse(request=request, name="admin/dashboard.html", context=ctx)


@app.post("/admin/analysis/delete/{analysis_id}")
def delete_analysis(request: Request, analysis_id: int, db: Session = Depends(get_db)):
    """Tahlilni o'chirish"""
    current_user = auth.get_current_user_optional(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    analysis = db.query(WaterAnalysis).filter(WaterAnalysis.id == analysis_id).first()
    if analysis:
        db.delete(analysis)
        db.commit()

    return RedirectResponse(url="/admin?msg=Tahlil+muvaffaqiyatli+o'chirildi&type=success", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/user/toggle-role/{user_id}")
def toggle_user_role(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Foydalanuvchi rolini o'zgartirish (admin <-> user)"""
    current_user = auth.get_current_user_optional(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user and target_user.id != current_user.id:
        target_user.role = "user" if target_user.role == "admin" else "admin"
        db.commit()

    return RedirectResponse(url="/admin?msg=Foydalanuvchi+roli+o'zgartirildi&type=success", status_code=status.HTTP_303_SEE_OTHER)


# ==============================================================================
# REST API Endpoints (JSON)
# ==============================================================================

class AnalyzeRequest(BaseModel):
    sample_name: str = Field("Suv namunasi", description="Namuna nomi")
    source_type: str = Field("Vodoprovod suvi", description="Suv manbasi")
    location: Optional[str] = Field("Toshkent", description="Hudud")
    ph: float = Field(7.0, ge=0, le=14, description="pH ko'rsatkichi")
    tds: float = Field(250.0, ge=0, description="TDS (mg/L)")
    turbidity: float = Field(1.0, ge=0, description="Loyqalik (NTU)")
    ec: float = Field(300.0, ge=0, description="Elektr o'tkazuvchanlik (uS/cm)")
    hardness: float = Field(150.0, ge=0, description="Qattiqlik (mg/L)")
    sulfate: float = Field(100.0, ge=0, description="Sulfatlar (mg/L)")
    chloramines: float = Field(2.0, ge=0, description="Xloraminlar (mg/L)")
    organic: float = Field(2.0, ge=0, description="Organik uglerod (mg/L)")
    trihalomethanes: float = Field(10.0, ge=0, description="Trihalometanlar (mg/L)")
    temperature: float = Field(20.0, description="Harorat (C)")


@app.post("/api/analyze")
def api_analyze_water(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    """Suv parametrlarini hisoblab, JSON formatida natijani qaytaruvchi API"""
    data = payload.model_dump()
    result = ai_engine.analyze_water_sample(data)

    analysis = WaterAnalysis(
        sample_name=payload.sample_name,
        source_type=payload.source_type,
        location=payload.location,
        temperature=payload.temperature,
        ph=payload.ph,
        tds=payload.tds,
        turbidity=payload.turbidity,
        ec=payload.ec,
        hardness=payload.hardness,
        sulfate=payload.sulfate,
        chloramines=payload.chloramines,
        organic=payload.organic,
        trihalomethanes=payload.trihalomethanes,
        status=result["status"],
        status_label=result["status_label"],
        quality_score=result["quality_score"],
        confidence=result["confidence"],
        prob_valid=result["prob_valid"],
        prob_conditional=result["prob_conditional"],
        prob_invalid=result["prob_invalid"],
        bad_parameters_count=result["bad_parameters_count"],
        status_text=result["status_text"],
        ai_recommendation=result["ai_recommendation"]
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    result["analysis_id"] = analysis.id
    return JSONResponse(content=result)


@app.get("/api/analyses")
def api_list_analyses(db: Session = Depends(get_db)):
    """Barcha tahlillar ro'yxatini qaytarish"""
    analyses = db.query(WaterAnalysis).order_by(WaterAnalysis.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "sample_name": a.sample_name,
            "source_type": a.source_type,
            "location": a.location,
            "quality_score": a.quality_score,
            "status": a.status,
            "status_label": a.status_label,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in analyses
    ]


@app.get("/api/analyses/{analysis_id}")
def api_get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Bitta tahlilning to'liq ma'lumotlarini olish"""
    a = db.query(WaterAnalysis).filter(WaterAnalysis.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Tahlil topilmadi")

    return {
        "id": a.id,
        "sample_name": a.sample_name,
        "source_type": a.source_type,
        "location": a.location,
        "parameters": {
            "ph": a.ph,
            "tds": a.tds,
            "turbidity": a.turbidity,
            "ec": a.ec,
            "hardness": a.hardness,
            "sulfate": a.sulfate,
            "chloramines": a.chloramines,
            "organic": a.organic,
            "trihalomethanes": a.trihalomethanes,
            "temperature": a.temperature
        },
        "quality_score": a.quality_score,
        "status": a.status,
        "status_label": a.status_label,
        "confidence": a.confidence,
        "probabilities": {
            "valid": a.prob_valid,
            "conditional": a.prob_conditional,
            "invalid": a.prob_invalid
        },
        "ai_recommendation": a.ai_recommendation,
        "created_at": a.created_at.isoformat() if a.created_at else None
    }


@app.get("/api/norms")
def api_get_norms(db: Session = Depends(get_db)):
    """Davlat me'yorlari va standartlari ro'yxati"""
    norms = db.query(ParameterNorm).all()
    return [
        {
            "code": n.code,
            "name": n.name,
            "unit": n.unit,
            "norm_text": n.norm_text,
            "min_val": n.min_val,
            "max_val": n.max_val,
            "importance_pct": n.importance_pct
        }
        for n in norms
    ]


# ==============================================================================
# Ishga tushirish (agar bevosita python main.py orqali chaqirilsa)
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
