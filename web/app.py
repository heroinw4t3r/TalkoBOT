import os
import json
import datetime as dt
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
import aiohttp
import ssl
import certifi
import logging
from sqlalchemy import select, insert, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from shared.config import get_settings
from shared.password import derive_password, current_version_key, hour_floor_utc
from shared.db import SessionLocal, init_db
from db import models

settings = get_settings()
logger = logging.getLogger("talko.web")
class AuthSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/favicon.ico" or path.startswith("/login"):
            return await call_next(request)
        v = request.session.get("pw_version")
        cur = current_version_key()
        if not v or v != cur:
            return RedirectResponse(url="/login", status_code=303)
        return await call_next(request)

# Явно задаём порядок middleware: сначала SessionMiddleware, затем AuthSessionMiddleware
app = FastAPI(middleware=[
    Middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, same_site="lax", https_only=False),
    Middleware(AuthSessionMiddleware),
])
BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
static_dir = os.path.join(BASE_DIR, "static")
if not os.path.isdir(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

async def require_auth(request: Request):
    # allow login page
    if request.url.path.startswith("/login"):
        return
    v = request.session.get("pw_version")
    cur = current_version_key()
    if not v or v != cur:
        return RedirectResponse(url="/login", status_code=303)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)  # пустой фавикон, без ошибки

 

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})

@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, password: str = Form(...)):
    cur_pwd = derive_password(settings.PASSWORD_SECRET)
    if password.strip() == cur_pwd:
        request.session["pw_version"] = current_version_key()
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный пароль"})

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Фильтры из query
    q_level = request.query_params.get("level")
    q_gender = request.query_params.get("gender")
    q_day = request.query_params.get("day")
    q_time = request.query_params.get("time")
    stmt = select(models.Form)
    if q_level:
        stmt = stmt.where(models.Form.level == q_level)
    if q_gender:
        stmt = stmt.where(models.Form.preferred_partner_gender == q_gender)
    if q_time:
        stmt = stmt.where(models.Form.time_of_day == q_time)
    # день недели ищем через LIKE по сохранённому JSON (простой быстрый фильтр)
    if q_day:
        stmt = stmt.where(models.Form.days.like(f"%{q_day}%"))
    stmt = stmt.order_by(models.Form.created_at.desc())
    async with SessionLocal() as session:  # type: AsyncSession
        rows = (await session.execute(stmt)).scalars().all()
    # минимальная карточка: Имя, возраст, уровень
    cards = []
    for f in rows:
        cards.append({
            "id": f.id,
            "full_name": f.full_name,
            "age": f.age,
            "level": f.level,
            "has_photo": bool(f.repost_photo_file_id),
            "in_project": bool(getattr(f, "in_project", False)),
            "details": {
                "Часовой пояс": f.timezone,
                "Телеграм": f.tg_username,
                "Участвовал ранее": f.participated_before,
                "Приоритет": f.priority,
                "Хобби": f.hobbies,
                "Темы": f.topics,
                "Дни": ", ".join(f.days_list()),
                "Время суток": f.time_of_day,
                "Соблюдение расписания": f.schedule_strictness,
                "Инициатива": f.initiative,
                "Партнер": f.preferred_partner_gender,
                "Примечания": f.other_notes,
                "Пакт правил": "Да" if f.accepted_rules else "Нет",
                "Оферта": "Да" if f.accepted_offer else "Нет",
                "NDA": "Да" if f.accepted_nda else "Нет",
                "ID фото репоста": f.repost_photo_file_id or "-",
                "Создано": f.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            }
        })
    return templates.TemplateResponse("index.html", {"request": request, "cards_json": json.dumps(cards, ensure_ascii=False)})

@app.post("/toggle/{form_id}")
async def toggle_in_project(request: Request, form_id: int):
    async with SessionLocal() as session:  # type: AsyncSession
        row = (await session.execute(select(models.Form).where(models.Form.id == form_id))).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Анкета не найдена")
        new_val = not bool(row.in_project)
        await session.execute(update(models.Form).where(models.Form.id == form_id).values(in_project=new_val))
        await session.commit()
    return {"ok": True, "in_project": new_val}

