from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Farm AI Chat", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        .container { max-width: 600px; margin: 0 auto; text-align: center; }
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
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🐷 Farm AI Chat</h1>
            <p>Система обліку свиноферми</p>
            
            <div class="status">
                ✅ ВИПРАВЛЕНО ЧОРНИЙ ЕКРАН!
            </div>
            
            <p>🎉 Тепер працює HTML інтерфейс</p>
            <p>📱 Відкривається на мобільному</p>
            <p>🚀 Деплой успішний!</p>

            <div class="actions">
                <button id="installBtn" class="btn primary" style="display:none">⬇️ Встановити як додаток</button>
                <button id="refreshBtn" class="btn">🔄 Оновити</button>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        // Показ тоста
        function showToast(msg) {
            const el = document.getElementById('toast');
            el.textContent = msg;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 2500);
        }

        // Реєстрація Service Worker + автооновлення
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', async () => {
                try {
                    const reg = await navigator.serviceWorker.register('/sw.js');
                    // Перевірка оновлення на старті
                    reg.update().catch(()=>{});

                    // Якщо з'явився новий SW
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

                    // Коли новий SW активувався
                    let refreshing = false;
                    navigator.serviceWorker.addEventListener('controllerchange', () => {
                        if (refreshing) return; refreshing = true;
                        window.location.reload();
                    });
                } catch (e) {
                    console.log('SW error', e);
                }
            });
        }

        // beforeinstallprompt (кнопка встановлення)
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

        // Оновити вручну
        document.getElementById('refreshBtn').addEventListener('click', () => window.location.reload());
    </script>
</body>
</html>""")

@app.get("/health")
def health():
    return {"status": "fixed", "html": True}

if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))


# ===================== PWA endpoints =====================
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

            // Для переходів по сторінках — network-first з offline fallback
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

            // Для статичних ресурсів — stale-while-revalidate
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
