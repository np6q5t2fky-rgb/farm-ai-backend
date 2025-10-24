from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pydantic import BaseModel, Field
from typing import Optional

# DB models and session
from database.models import (
    create_tables,
    get_db,
    Sow,
    WeeklyRecord,
)
from sqlalchemy.orm import Session

# AI model (Gemini)
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _ai_model = genai.GenerativeModel('gemini-pro')
    except Exception:
        _ai_model = None
else:
    _ai_model = None

app = FastAPI(title="Farm AI Chat", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (icons, images) for PWA; tolerate missing directory in repo
static_dir = "backend/static"
try:
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception:
    # Ignore static mount issues to prevent startup failure on Render
    pass


@app.get("/")
def root():
    """Головна: HTML + PWA (маніфест, Service Worker)"""
    return HTMLResponse("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐷 Farm AI</title>
    <meta name="theme-color" content="#667eea">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/static/icons/icon-192.png">
    <style>
        body { 
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; font-family: Arial; min-height: 100vh;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .card { 
            background: rgba(255,255,255,0.1); padding: 30px; 
            border-radius: 20px; margin: 20px 0; backdrop-filter: blur(10px);
        }
        h1 { font-size: 2.5em; margin-bottom: 10px; }
        .status { 
            background: rgba(0,255,0,0.2); padding: 15px; 
            border-radius: 10px; margin: 20px 0; font-size: 1.2em;
        }
        .actions { display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin-top: 10px; }
        .btn { background:#111827; color:white; border:1px solid #374151; padding:10px 16px; border-radius:10px; cursor:pointer; }
        .btn.primary { background:#2563eb; border-color:#1d4ed8; }
        .toast { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.75); color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 14px; display:none; }

        /* Chat */
        .chat { display:flex; gap:16px; }
        .chat-col { flex:1; min-width: 280px; }
        .messages { height: 360px; overflow:auto; padding:12px; background: rgba(255,255,255,0.08); border-radius:12px; }
        .msg { margin: 8px 0; padding: 10px 12px; border-radius: 10px; line-height: 1.4; }
        .msg.user { background:#2563eb; color:#fff; border-top-right-radius: 4px; }
        .msg.ai { background:#111827; color:#e5e7eb; border-top-left-radius: 4px; }
        .msg small { display:block; opacity:0.7; margin-top:6px; font-size: 12px; }
        .row { display:flex; gap:8px; margin-top:10px; }
        .row input { flex:1; padding:10px 12px; border-radius:8px; border:1px solid #374151; background:#0b1220; color:#fff; }
        .row button { padding:10px 14px; border-radius:8px; border:1px solid #374151; background:#2563eb; color:#fff; cursor:pointer; }
        .hint { font-size: 13px; opacity: 0.85; }
    </style>
    <link rel="preload" href="/sw.js" as="script" crossorigin>
    <meta http-equiv="Cache-Control" content="no-store" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta http-equiv="Expires" content="0" />
</head>
<body>
    <div class="container">
        <div class="card" style="text-align:center">
            <h1>🐷 Farm AI Chat</h1>
            <p>Система обліку свиноферми</p>
            <div class="actions" style="justify-content:center">
                <button id="installBtn" class="btn primary" style="display:none">⬇️ Встановити як додаток</button>
                <button id="refreshBtn" class="btn">🔄 Оновити</button>
            </div>
        </div>

        <div class="card">
            <h3>Чат з AI</h3>
            <div class="chat">
                <div class="chat-col">
                    <div id="messages" class="messages"></div>
                    <div class="row">
                        <input id="input" placeholder="Напишіть питання…" />
                        <button id="send">Надіслати</button>
                    </div>
                    <div class="hint">Порада: напишіть "Підсумуй останні 4 тижні" або "Яка виживаність і що покращити?"</div>
                </div>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        function showToast(msg) {
            const el = document.getElementById('toast');
            el.textContent = msg;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 2500);
        }

        if ('serviceWorker' in navigator) {
            window.addEventListener('load', async () => {
                try {
                    const reg = await navigator.serviceWorker.register('/sw.js');
                    reg.update().catch(()=>{});
                    reg.addEventListener('updatefound', () => {
                        const newWorker = reg.installing;
                        if (newWorker) {
                            newWorker.addEventListener('statechange', () => {
                                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                    showToast('Доступне оновлення — перезавантажую...');
                                    setTimeout(() => window.location.reload(), 500);
                                }
                            });
                        }
                    });
                    let refreshing = false;
                    navigator.serviceWorker.addEventListener('controllerchange', () => {
                        if (refreshing) return; refreshing = true;
                        window.location.reload();
                    });
                } catch (e) { console.log('SW error', e); }
            });
        }

        let deferredPrompt = null;
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            const btn = document.getElementById('installBtn');
            btn.style.display = 'inline-block';
        });
        document.getElementById('installBtn').addEventListener('click', async () => {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') showToast('Встановлення розпочато');
            deferredPrompt = null;
        });

        document.getElementById('refreshBtn').addEventListener('click', () => window.location.reload());

        // Chat logic
        const elMsgs = document.getElementById('messages');
        const elInput = document.getElementById('input');
        const elSend = document.getElementById('send');
        const history = JSON.parse(localStorage.getItem('farm_chat_hist')||'[]');

        function render(){
            elMsgs.innerHTML = history.map(m => `
                <div class="msg ${m.role}">${m.text.replace(/</g,'&lt;').replace(/\n/g,'<br>')}
                    <small>${new Date(m.time).toLocaleString()}</small>
                </div>`).join('');
            elMsgs.scrollTop = elMsgs.scrollHeight;
        }
        render();

        function push(role, text){
            history.push({role, text, time: Date.now()});
            if(history.length>50) history.shift();
            localStorage.setItem('farm_chat_hist', JSON.stringify(history));
            render();
        }

        async function send(){
            const msg = elInput.value.trim();
            if(!msg) return;
            elInput.value = '';
            push('user', msg);
            const typingId = `typing_${Date.now()}`;
            elMsgs.insertAdjacentHTML('beforeend', `<div id="${typingId}" class="msg ai">Думаю…</div>`);
            elMsgs.scrollTop = elMsgs.scrollHeight;
            try{
                const res = await fetch('/api/chat', {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({message: msg, include_context: true})
                });
                if(!res.ok){
                    const err = await res.json().catch(()=>({detail: res.statusText}));
                    throw new Error(err.detail||'Помилка сервера');
                }
                const data = await res.json();
                document.getElementById(typingId)?.remove();
                push('ai', data.response || 'Немає відповіді');
            }catch(e){
                document.getElementById(typingId)?.remove();
                push('ai', `❌ ${e.message}`);
            }
        }
        elSend.addEventListener('click', send);
        elInput.addEventListener('keydown', (e)=>{ if(e.key==='Enter') send(); });
    </script>
</body>
</html>""")


@app.head("/")
def root_head():
    """Handle HEAD / to avoid 405 in platform health checks."""
    return Response(status_code=200)


@app.get("/health")
def health():
    """Health check with clear status for monitoring and user checks."""
    return {"status": "online", "message": "Farm AI Backend працює!", "version": app.version}


@app.get("/healthz")
def healthz():
    """Alias for platform health checks (Render default: /healthz)."""
    return {"status": "online", "message": "Farm AI Backend працює!", "version": app.version}


@app.get("/manifest.json")
def manifest():
    """PWA manifest (disable cache to ensure fast updates)"""
    manifest = {
        "name": "Farm AI Chat",
        "short_name": "Farm AI",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#1f2937",
        "theme_color": "#667eea",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    import json
    return Response(
        content=json.dumps(manifest),
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache"}
    )


@app.get("/offline")
def offline_page():
    """Offline fallback page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>Farm AI — Offline</title>
    <style>body{background:#111;color:#eee;font-family:Arial;margin:0;padding:24px} .box{max-width:600px;margin:0 auto;text-align:center;background:#1f2937;padding:24px;border-radius:12px} a{color:#93c5fd}</style>
    </head><body>
    <div class='box'>
      <h2>🔌 Немає інтернету</h2>
      <p>Додаток встановлено на телефон. Як тільки зʼявиться мережа — дані оновляться автоматично.</p>
      <p><a href="/">Спробувати знову</a></p>
    </div>
    </body></html>
    """)


@app.get("/sw.js")
def service_worker():
    """Service Worker for PWA caching and auto-update (no-cache headers)"""
    sw_code = r"""
        const CACHE = 'farm-ai-v1';
        const APP_SHELL = ['/', '/manifest.json', '/offline'];

        self.addEventListener('install', (event) => {
            self.skipWaiting();
            event.waitUntil(
                caches.open(CACHE).then(cache => cache.addAll(APP_SHELL))
            );
        });

        self.addEventListener('activate', (event) => {
            event.waitUntil(
                (async () => {
                    const keys = await caches.keys();
                    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
                    await self.clients.claim();
                })()
            );
        });

        self.addEventListener('fetch', (event) => {
            const req = event.request;
            const url = new URL(req.url);

            if (req.mode === 'navigate') {
                event.respondWith(
                    (async () => {
                        try {
                            const fresh = await fetch(req);
                            const cache = await caches.open(CACHE);
                            cache.put('/', fresh.clone());
                            return fresh;
                        } catch (e) {
                            const cache = await caches.open(CACHE);
                            const cached = await cache.match('/');
                            return cached || cache.match('/offline');
                        }
                    })()
                );
                return;
            }

            if (url.origin === location.origin) {
                event.respondWith(
                    caches.match(req).then(cached => {
                        const network = fetch(req).then(res => {
                            caches.open(CACHE).then(cache => cache.put(req, res.clone()));
                            return res;
                        }).catch(() => cached);
                        return cached || network;
                    })
                );
            }
        });
    """
    return Response(content=sw_code, media_type="text/javascript", headers={"Cache-Control": "no-cache"})


# ===================== API: Chat =====================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    include_context: Optional[bool] = True


@app.post("/api/chat")
def chat_with_ai(req: ChatRequest, db: Session = Depends(get_db)):
    if not _ai_model:
        raise HTTPException(status_code=503, detail="AI недоступний. Перевірте GEMINI_API_KEY")

    # Контекст з БД: останні 8 тижнів + статистика свиноматок
    recent = db.query(WeeklyRecord).order_by(WeeklyRecord.week_start_date.desc()).limit(8).all()
    active = db.query(Sow).filter(Sow.status == "активна").count()
    total = db.query(Sow).count()

    context = ""
    if req.include_context:
        context = (
            f"Свиноматки: всього {total}, активних {active}.\n"
            f"Останні тижні:\n" +
            "\n".join([
                f"- {r.week_start_date}: {r.farrowings} опоросів, виживаність {r.survival_rate:.1f}%"
                for r in recent
            ])
        )

    system_prompt = (
        "Ти — AI асистент для свиноферми. Аналізуй дані та відповідай українською,"
        " будь конкретним і корисним. Якщо даних бракує — проси уточнення."
    )

    full_prompt = f"{system_prompt}\n\n{context}\n\nПитання: {req.message}"
    try:
        resp = _ai_model.generate_content(full_prompt)
        text = getattr(resp, 'text', None) or "(порожня відповідь)"
        return {"response": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка AI: {str(e)}")


# ===================== Startup: ensure tables =====================
@app.on_event("startup")
def _on_startup():
    try:
        create_tables()
    except Exception:
        # Не блокуємо старт, якщо немає прав/БД — чат без контексту все одно можливий
        pass


if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
