#!/usr/bin/env python3
"""Rebuild site/index.html from site/library.json.
Light theme + collapsible book groups + QR share button.
Run from the 'Scripture Reader-WORKING' folder:  python3 build_index.py
Safe to re-run any time chapters are added to library.json."""
import json, os, html

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, 'site')
lib = json.load(open(os.path.join(SITE, 'library.json'), encoding='utf-8'))

def fmt(sec):
    sec = int(sec or 0)
    return f"{sec//60}:{sec%60:02d}"

# Group: set -> book -> [entries], preserving library.json order
sets = {}
for e in lib:
    sets.setdefault(e['scriptureSet'], {}).setdefault(e['book'], []).append(e)

QR_PATH = "M0 0h7v1h-7zM8 0h2v1h-2zM17 0h2v1h-2zM22 0h7v1h-7zM0 1h1v1h-1zM6 1h1v1h-1zM9 1h1v1h-1zM12 1h1v1h-1zM16 1h1v1h-1zM19 1h2v1h-2zM22 1h1v1h-1zM28 1h1v1h-1zM0 2h1v1h-1zM2 2h3v1h-3zM6 2h1v1h-1zM9 2h1v1h-1zM13 2h1v1h-1zM15 2h3v1h-3zM20 2h1v1h-1zM22 2h1v1h-1zM24 2h3v1h-3zM28 2h1v1h-1zM0 3h1v1h-1zM2 3h3v1h-3zM6 3h1v1h-1zM8 3h2v1h-2zM14 3h3v1h-3zM18 3h1v1h-1zM20 3h1v1h-1zM22 3h1v1h-1zM24 3h3v1h-3zM28 3h1v1h-1zM0 4h1v1h-1zM2 4h3v1h-3zM6 4h1v1h-1zM8 4h1v1h-1zM10 4h2v1h-2zM13 4h2v1h-2zM16 4h3v1h-3zM22 4h1v1h-1zM24 4h3v1h-3zM28 4h1v1h-1zM0 5h1v1h-1zM6 5h1v1h-1zM8 5h8v1h-8zM18 5h2v1h-2zM22 5h1v1h-1zM28 5h1v1h-1zM0 6h7v1h-7zM8 6h1v1h-1zM10 6h1v1h-1zM12 6h1v1h-1zM14 6h1v1h-1zM16 6h1v1h-1zM18 6h1v1h-1zM20 6h1v1h-1zM22 6h7v1h-7zM8 7h3v1h-3zM14 7h1v1h-1zM17 7h2v1h-2zM20 7h1v1h-1zM0 8h1v1h-1zM4 8h1v1h-1zM6 8h4v1h-4zM13 8h5v1h-5zM19 8h7v1h-7zM28 8h1v1h-1zM1 9h1v1h-1zM4 9h1v1h-1zM7 9h1v1h-1zM9 9h2v1h-2zM18 9h1v1h-1zM21 9h8v1h-8zM0 10h5v1h-5zM6 10h2v1h-2zM10 10h2v1h-2zM13 10h3v1h-3zM18 10h1v1h-1zM21 10h2v1h-2zM28 10h1v1h-1zM2 11h1v1h-1zM4 11h1v1h-1zM7 11h2v1h-2zM12 11h2v1h-2zM15 11h3v1h-3zM19 11h3v1h-3zM24 11h2v1h-2zM27 11h2v1h-2zM0 12h1v1h-1zM2 12h5v1h-5zM8 12h1v1h-1zM11 12h1v1h-1zM13 12h1v1h-1zM17 12h1v1h-1zM20 12h2v1h-2zM27 12h1v1h-1zM4 13h2v1h-2zM8 13h1v1h-1zM11 13h1v1h-1zM13 13h2v1h-2zM16 13h2v1h-2zM22 13h1v1h-1zM24 13h5v1h-5zM2 14h1v1h-1zM6 14h2v1h-2zM9 14h1v1h-1zM11 14h2v1h-2zM16 14h2v1h-2zM22 14h1v1h-1zM25 14h2v1h-2zM28 14h1v1h-1zM5 15h1v1h-1zM8 15h2v1h-2zM12 15h1v1h-1zM14 15h1v1h-1zM17 15h4v1h-4zM22 15h1v1h-1zM24 15h1v1h-1zM27 15h2v1h-2zM1 16h4v1h-4zM6 16h1v1h-1zM8 16h1v1h-1zM13 16h6v1h-6zM20 16h2v1h-2zM27 16h1v1h-1zM0 17h1v1h-1zM2 17h3v1h-3zM8 17h3v1h-3zM12 17h1v1h-1zM17 17h2v1h-2zM20 17h1v1h-1zM22 17h4v1h-4zM27 17h2v1h-2zM2 18h3v1h-3zM6 18h3v1h-3zM10 18h2v1h-2zM13 18h3v1h-3zM18 18h1v1h-1zM21 18h2v1h-2zM24 18h1v1h-1zM26 18h1v1h-1zM28 18h1v1h-1zM3 19h1v1h-1zM5 19h1v1h-1zM9 19h1v1h-1zM11 19h3v1h-3zM15 19h3v1h-3zM19 19h1v1h-1zM22 19h1v1h-1zM24 19h1v1h-1zM27 19h2v1h-2zM0 20h3v1h-3zM4 20h1v1h-1zM6 20h2v1h-2zM9 20h1v1h-1zM13 20h1v1h-1zM17 20h1v1h-1zM19 20h7v1h-7zM28 20h1v1h-1zM8 21h1v1h-1zM12 21h3v1h-3zM16 21h1v1h-1zM18 21h1v1h-1zM20 21h1v1h-1zM24 21h1v1h-1zM28 21h1v1h-1zM0 22h7v1h-7zM8 22h1v1h-1zM10 22h1v1h-1zM12 22h1v1h-1zM16 22h2v1h-2zM19 22h2v1h-2zM22 22h1v1h-1zM24 22h3v1h-3zM28 22h1v1h-1zM0 23h1v1h-1zM6 23h1v1h-1zM9 23h1v1h-1zM11 23h1v1h-1zM14 23h1v1h-1zM17 23h4v1h-4zM24 23h1v1h-1zM27 23h1v1h-1zM0 24h1v1h-1zM2 24h3v1h-3zM6 24h1v1h-1zM8 24h3v1h-3zM12 24h4v1h-4zM17 24h1v1h-1zM19 24h7v1h-7zM27 24h2v1h-2zM0 25h1v1h-1zM2 25h3v1h-3zM6 25h1v1h-1zM9 25h1v1h-1zM12 25h2v1h-2zM20 25h2v1h-2zM27 25h1v1h-1zM0 26h1v1h-1zM2 26h3v1h-3zM6 26h1v1h-1zM10 26h2v1h-2zM13 26h5v1h-5zM19 26h1v1h-1zM21 26h1v1h-1zM25 26h4v1h-4zM0 27h1v1h-1zM6 27h1v1h-1zM9 27h9v1h-9zM20 27h1v1h-1zM22 27h4v1h-4zM27 27h2v1h-2zM0 28h7v1h-7zM8 28h1v1h-1zM10 28h2v1h-2zM16 28h2v1h-2zM20 28h1v1h-1zM24 28h2v1h-2zM27 28h1v1h-1z"

STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{background:#faf5ea;color:#2f2a22;font-family:'Lora',Georgia,serif;min-height:100vh;}
.layout{display:flex;min-height:100vh;}
.sidebar{width:260px;flex-shrink:0;background:#f1e9da;border-right:1px solid rgba(62,52,38,0.12);display:flex;flex-direction:column;position:sticky;top:0;height:100vh;overflow-y:auto;}
.sidebar-header{padding:22px 20px 16px;border-bottom:1px solid rgba(62,52,38,0.12);}
.app-title{font-size:18px;font-weight:600;letter-spacing:-0.01em;line-height:1.2;}
.app-sub{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#8a6a34;text-transform:uppercase;letter-spacing:0.08em;margin-top:4px;}
.book-nav{padding:8px 0;flex:1;}
.set-section{margin-bottom:2px;}
.set-label{display:flex;align-items:center;justify-content:space-between;padding:9px 20px;font-size:14px;font-weight:600;color:#2f2a22;cursor:pointer;user-select:none;background:rgba(62,52,38,0.05);}
.set-label:hover{color:#8a6a34;}
.set-list{display:none;}
.set-list.open{display:block;}
.book-section{margin-bottom:0;}
.book-label{display:flex;align-items:center;justify-content:space-between;padding:7px 20px 7px 32px;font-size:13px;font-weight:500;color:#7c7465;cursor:pointer;user-select:none;}
.book-label:hover{color:#2f2a22;}
.chapter-list{display:none;padding:0 0 4px;}
.chapter-list.open{display:block;}
.chapter-item{display:block;padding:5px 20px 5px 44px;font-size:12px;color:#7c7465;text-decoration:none;font-family:'IBM Plex Mono',monospace;}
.chapter-item:hover{color:#2f2a22;background:rgba(62,52,38,0.05);}
.arrow{font-size:10px;transition:transform 0.2s;opacity:0.4;font-family:'IBM Plex Mono',monospace;}
.set-label.open .arrow,.book-label.open .arrow{transform:rotate(90deg);}
.main{flex:1;padding:3rem 2.5rem;max-width:860px;}
.welcome{margin-bottom:3rem;}
.welcome h2{font-size:28px;font-weight:600;letter-spacing:-0.02em;margin-bottom:8px;}
.welcome p{font-size:15px;color:#7c7465;line-height:1.7;max-width:520px;font-style:italic;}
.section-title{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#8a6a34;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:20px;padding-bottom:8px;border-bottom:1px solid rgba(62,52,38,0.12);}
.set-group{margin-bottom:3rem;}
.set-group-title{font-size:22px;font-weight:600;letter-spacing:-0.02em;margin-bottom:20px;border-bottom:1px solid rgba(62,52,38,0.12);padding-bottom:10px;}
.book-group{margin-bottom:2rem;}
.book-group-title{font-size:17px;font-weight:500;letter-spacing:-0.01em;margin-bottom:12px;color:#7c7465;}
.chapter-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;}
.chapter-card{display:flex;align-items:center;gap:12px;background:#f1e9da;border:1px solid rgba(62,52,38,0.12);border-radius:10px;padding:14px 16px;text-decoration:none;color:#2f2a22;transition:background 0.15s,border-color 0.15s,transform 0.1s;}
.chapter-card:hover{background:#e9dfcc;border-color:rgba(62,52,38,0.22);transform:translateY(-1px);}
.play-icon{width:32px;height:32px;background:rgba(138,106,52,0.12);border:1px solid rgba(138,106,52,0.3);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;color:#8a6a34;}
.card-chapter{font-size:14px;font-weight:500;}
.card-book{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#7c7465;margin-top:2px;text-transform:uppercase;letter-spacing:0.06em;display:flex;align-items:center;gap:6px;}
.card-duration{color:#8a6a34;opacity:0.8;}
.empty-state{text-align:center;padding:4rem 2rem;color:#7c7465;}
.empty-state .big{font-size:40px;margin-bottom:16px;opacity:0.4;}
.empty-state h3{font-size:18px;font-weight:500;margin-bottom:8px;color:#2f2a22;}
/* Collapsible groups in main window */
.set-group-title,.book-group-title{cursor:pointer;user-select:none;display:flex;align-items:center;justify-content:space-between;gap:10px;-webkit-tap-highlight-color:transparent;}
.set-group-title:hover,.book-group-title:hover{color:#8a6a34;}
.g-arrow{font-family:'IBM Plex Mono',monospace;font-size:11px;opacity:0.45;transition:transform 0.2s;flex-shrink:0;}
.set-group.open>.set-group-title .g-arrow,.book-group.open>.book-group-title .g-arrow{transform:rotate(90deg);}
.set-group:not(.open)>.book-group{display:none;}
.book-group:not(.open)>.chapter-grid{display:none;}
.book-group:not(.open){margin-bottom:0.9rem;}
@media(max-width:640px){.sidebar{display:none;}.main{padding:1.5rem 1rem;}.chapter-grid{grid-template-columns:1fr;}.book-group-title{padding:6px 0;}}
/* QR button + modal */
.welcome-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px;}
.welcome-row h2{margin-bottom:0;}
.qr-btn{font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:500;letter-spacing:0.08em;color:#8a6a34;background:transparent;border:1.5px solid #8a6a34;border-radius:8px;padding:8px 16px;cursor:pointer;flex-shrink:0;min-height:38px;transition:background 0.15s,color 0.15s;-webkit-tap-highlight-color:transparent;}
.qr-btn:hover{background:#8a6a34;color:#faf5ea;}
.qr-overlay{display:none;position:fixed;inset:0;background:rgba(47,42,34,0.55);z-index:100;align-items:center;justify-content:center;padding:24px;}
.qr-overlay.show{display:flex;}
.qr-card{background:#faf5ea;border:1px solid rgba(62,52,38,0.2);border-radius:14px;padding:24px 24px 18px;text-align:center;max-width:320px;width:100%;box-shadow:0 12px 40px rgba(47,42,34,0.35);}
.qr-card svg{width:100%;max-width:240px;height:auto;display:block;margin:0 auto;}
.qr-url{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#7c7465;margin-top:14px;word-break:break-all;}
.qr-hint{font-size:13px;color:#2f2a22;margin-top:6px;font-style:italic;}
""".strip()

def sidebar_html():
    out = []
    for sname, books in sets.items():
        out.append('<div class="set-section"><div class="set-label" onclick="this.classList.toggle(\'open\');this.nextElementSibling.classList.toggle(\'open\')">%s <span class="arrow">▶</span></div><div class="set-list">' % html.escape(sname))
        for bname, entries in books.items():
            out.append('<div class="book-section"><div class="book-label" onclick="this.classList.toggle(\'open\');this.nextElementSibling.classList.toggle(\'open\')">— %s <span class="arrow">▶</span></div><div class="chapter-list">' % html.escape(bname))
            for e in entries:
                out.append('<a class="chapter-item" href="%s">%s</a>' % (html.escape(e['file']), html.escape(e['chapter'])))
            out.append('</div></div>')
        out.append('</div></div>')
    return ''.join(out)

def main_html():
    out = []
    for sname, books in sets.items():
        out.append('<div class="set-group"><div class="set-group-title">%s</div>' % html.escape(sname))
        for bname, entries in books.items():
            out.append('<div class="book-group"><div class="book-group-title">%s</div><div class="chapter-grid">' % html.escape(bname))
            for e in entries:
                out.append('<a class="chapter-card" href="%s"><div class="play-icon">▶</div><div class="card-text"><div class="card-chapter">%s</div><div class="card-book">%s<span class="card-duration">%s</span></div></div></a>'
                           % (html.escape(e['file']), html.escape(e['chapter']), html.escape(bname), fmt(e.get('duration'))))
            out.append('</div></div>')
        out.append('</div>')
    return ''.join(out)

page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<title>Scripture Reader</title>
<style>
%s
</style>
</head>
<body>
<div class="layout">
  <nav class="sidebar">
    <div class="sidebar-header"><div class="app-title">Scripture Reader</div><div class="app-sub">Audio · Text · Sync</div></div>
    <div class="book-nav">%s</div>
  </nav>
  <main class="main">
    <div class="welcome"><div class="welcome-row"><h2>Library</h2><button class="qr-btn" id="qr-btn" aria-label="Show QR code to share this site" onclick="document.getElementById('qr-overlay').classList.add('show')">QR</button></div><p>Select a scripture set, book, and chapter to begin listening and reading along.</p></div>
    <div class="section-title">Scripture Library</div>
    <div>%s</div>
  </main>
</div>
<div class="qr-overlay" id="qr-overlay" role="dialog" aria-label="QR code for this site" onclick="this.classList.remove('show')">
  <div class="qr-card" onclick="event.stopPropagation()">
    <svg viewBox="-2 -2 33 33" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg"><rect x="-2" y="-2" width="33" height="33" fill="#ffffff"/><path fill="#1a1712" d="%s"/></svg>
    <div class="qr-url">bom-reader.netlify.app</div>
    <div class="qr-hint">Scan to open the Scripture Reader</div>
  </div>
</div>
<script>
(function(){
  document.addEventListener('keydown',function(e){if(e.key==='Escape')document.getElementById('qr-overlay').classList.remove('show');});
  document.querySelectorAll('.set-group-title,.book-group-title').forEach(function(t){
    var a=document.createElement('span');a.className='g-arrow';a.textContent='▶';
    t.appendChild(a);
    t.addEventListener('click',function(){t.parentElement.classList.toggle('open');});
  });
  var mobile=window.matchMedia('(max-width: 640px)').matches;
  document.querySelectorAll('.set-group').forEach(function(g){g.classList.add('open');});
  if(!mobile){document.querySelectorAll('.book-group').forEach(function(g){g.classList.add('open');});}
})();
</script>
</body>
</html>
""" % (STYLE, sidebar_html(), main_html(), QR_PATH)

out = os.path.join(SITE, 'index.html')
open(out, 'w', encoding='utf-8', newline='\n').write(page)
print('Wrote', out, len(page), 'bytes,', len(lib), 'chapters,', sum(len(b) for b in sets.values()), 'books')