@app.get("/project", response_class=HTMLResponse)
async def project_page(request: Request):
    async with SessionLocal() as session:  # type: AsyncSession
        inproj = (await session.execute(select(models.Form).where(models.Form.in_project == True).order_by(models.Form.created_at.desc()))).scalars().all()
        pairs = (await session.execute(select(models.StudyBuddy).order_by(models.StudyBuddy.created_at.desc()))).scalars().all()
        # Собираем данные пар
        form_by_id = {f.id: f for f in inproj}
        # также дотянем формы, которых нет в inproj (если уже спарены)
        ids_missing = set()
        for p in pairs:
            if p.form1_id not in form_by_id: ids_missing.add(p.form1_id)
            if p.form2_id not in form_by_id: ids_missing.add(p.form2_id)
        if ids_missing:
            extra = (await session.execute(select(models.Form).where(models.Form.id.in_(list(ids_missing))))).scalars().all()
            for f in extra: form_by_id[f.id] = f
    # Готовим JSON
    def brief(f):
        return {
            "id": f.id,
            "full_name": f.full_name,
            "age": f.age,
            "level": f.level,
            "has_photo": bool(f.repost_photo_file_id),
            "in_project": bool(getattr(f, "in_project", False)),
            "details": {
                "Часовой пояс": f.timezone,
                "Телеграм": f.tg_username,
                "Дни": ", ".join(f.days_list()),
                "Время суток": f.time_of_day,
            }
        }
    forms_json = [brief(f) for f in inproj]
    buddies_json = [{
        "id": p.id,
        "a": brief(form_by_id.get(p.form1_id)),
        "b": brief(form_by_id.get(p.form2_id))
    } for p in pairs if form_by_id.get(p.form1_id) and form_by_id.get(p.form2_id)]
    return templates.TemplateResponse("project.html", {"request": request, "forms_json": json.dumps(forms_json, ensure_ascii=False), "buddies_json": json.dumps(buddies_json, ensure_ascii=False)})

@app.get("/pairs", response_class=HTMLResponse)
async def pairs_page(request: Request):
    async with SessionLocal() as session:  # type: AsyncSession
        pairs = (await session.execute(select(models.StudyBuddy).order_by(models.StudyBuddy.created_at.desc()))).scalars().all()
        # подтянем формы
        ids = set()
        for p in pairs:
            ids.add(p.form1_id); ids.add(p.form2_id)
        forms = (await session.execute(select(models.Form).where(models.Form.id.in_(list(ids))))).scalars().all()
        fmap = {f.id: f for f in forms}
    def brief(f):
        return {"id": f.id, "full_name": f.full_name, "age": f.age, "level": f.level}
    buddies_json = [{
        "id": p.id,
        "a": brief(fmap.get(p.form1_id)),
        "b": brief(fmap.get(p.form2_id))
    } for p in pairs if fmap.get(p.form1_id) and fmap.get(p.form2_id)]
    return templates.TemplateResponse("pairs.html", {"request": request, "buddies_json": json.dumps(buddies_json, ensure_ascii=False)})

@app.post("/pair")
async def create_pair(request: Request):
    data = await request.json()
    a = int(data.get("a")); b = int(data.get("b"))
    if not a or not b or a == b:
        raise HTTPException(status_code=400, detail="Нужны два разных id")
    async with SessionLocal() as session:  # type: AsyncSession
        # Проверим, что формы существуют
        forms = (await session.execute(select(models.Form).where(models.Form.id.in_([a,b])))).scalars().all()
        if len(forms) != 2:
            raise HTTPException(status_code=404, detail="Форма не найдена")
        await session.execute(insert(models.StudyBuddy).values(form1_id=a, form2_id=b))
        await session.commit()
    return {"ok": True}

@app.post("/pair/delete")
async def delete_pair(request: Request):
    data = await request.json()
    pid = int(data.get("id", 0))
    if not pid:
        raise HTTPException(status_code=400, detail="id пары обязателен")
    async with SessionLocal() as session:  # type: AsyncSession
        await session.execute(delete(models.StudyBuddy).where(models.StudyBuddy.id == pid))
        await session.commit()
    return {"ok": True}

@app.get("/photo/{form_id}")
async def photo_proxy(request: Request, form_id: int):
    # Доступ защищен тем же middleware сессии
    async with SessionLocal() as session:  # type: AsyncSession
        row = (await session.execute(select(models.Form).where(models.Form.id == form_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Анкета не найдена")
    if not row.repost_photo_file_id:
        raise HTTPException(status_code=404, detail="Фото отсутствует")
    if not settings.BOT1_TOKEN:
        logger.error("BOT1_TOKEN is empty; cannot fetch Telegram file for form_id=%s", form_id)
        raise HTTPException(status_code=500, detail="BOT1_TOKEN не задан на сервере")

    # 1) Получаем file_path через getFile
    api_base = f"https://api.telegram.org/bot{settings.BOT1_TOKEN}"
    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as http:
            async with http.get(f"{api_base}/getFile", params={"file_id": row.repost_photo_file_id}) as r1:
                if r1.status != 200:
                    text = await r1.text()
                    logger.error("getFile status=%s body=%s", r1.status, text[:500])
                    raise HTTPException(status_code=502, detail=f"Telegram getFile HTTP {r1.status}")
                # allow non-json content-type just in case
                data = await r1.json(content_type=None)
                if not data.get("ok"):
                    logger.error("getFile ok=false payload=%s", data)
                    raise HTTPException(status_code=502, detail="Telegram getFile not ok")
                file_path = data.get("result", {}).get("file_path")
                if not file_path:
                    logger.error("getFile missing file_path payload=%s", data)
                    raise HTTPException(status_code=404, detail="file_path not found")

            # 2) Скачиваем файл
            file_url = f"https://api.telegram.org/file/bot{settings.BOT1_TOKEN}/{file_path}"
            async with http.get(file_url) as r2:
                if r2.status != 200:
                    text = await r2.text()
                    logger.error("download status=%s body=%s", r2.status, text[:500])
                    raise HTTPException(status_code=502, detail=f"Telegram file HTTP {r2.status}")
                content_type = r2.headers.get("Content-Type", "image/jpeg")
                content = await r2.read()
                return Response(content=content, media_type=content_type)
    except aiohttp.ClientError as e:
        logger.exception("Telegram ClientError while fetching photo for form_id=%s", form_id)
        raise HTTPException(status_code=502, detail="Ошибка сети при обращении к Telegram")
    except Exception:
        logger.exception("Unexpected error while fetching photo for form_id=%s", form_id)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка обработки фото")

async def rotate_and_persist_password():
    """Сохраняем текущий пароль в БД каждый час (для аудита/синхронизации)."""
    now = hour_floor_utc()
    version = current_version_key(now)
    value = derive_password(settings.PASSWORD_SECRET, now)
    async with SessionLocal() as session:  # type: AsyncSession
        row = (await session.execute(select(models.PasswordState).where(models.PasswordState.id == 1))).scalar_one_or_none()
        if row:
            await session.execute(update(models.PasswordState).where(models.PasswordState.id == 1).values(version_key=version, value=value))
        else:
            await session.execute(insert(models.PasswordState).values(id=1, version_key=version, value=value))
        await session.commit()

def setup_scheduler():
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(lambda: None, "interval", seconds=1)  # keep loop active in some envs
    sched.add_job(lambda: None, "date")  # no-op
    sched.add_job(lambda: None, "cron", minute="*")  # no-op
    # Реальная задача:
    sched.add_job(lambda: None, "cron", minute=0)  # placeholder, we'll run async below
    # Привязываем корректно async-задачу:
    sched.remove_all_jobs()
    sched.add_job(lambda: None, "date")  # ensure scheduler alive
    sched.add_job(lambda: None, "cron", minute="*")
    sched.add_job(lambda: None, "interval", minutes=5)
    # Ежечасно на нуле минуты:
    sched.add_job(lambda: None, "cron", minute=0)
    # Используем вспомогательный “tick” для вызова async функции:
    sched.add_job(lambda: None, "date")
    sched.start()

@app.on_event("startup")
async def on_startup():
    await init_db(models)
    # lightweight migration for new columns
    try:
        async with SessionLocal() as session:
            res = await session.execute(text("PRAGMA table_info(forms)"))
            cols = [row[1] for row in res.all()]  # name is at index 1
            if "in_project" not in cols:
                await session.execute(text("ALTER TABLE forms ADD COLUMN in_project BOOLEAN DEFAULT 0"))
            if "alt_contact" not in cols:
                await session.execute(text("ALTER TABLE forms ADD COLUMN alt_contact TEXT DEFAULT ''"))
                await session.commit()
    except Exception:
        logger.exception("DB migration check failed")
    await rotate_and_persist_password()  # сразу сохранить при старте
    # Простой таймер без сложной привязки APScheduler к async:
    async def hourly():
        while True:
            now = dt.datetime.utcnow()
            next_top = (now.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1))
            await asyncio.sleep( (next_top - now).total_seconds() )
            await rotate_and_persist_password()
    import asyncio
    asyncio.create_task(hourly())