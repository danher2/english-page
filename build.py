"""Builds index.html from frases.md.

Usage:  python build.py
Edit frases.md, run this script, then commit and push both files.
"""
import html
import io
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
MD = (ROOT / "frases.md").read_text(encoding="utf-8")


def slug(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t.lower()).strip("-")
    return t or "section"


def inline(text):
    t = text.replace("\\_", "\x00")
    t = html.escape(t, quote=False)
    t = re.sub(r"\x00{3,}", '<span class="blank">___</span>', t)
    t = t.replace("\x00", "_")
    t = re.sub(r"~~(.+?)~~", r"<s>\1</s>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(?!\s)(.+?)\*", r"<em>\1</em>", t)
    return t


def plain(text):
    return re.sub(r"<[^>]+>", "", inline(text)).replace("&#x27;", "'")


def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


SPEAK = ('<button class="say" type="button" aria-label="Listen" title="Listen">'
         '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4zm12.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z"/></svg></button>')


def en_cell(text):
    return f'<span class="en" data-say="{html.escape(plain(text))}">{inline(text)}</span>{SPEAK}'


def render_table(header, rows):
    h = [c.lower() for c in header]
    if h == ["english", "spanish"]:
        items = "".join(
            f'<li class="item phrase"><div class="en-wrap">{en_cell(r[0])}</div>'
            f'<div class="es">{inline(r[1])}</div></li>' for r in rows)
        return f'<ul class="phrases">{items}</ul>', len(rows)
    if h == ["simple", "perfect", "spanish"]:
        out = []
        for r in rows:
            es = [s.strip() for s in r[2].split(" / ")]
            es1, es2 = (es[0], es[1]) if len(es) == 2 else (r[2], "")
            out.append(
                '<li class="item pair">'
                f'<div class="half"><span class="tag">Simple</span><div class="en-wrap">{en_cell(r[0])}</div>'
                f'<div class="es">{inline(es1)}</div></div>'
                f'<div class="half"><span class="tag perf">Perfect</span><div class="en-wrap">{en_cell(r[1])}</div>'
                f'<div class="es">{inline(es2)}</div></div></li>')
        return f'<ul class="pairs">{"".join(out)}</ul>', len(rows)
    drill = h == ["form", "simple", "perfect"]
    th = "".join(f"<th>{inline(c)}</th>" for c in header)
    body = []
    for r in rows:
        tds = []
        for i, c in enumerate(r):
            if drill and i > 0:
                tds.append(f'<td><span class="en">{inline(c)}</span></td>')
            elif drill:
                tds.append(f'<td class="label">{inline(c)}</td>')
            else:
                tds.append(f"<td>{inline(c)}</td>")
        body.append(f'<tr class="item">{"".join(tds)}</tr>')
    cls = "grid drill" if drill else "grid"
    return (f'<div class="table-wrap"><table class="{cls}"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>'), 0


# ---------- parse markdown into blocks ----------
lines = MD.split("\n")
title, updated = "", ""
sections = []          # [{id, title, html:[...], count, subs:[(id,title)]}]
intro = []
cur = None
i = 0


def emit(s):
    (cur["html"] if cur else intro).append(s)


while i < len(lines):
    ln = lines[i]
    if ln.startswith("# "):
        title = ln[2:].strip()
    elif ln.startswith("Updated:"):
        updated = ln.strip()
    elif ln.startswith("## "):
        t = ln[3:].strip()
        cur = {"id": slug(t), "title": t, "html": [], "count": 0, "subs": []}
        sections.append(cur)
    elif ln.startswith("### "):
        t = ln[4:].strip()
        sid = cur["id"] + "--" + slug(t)
        cur["subs"].append((sid, t))
        emit(f'<h3 id="{sid}">{inline(t)}</h3>')
    elif ln.startswith("| "):
        header = cells(ln)
        i += 2
        rows = []
        while i < len(lines) and lines[i].startswith("| "):
            r = cells(lines[i])
            rows.append(r + [""] * (len(header) - len(r)))
            i += 1
        block, n = render_table(header, rows)
        cur["count"] += n
        emit(block)
        continue
    elif re.match(r"^\d+\. ", ln):
        items = []
        while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
            items.append(f"<li>{inline(re.sub(r'^\d+\. ', '', lines[i]))}</li>")
            i += 1
        emit(f'<ol class="steps">{"".join(items)}</ol>')
        continue
    elif ln.startswith("- "):
        items = []
        while i < len(lines) and lines[i].startswith("- "):
            items.append(f"<li>{inline(lines[i][2:])}</li>")
            i += 1
        emit(f'<ul class="bullets">{"".join(items)}</ul>')
        continue
    elif ln.strip():
        txt = ln.strip()
        cls = ""
        if txt.startswith(("Tip:", "Exception:", "Careful:")) or txt.startswith("**Corrections") \
                or txt.startswith("**How to flip"):
            cls = ' class="note"'
        elif txt.startswith("**Full drill"):
            cls = ' class="drill-title"'
        emit(f"<p{cls}>{inline(txt)}</p>")
    i += 1

total = sum(s["count"] for s in sections)

# ---------- assemble page ----------
toc = []
for n, s in enumerate(sections, 1):
    badge = f'<span class="count">{s["count"]}</span>' if s["count"] else ""
    toc.append(f'<li><a href="#{s["id"]}"><span class="num">{n:02d}</span>'
               f'<span class="t">{inline(s["title"])}</span>{badge}</a></li>')

body = []
for n, s in enumerate(sections, 1):
    meta = f'<span class="count-pill">{s["count"]} phrases</span>' if s["count"] else ""
    body.append(
        f'<section class="card" id="{s["id"]}">'
        f'<header class="card-head"><span class="num">{n:02d}</span>'
        f'<h2>{inline(s["title"])}</h2>{meta}</header>'
        f'{"".join(s["html"])}</section>')

CSS = r"""
:root{
  --bg:#f6f7fb;--surface:#fff;--surface-2:#f1f3f9;--fg:#1a1d29;--muted:#5d6478;--line:#e3e6ef;
  --accent:#4f46e5;--accent-soft:#eef0ff;--accent-2:#0e9f6e;--accent-2-soft:#e6f7f0;
  --es:#7a4b00;--blank-bg:#fff4d6;--blank-fg:#8a5a00;--shadow:0 1px 2px rgba(20,24,40,.04),0 4px 16px rgba(20,24,40,.06);
  --radius:16px;
}
:root[data-theme=dark]{
  --bg:#0f1117;--surface:#171a23;--surface-2:#1e2230;--fg:#e8eaf2;--muted:#9aa1b5;--line:#2a2f3e;
  --accent:#8b85ff;--accent-soft:#25244a;--accent-2:#3ccf98;--accent-2-soft:#14332a;
  --es:#f0c27a;--blank-bg:#3a2f12;--blank-fg:#f5cf7a;--shadow:0 1px 2px rgba(0,0,0,.3),0 4px 16px rgba(0,0,0,.25);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:84px}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
strong{font-weight:650}
.hero{background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 55%,#db2777 100%);color:#fff;padding:56px 20px 88px}
.hero-in{max-width:1180px;margin:0 auto}
.hero .eyebrow{display:inline-block;font-size:13px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;background:rgba(255,255,255,.16);padding:5px 12px;border-radius:999px}
.hero h1{font-size:clamp(30px,5vw,48px);line-height:1.1;margin:16px 0 10px;letter-spacing:-.02em}
.hero p{margin:0;opacity:.9;max-width:640px;font-size:17px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-top:22px}
.stat{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);padding:10px 16px;border-radius:12px;font-size:14px}
.stat b{display:block;font-size:22px;line-height:1.2}
.toolbar{position:sticky;top:0;z-index:20;margin:-56px auto 0;max-width:1180px;padding:0 20px}
.toolbar-in{display:flex;gap:10px;align-items:center;flex-wrap:wrap;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:10px;box-shadow:var(--shadow);backdrop-filter:saturate(1.4) blur(8px)}
.search{flex:1 1 260px;position:relative}
.search svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);width:18px;height:18px;fill:var(--muted)}
.search input{width:100%;font:inherit;font-size:15px;padding:10px 12px 10px 38px;border:1px solid var(--line);border-radius:10px;background:var(--surface-2);color:var(--fg);outline:none}
.search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.btn{font:inherit;font-size:14px;font-weight:600;padding:9px 14px;border-radius:10px;border:1px solid var(--line);background:var(--surface);color:var(--fg);cursor:pointer;display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.btn:hover{background:var(--surface-2)}
.btn[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.icon{padding:9px 11px}
.btn svg{width:18px;height:18px;fill:currentColor}
#toc-btn{display:none}
.result{font-size:13px;color:var(--muted);width:100%;padding:2px 4px 0;display:none}
.result.on{display:block}
.layout{max-width:1180px;margin:24px auto 80px;padding:0 20px;display:grid;grid-template-columns:270px 1fr;gap:28px;align-items:start}
nav.toc{position:sticky;top:96px;max-height:calc(100vh - 116px);overflow:auto;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:10px;box-shadow:var(--shadow)}
.toc h4{margin:6px 10px 8px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.toc ol{list-style:none;margin:0;padding:0}
.toc a{display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:9px;color:var(--fg);font-size:14px;line-height:1.3}
.toc a:hover{background:var(--surface-2)}
.toc a.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.toc .num{font-size:11px;font-weight:700;color:var(--muted);font-variant-numeric:tabular-nums}
.toc a.active .num{color:var(--accent)}
.toc .t{flex:1}
.toc .count{font-size:11px;color:var(--muted);background:var(--surface-2);padding:1px 7px;border-radius:999px}
main{min-width:0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:26px 28px;margin-bottom:22px;box-shadow:var(--shadow)}
.card-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:6px}
.card-head .num{font-size:13px;font-weight:800;color:var(--accent);background:var(--accent-soft);border-radius:8px;padding:4px 8px;font-variant-numeric:tabular-nums}
.card-head h2{margin:0;font-size:22px;letter-spacing:-.01em;flex:1;min-width:200px}
.count-pill{font-size:12px;font-weight:600;color:var(--muted);border:1px solid var(--line);padding:3px 10px;border-radius:999px}
.card>p{color:var(--muted);margin:8px 0 14px}
.card h3{font-size:17px;margin:28px 0 10px;padding-top:18px;border-top:1px dashed var(--line)}
.card h3:first-of-type{border-top:0;padding-top:0}
p.note{background:var(--accent-soft);color:var(--fg);border-left:4px solid var(--accent);padding:12px 16px;border-radius:0 10px 10px 0}
p.drill-title{color:var(--fg);margin-top:22px;font-size:15px}
ol.steps{counter-reset:s;list-style:none;padding:0;margin:12px 0}
ol.steps li{counter-increment:s;position:relative;padding:10px 12px 10px 48px;border-radius:10px;margin-bottom:6px;background:var(--surface-2)}
ol.steps li::before{content:counter(s);position:absolute;left:12px;top:10px;width:26px;height:26px;border-radius:50%;background:var(--accent);color:#fff;font-size:13px;font-weight:700;display:grid;place-items:center}
ul.bullets{padding-left:20px}
ul.bullets li{margin:6px 0}
s{color:var(--muted)}
.blank{display:inline-block;min-width:34px;text-align:center;background:var(--blank-bg);color:var(--blank-fg);border-radius:6px;padding:0 6px;font-weight:700;letter-spacing:.05em;line-height:1.45}
ul.phrases,ul.pairs{list-style:none;margin:10px 0 0;padding:0}
.phrase{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:center;padding:12px 14px;border-radius:12px;border:1px solid transparent}
.phrase:nth-child(odd){background:var(--surface-2)}
.phrase:hover{border-color:var(--line)}
.en-wrap{display:flex;align-items:flex-start;gap:8px}
.en{font-weight:600;font-size:16.5px}
.es{color:var(--es);font-size:15.5px}
.say{flex:none;border:0;background:transparent;color:var(--muted);cursor:pointer;width:28px;height:28px;border-radius:8px;display:grid;place-items:center;margin-top:-2px;opacity:.55}
.say:hover,.say.on{opacity:1;color:var(--accent);background:var(--accent-soft)}
.say svg{width:17px;height:17px;fill:currentColor}
.pair{display:grid;grid-template-columns:1fr 1fr;margin-bottom:12px;background:var(--surface-2);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.half{padding:12px 16px}
.half+.half{border-left:1px solid var(--line)}
.tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);background:var(--accent-soft);padding:2px 8px;border-radius:6px;margin-bottom:6px}
.tag.perf{color:var(--accent-2);background:var(--accent-2-soft)}
.half .es{margin-top:4px}
.table-wrap{overflow-x:auto;margin:12px 0;border:1px solid var(--line);border-radius:12px}
table.grid{border-collapse:collapse;width:100%;font-size:15px}
.grid th{background:var(--surface-2);text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:10px 14px;white-space:nowrap}
.grid td{padding:10px 14px;border-top:1px solid var(--line);vertical-align:top}
.grid td.label{font-weight:600;color:var(--muted);white-space:nowrap}
.grid .en{font-weight:500;font-size:15px}
body.hide-en .en,body.hide-es .es{background:var(--surface-2);color:transparent!important;border-radius:6px;cursor:pointer;user-select:none;filter:blur(0);box-shadow:inset 0 0 0 1px var(--line)}
body.hide-en .en *,body.hide-es .es *{color:transparent!important;background:transparent!important}
body.hide-en .en.show,body.hide-es .es.show{color:inherit!important;background:transparent;box-shadow:none;cursor:auto}
body.hide-en .en.show *,body.hide-es .es.show *{color:inherit!important}
body.hide-es .es.show{color:var(--es)!important}
body.hide-en .en.show .blank,body.hide-es .es.show .blank{background:var(--blank-bg)!important;color:var(--blank-fg)!important}
body.hide-en .es.es{color:var(--es)}
.item.miss,.card.miss,.card h3.miss,.miss{display:none!important}
mark{background:#ffe58a;color:#1a1d29;border-radius:3px;padding:0 1px}
.empty{display:none;text-align:center;color:var(--muted);padding:40px}
.empty.on{display:block}
#top{position:fixed;right:20px;bottom:20px;width:46px;height:46px;border-radius:50%;border:0;background:var(--accent);color:#fff;box-shadow:var(--shadow);cursor:pointer;opacity:0;pointer-events:none;transition:opacity .2s;display:grid;place-items:center;z-index:30}
#top.on{opacity:1;pointer-events:auto}
#top svg{width:22px;height:22px;fill:currentColor}
.scrim{display:none}
footer{text-align:center;color:var(--muted);font-size:13px;padding:0 20px 40px}
@media (max-width:900px){
  .layout{grid-template-columns:minmax(0,1fr)}
  #toc-btn{display:inline-flex}
  nav.toc{position:fixed;top:0;left:0;bottom:0;width:min(320px,86vw);max-height:none;border-radius:0 var(--radius) var(--radius) 0;z-index:50;transform:translateX(-105%);transition:transform .25s}
  nav.toc.open{transform:none}
  .scrim.open{display:block;position:fixed;inset:0;background:rgba(10,12,20,.45);z-index:40}
}
@media (max-width:640px){
  .hero{padding:40px 16px 80px}
  .toolbar{padding:0 10px}
  .layout{padding:0 10px}
  .card{padding:20px 16px}
  .phrase{grid-template-columns:1fr;gap:4px}
  .pair{grid-template-columns:1fr}
  .half+.half{border-left:0;border-top:1px dashed var(--line)}
  .btn .lbl{display:none}
}
@media print{.toolbar,nav.toc,#top,.say{display:none!important}.layout{display:block}.hero{color:#000;background:none}}
"""

JS = r"""
(function(){
  var root=document.documentElement,b=document.body;
  var saved=localStorage.getItem('theme');
  if(!saved){saved=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}
  root.dataset.theme=saved;
  document.getElementById('theme').onclick=function(){
    var t=root.dataset.theme==='dark'?'light':'dark';root.dataset.theme=t;localStorage.setItem('theme',t)};
  // hide toggles
  function bindHide(id,cls){var el=document.getElementById(id);
    if(localStorage.getItem(cls)==='1'){b.classList.add(cls);el.setAttribute('aria-pressed','true')}
    el.onclick=function(){var on=b.classList.toggle(cls);el.setAttribute('aria-pressed',on);
      localStorage.setItem(cls,on?'1':'0');
      document.querySelectorAll('.show').forEach(function(x){x.classList.remove('show')})}}
  bindHide('hide-en','hide-en');bindHide('hide-es','hide-es');
  document.addEventListener('click',function(e){
    var t=e.target.closest('.en,.es');
    if(t&&((b.classList.contains('hide-en')&&t.classList.contains('en'))||(b.classList.contains('hide-es')&&t.classList.contains('es'))))t.classList.toggle('show');
    var s=e.target.closest('.say');
    if(s){speak(s.parentNode.querySelector('.en').dataset.say,s)}
  });
  // speech
  var voice=null;
  function pick(){var v=speechSynthesis.getVoices().filter(function(x){return /^en[-_]US/i.test(x.lang)});
    voice=v.find(function(x){return /natural|google|samantha|aria|jenny/i.test(x.name)})||v[0]||null}
  if('speechSynthesis' in window){pick();speechSynthesis.onvoiceschanged=pick}
  else document.querySelectorAll('.say').forEach(function(x){x.remove()});
  function speak(text,btn){
    speechSynthesis.cancel();
    var u=new SpeechSynthesisUtterance(text.replace(/_{3,}/g,'something'));
    u.lang='en-US';u.rate=.92;if(voice)u.voice=voice;
    btn.classList.add('on');u.onend=u.onerror=function(){btn.classList.remove('on')};
    speechSynthesis.speak(u)}
  // search
  var q=document.getElementById('q'),res=document.getElementById('result'),empty=document.getElementById('empty');
  var items=[].slice.call(document.querySelectorAll('.item'));
  items.forEach(function(it){it._html=it.innerHTML;it._text=norm(it.textContent)});
  function norm(s){return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'')}
  function esc(s){return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
  var timer;q.addEventListener('input',function(){clearTimeout(timer);timer=setTimeout(run,120)});
  function run(){
    var term=norm(q.value.trim()),hits=0;
    items.forEach(function(it){
      it.innerHTML=it._html;
      var ok=!term||it._text.indexOf(term)>-1;
      it.classList.toggle('miss',!ok);
      if(ok&&term){hits++;highlight(it,term)}
    });
    document.querySelectorAll('.card').forEach(function(c){
      var has=!term||c.querySelector('.item:not(.miss)');
      c.classList.toggle('miss',!has);
      c.querySelectorAll('.table-wrap,ul.phrases,ul.pairs').forEach(function(w){
        w.classList.toggle('miss',!!term&&!w.querySelector('.item:not(.miss)'))});
      c.querySelectorAll(':scope>p,:scope>ol,:scope>ul.bullets,:scope>h3').forEach(function(p){p.classList.toggle('miss',!!term)});
    });
    res.classList.toggle('on',!!term);
    res.textContent=term?(hits+(hits===1?' match':' matches')+' for “'+q.value.trim()+'”'):'';
    empty.classList.toggle('on',!!term&&!hits);
  }
  function highlight(el,term){
    var re=new RegExp(esc(term).split('').join('[\\u0300-\\u036f]*'),'gi');
    var w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),nodes=[],n;
    while(n=w.nextNode())nodes.push(n);
    nodes.forEach(function(t){
      var src=t.nodeValue,low=norm(src),i=low.indexOf(term);if(i<0)return;
      var f=document.createDocumentFragment(),last=0;
      while(i>-1){f.appendChild(document.createTextNode(src.slice(last,i)));
        var m=document.createElement('mark');m.textContent=src.slice(i,i+term.length);f.appendChild(m);
        last=i+term.length;i=low.indexOf(term,last)}
      f.appendChild(document.createTextNode(src.slice(last)));t.parentNode.replaceChild(f,t)})
  }
  document.addEventListener('keydown',function(e){
    if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus()}
    if(e.key==='Escape'&&document.activeElement===q){q.value='';run();q.blur()}});
  // toc drawer + scrollspy
  var toc=document.querySelector('nav.toc'),scrim=document.querySelector('.scrim');
  function drawer(o){toc.classList.toggle('open',o);scrim.classList.toggle('open',o)}
  document.getElementById('toc-btn').onclick=function(){drawer(true)};
  scrim.onclick=function(){drawer(false)};
  toc.addEventListener('click',function(e){if(e.target.closest('a'))drawer(false)});
  var links={};toc.querySelectorAll('a').forEach(function(a){links[a.getAttribute('href').slice(1)]=a});
  var io=new IntersectionObserver(function(es){es.forEach(function(e){
    if(e.isIntersecting){toc.querySelectorAll('a.active').forEach(function(a){a.classList.remove('active')});
      var a=links[e.target.id];if(a){a.classList.add('active');
        if(innerWidth>900)a.scrollIntoView({block:'nearest'})}}})},{rootMargin:'-90px 0px -70% 0px'});
  document.querySelectorAll('section.card').forEach(function(s){io.observe(s)});
  var top=document.getElementById('top');
  addEventListener('scroll',function(){top.classList.toggle('on',scrollY>600)},{passive:true});
  top.onclick=function(){scrollTo({top:0,behavior:'smooth'})};
})();
"""

ICON_SEARCH = '<svg viewBox="0 0 24 24"><path d="M10 2a8 8 0 0 1 6.3 12.9l5.4 5.4-1.4 1.4-5.4-5.4A8 8 0 1 1 10 2zm0 2a6 6 0 1 0 0 12 6 6 0 0 0 0-12z"/></svg>'
ICON_MENU = '<svg viewBox="0 0 24 24"><path d="M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z"/></svg>'
ICON_EYE = '<svg viewBox="0 0 24 24"><path d="M12 5c5 0 9 4.5 10 7-1 2.5-5 7-10 7S3 14.5 2 12c1-2.5 5-7 10-7zm0 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"/></svg>'
ICON_MOON = '<svg viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
ICON_UP = '<svg viewBox="0 0 24 24"><path d="M12 5l7 7-1.4 1.4L13 8.8V20h-2V8.8l-4.6 4.6L5 12z"/></svg>'


DICT_CSS = r"""
.dict{position:fixed;inset:0;z-index:60;background:rgba(10,12,20,.55);display:none;align-items:flex-start;justify-content:center;padding:5vh 16px 16px}
.dict.open{display:flex}
body.dict-open{overflow:hidden}
.dict-box{width:min(780px,100%);max-height:90vh;display:flex;flex-direction:column;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);box-shadow:0 20px 60px rgba(0,0,0,.35);overflow:hidden}
.dict-top{padding:14px 14px 10px;border-bottom:1px solid var(--line);background:var(--surface)}
.dict-title{display:flex;align-items:center;gap:10px;margin:0 2px 10px}
.dict-title h2{margin:0;font-size:18px;flex:1;display:flex;align-items:center;gap:8px}
.dict-title h2 svg{width:20px;height:20px;fill:var(--accent)}
.dform{display:flex;gap:8px;flex-wrap:wrap}
.dform .search{flex:1 1 220px}
#ddir{min-width:96px;justify-content:center}
.dhist{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;align-items:center}
.dhist:empty{display:none}
.dhist .lab{font-size:12px;color:var(--muted);margin-right:2px}
.dchip{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--surface-2);color:var(--fg);padding:3px 10px;border-radius:999px;cursor:pointer}
.dchip:hover{border-color:var(--accent);color:var(--accent)}
.dout{overflow:auto;padding:18px 20px 26px;flex:1}
.dempty{color:var(--muted);text-align:center;padding:26px 10px}
.dempty p{margin:6px 0}
.dload{color:var(--muted);padding:6px 0}
.dhead{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap;padding-bottom:14px;border-bottom:1px solid var(--line)}
.dword{margin:0;font-size:30px;letter-spacing:-.01em;line-height:1.15}
.dfrom{font-size:13px;color:var(--muted);margin-top:2px}
.dphon{color:var(--muted);font-size:16px;margin-top:4px;font-family:"Lucida Sans Unicode","Segoe UI",Arial,sans-serif}
.daudio{display:flex;gap:6px;flex-wrap:wrap}
.dplay{font:inherit;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--surface-2);color:var(--fg);padding:6px 11px;border-radius:999px;cursor:pointer}
.dplay svg{width:15px;height:15px;fill:currentColor}
.dplay:hover,.dplay.on{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.dsec{margin-top:18px}
.dsec h4{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.des-main{font-size:22px;font-weight:650;color:var(--es)}
.des-alt{margin-top:4px;color:var(--muted);font-size:14px}
.dpos{margin:10px 0 4px;font-size:13px;font-weight:700;color:var(--accent);font-style:italic}
.ddefs{margin:0;padding-left:22px}
.ddefs li{margin:5px 0}
.dsyns{display:flex;gap:6px;flex-wrap:wrap}
.dsyns .dchip{background:var(--accent-soft);border-color:transparent;color:var(--accent);font-weight:600}
.dex{list-style:none;margin:0;padding:0}
.dex li{display:flex;gap:8px;align-items:flex-start;padding:9px 12px;border-radius:10px;background:var(--surface-2);margin-bottom:6px}
.dex .txt{flex:1}
.dex .tr{display:block;color:var(--es);font-size:14px;margin-top:3px}
.dex .src{display:block;color:var(--muted);font-size:12px;margin-top:2px}
.dsay,.dtr{flex:none;border:0;background:transparent;color:var(--muted);cursor:pointer;height:28px;min-width:28px;border-radius:8px;display:grid;place-items:center;font:inherit;font-size:12px;font-weight:600}
.dsay svg{width:17px;height:17px;fill:currentColor}
.dsay:hover,.dsay.on,.dtr:hover{color:var(--accent);background:var(--accent-soft)}
.dnote{color:var(--muted);font-size:14px}
.dlinks{margin-top:22px;padding-top:14px;border-top:1px solid var(--line);font-size:14px;color:var(--muted)}
.dlinks a{margin-right:12px}
@media (max-width:640px){
  .dict{padding:0}
  .dict-box{max-height:none;height:100%;height:100dvh;border-radius:0;border:0}
  .dword{font-size:26px}
  .dform .btn{flex:1 1 0;justify-content:center}
}
"""

DICT_JS = r"""
(function(){
  var dlg=document.getElementById('dict'),inp=document.getElementById('dq'),out=document.getElementById('dout'),
      form=document.getElementById('dform'),dirBtn=document.getElementById('ddir'),histEl=document.getElementById('dhist');
  var SPK='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4zm12.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z"/></svg>';
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function lc(s){return String(s).toLowerCase().trim()}
  function store(k,v){try{if(v===undefined)return localStorage.getItem(k);localStorage.setItem(k,v)}catch(e){return null}}

  // ---- direction EN->ES / ES->EN ----
  var dir=store('dictDir')||'en';
  function setDir(d){dir=d;store('dictDir',d);dirBtn.textContent=d==='en'?'EN → ES':'ES → EN';
    dirBtn.title=d==='en'?'Searching an English word':'Searching a Spanish word';
    inp.placeholder=d==='en'?'Type an English word or phrase…':'Type a Spanish word (e.g. presupuesto)…'}
  setDir(dir);
  dirBtn.onclick=function(){setDir(dir==='en'?'es':'en');inp.focus()};

  // ---- open / close ----
  function open(term){dlg.classList.add('open');document.body.classList.add('dict-open');renderHist();
    if(term){inp.value=term;lookup(term)}else if(!out.dataset.used)empty();
    setTimeout(function(){inp.focus();inp.select()},60)}
  function close(){dlg.classList.remove('open');document.body.classList.remove('dict-open');
    if(location.hash.indexOf('#dict')===0)history.replaceState(null,'',location.pathname+location.search);
    try{speechSynthesis.cancel()}catch(e){}}
  document.getElementById('dict-btn').onclick=function(){open()};
  document.getElementById('dclose').onclick=close;
  dlg.addEventListener('click',function(e){if(e.target===dlg)close()});
  document.addEventListener('keydown',function(e){
    if(dlg.classList.contains('open')){e.stopPropagation();if(e.key==='Escape')close();return}
    var tag=(document.activeElement||{}).tagName;
    if(e.key==='d'&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&tag!=='INPUT'&&tag!=='TEXTAREA'){e.preventDefault();open()}
  },true);
  // double-click any word on the page to look it up
  document.querySelector('main').addEventListener('dblclick',function(){
    var s=String(window.getSelection()||'').trim().replace(/[^\w' -]+$/,'').replace(/^[^\w']+/,'');
    if(s&&s.length<40){if(dir!=='en')setDir('en');open(s)}});
  form.onsubmit=function(e){e.preventDefault();var t=inp.value.trim();if(t)lookup(t)};

  // ---- history ----
  function getHist(){try{return JSON.parse(store('dictHist')||'[]')}catch(e){return []}}
  function addHist(t){var h=getHist().filter(function(x){return lc(x)!==lc(t)});h.unshift(t);store('dictHist',JSON.stringify(h.slice(0,12)));renderHist()}
  function renderHist(){var h=getHist();histEl.innerHTML=h.length?'<span class="lab">Recent:</span>'+h.map(function(x){
    return '<button type="button" class="dchip" data-look="'+esc(x)+'">'+esc(x)+'</button>'}).join(''):''}
  histEl.addEventListener('click',function(e){var b=e.target.closest('[data-look]');if(b){if(dir!=='en')setDir('en');inp.value=b.dataset.look;lookup(b.dataset.look)}});

  function empty(){out.innerHTML='<div class="dempty"><p><b>Look up any English word or phrase.</b></p>'+
    '<p>You get the Spanish meaning, an English explanation, synonyms, examples and pronunciation.</p>'+
    '<p style="margin-top:14px">Try: '+['deadline','bandwidth','take over','reliable','follow up'].map(function(w){
      return '<button type="button" class="dchip" data-look="'+w+'">'+w+'</button>'}).join(' ')+'</p>'+
    '<p style="margin-top:14px;font-size:13px">Tip: press <b>d</b> to open the dictionary, or double-click a word on the page (on a computer).</p></div>'}

  // ---- network helpers ----
  function get(url){var c=('AbortController' in window)?new AbortController():null,t=setTimeout(function(){c&&c.abort()},10000);
    return fetch(url,c?{signal:c.signal}:{}).then(function(r){clearTimeout(t);if(!r.ok){var er=new Error('http');er.status=r.status;throw er}return r.json()})}
  // MyMemory mixes machine translation with a public, crowd-edited memory that
  // contains junk for single words ("hello" -> "testvalue"). Prefer the
  // machine-translation match ("created-by": "MT!") and show no extra options.
  function translate(text,pair){
    var ck='tr2:'+pair+':'+lc(text),hit=store(ck);
    if(hit){try{return Promise.resolve(JSON.parse(hit))}catch(e){}}
    return get('https://api.mymemory.translated.net/get?q='+encodeURIComponent(text)+'&langpair='+pair).then(function(d){
      var main=((d.responseData||{}).translatedText||'').trim();
      if(String(d.responseStatus)!=='200'||!main||/MYMEMORY WARNING|QUERY LENGTH LIMIT/i.test(main))throw new Error('quota');
      // vote: every match counts, machine translation counts extra, one-off junk loses
      var votes={},best=null;
      function add(t,w){t=String(t||'').trim();if(!t||t.length>80)return;
        var k=lc(t).replace(/^[¡¿"']+|[.!?"']+$/g,'');if(!k||k===lc(text))return;
        var v=votes[k]||(votes[k]={t:t,s:0});v.s+=w;if(!best||v.s>best.s)best=v}
      add(main,1);
      (d.matches||[]).forEach(function(m){var q=parseFloat(m.match)||0.5,u=Math.min(parseInt(m['usage-count'],10)||0,5);
        add(m.translation,q+u*0.1+(/^MT/i.test(String(m['created-by']||''))?1.5:0))});
      if(best)main=best.t;
      var t=document.createElement('textarea');t.innerHTML=main;main=t.value;
      var r={main:main,alts:[]};store(ck,JSON.stringify(r));return r})}

  // ---- speech ----
  var voice=null;
  function pick(){try{var v=speechSynthesis.getVoices().filter(function(x){return /^en[-_]US/i.test(x.lang)});
    voice=v.find(function(x){return /natural|google|samantha|aria|jenny/i.test(x.name)})||v[0]||null}catch(e){}}
  if('speechSynthesis' in window){pick();speechSynthesis.addEventListener&&speechSynthesis.addEventListener('voiceschanged',pick)}
  var audio=null;
  function say(text,rate,btn){
    if(audio){audio.pause();audio=null}
    if(!('speechSynthesis' in window))return;
    speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(String(text).replace(/_{3,}/g,'something'));u.lang='en-US';u.rate=rate||.92;if(voice)u.voice=voice;
    if(btn){btn.classList.add('on');u.onend=u.onerror=function(){btn.classList.remove('on')}}
    speechSynthesis.speak(u)}
  function playUrl(url,btn){try{speechSynthesis.cancel()}catch(e){}if(audio)audio.pause();
    audio=new Audio(url);btn.classList.add('on');audio.onended=audio.onerror=function(){btn.classList.remove('on')};
    audio.play().catch(function(){btn.classList.remove('on')})}

  out.addEventListener('click',function(e){
    var b=e.target.closest('button');if(!b)return;
    if(b.dataset.say!=null)say(b.dataset.say,parseFloat(b.dataset.rate||'.92'),b);
    else if(b.dataset.url)playUrl(b.dataset.url,b);
    else if(b.dataset.look){if(dir!=='en')setDir('en');inp.value=b.dataset.look;lookup(b.dataset.look);out.scrollTop=0}
    else if(b.dataset.tr!=null){var li=b.closest('li'),slot=li.querySelector('.tr');b.disabled=true;b.textContent='…';
      translate(b.dataset.tr,'en|es').then(function(r){slot.textContent=r.main;b.remove()})
        .catch(function(){b.textContent='ES';b.disabled=false;slot.textContent='Translation limit reached for today.'})}
  });

  // ---- phrases from this page that contain the word ----
  function fromList(term){
    var re;try{re=new RegExp('(^|[^a-z])'+term.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'([^a-z]|$)','i')}catch(e){return []}
    var seen={},res=[];
    document.querySelectorAll('main .en[data-say]').forEach(function(el){
      var t=el.dataset.say;if(seen[t]||!re.test(t))return;seen[t]=1;
      var box=el.closest('.phrase,.half'),es=box&&box.querySelector('.es');
      res.push({en:t,es:es?es.textContent.trim():''})});
    return res.slice(0,8)}

  function exItem(text,es,src,canTr){
    return '<li><button type="button" class="dsay" data-say="'+esc(text)+'" aria-label="Listen" title="Listen">'+SPK+'</button>'+
      '<span class="txt">'+esc(text)+'<span class="tr">'+esc(es||'')+'</span>'+(src?'<span class="src">'+esc(src)+'</span>':'')+'</span>'+
      (canTr?'<button type="button" class="dtr" data-tr="'+esc(text)+'" title="Translate to Spanish">ES</button>':'')+'</li>'}

  // ---- main lookup ----
  var seq=0;
  function lookup(raw){
    var my=++seq,term=raw.trim().replace(/\s+/g,' ');if(!term)return;
    out.dataset.used='1';
    out.innerHTML='<div class="dload">Looking up “'+esc(term)+'”…</div>';
    var start=dir==='es'
      ?translate(term,'es|en').then(function(r){return {en:r.main.replace(/[.!]+$/,''),es:term,esAlts:r.alts}})
      :Promise.resolve({en:term});
    start.then(function(x){
      if(my!==seq)return;
      var en=x.en;addHist(en);
      history.replaceState(null,'','#dict='+encodeURIComponent(en));
      out.innerHTML=
        '<div class="dhead"><div><h3 class="dword">'+esc(en)+'</h3>'+
          (x.es?'<div class="dfrom">from Spanish: “'+esc(x.es)+'”</div>':'')+
          '<div class="dphon" id="d-phon"></div></div>'+
          '<div class="daudio"><button type="button" class="dplay" data-say="'+esc(en)+'" data-rate="0.92">'+SPK+'Listen</button>'+
          '<button type="button" class="dplay" data-say="'+esc(en)+'" data-rate="0.6">'+SPK+'Slow</button><span id="d-native" class="daudio"></span></div></div>'+
        '<section class="dsec"><h4>Spanish</h4><div id="d-es"><span class="dload">Translating…</span></div></section>'+
        '<section class="dsec"><h4>Meaning in English</h4><div id="d-def"><span class="dload">Loading…</span></div></section>'+
        '<section class="dsec"><h4 id="d-syn-h">Synonyms</h4><div id="d-syn" class="dsyns"><span class="dload">Loading…</span></div></section>'+
        '<section class="dsec"><h4>Examples</h4><ul id="d-ex" class="dex"><li class="dload" style="background:none">Loading…</li></ul></section>'+
        '<section class="dsec" id="d-list-s"><h4>In your phrase list</h4><ul id="d-list" class="dex"></ul></section>'+
        '<div class="dlinks">See more: '+
          '<a target="_blank" rel="noopener" href="https://dictionary.cambridge.org/dictionary/english-spanish/'+encodeURIComponent(en.toLowerCase().replace(/ /g,'-'))+'">Cambridge</a>'+
          '<a target="_blank" rel="noopener" href="https://www.wordreference.com/es/translation.asp?tranword='+encodeURIComponent(en)+'">WordReference</a>'+
          '<a target="_blank" rel="noopener" href="https://youglish.com/pronounce/'+encodeURIComponent(en)+'/english/us">YouGlish (hear it in real videos)</a></div>';
      var $=function(id){return document.getElementById(id)};

      // Spanish
      if(x.es){$('d-es').innerHTML='<div class="des-main">'+esc(x.es)+'</div>'+
          (x.esAlts&&x.esAlts.length?'<div class="des-alt">Other English options: '+x.esAlts.map(function(a){
            return '<button type="button" class="dchip" data-look="'+esc(a)+'">'+esc(a)+'</button>'}).join(' ')+'</div>':'')}

      // phrase list
      var mine=fromList(en);$('d-list-s').style.display='none';

      // dictionary + synonyms
      var dictP=get('https://api.dictionaryapi.dev/api/v2/entries/en/'+encodeURIComponent(en.toLowerCase())).catch(function(e){return null});
      var synP=get('https://api.datamuse.com/words?rel_syn='+encodeURIComponent(en.toLowerCase())+'&max=14').then(function(d){
          if(d&&d.length)return {kind:'syn',w:d};
          return get('https://api.datamuse.com/words?ml='+encodeURIComponent(en.toLowerCase())+'&max=10').then(function(r){return {kind:'rel',w:r||[]}})})
        .catch(function(){return {kind:'syn',w:[]}});

      // Spanish: a single word alone gets bad translations ("run" -> "demanda"),
      // so translate it in context for each part of speech: "to run", "the run"...
      var NOTR='<span class="dnote">Spanish translation unavailable right now (the free service allows about 5,000 characters a day). Try the links below.</span>';
      function cleanEs(t,pos){t=String(t).trim().replace(/[.!]+$/,'');
        if(pos==='verb')t=t.replace(/^(para|a)\s+/i,'');
        return t}
      if(!x.es)dictP.then(function(d){
        if(my!==seq)return;
        var pos=[];(Array.isArray(d)?d:[]).forEach(function(e1){(e1.meanings||[]).forEach(function(m){
          if(m.partOfSpeech&&pos.indexOf(m.partOfSpeech)<0)pos.push(m.partOfSpeech)})});
        var w=en.toLowerCase();
        if(en.indexOf(' ')>-1||!pos.length){
          return translate(en,'en|es').then(function(r){if(my!==seq)return;
            $('d-es').innerHTML='<div class="des-main">'+esc(cleanEs(r.main))+'</div>'+(r.alts.length?'<div class="des-alt">Also: '+r.alts.map(esc).join(' · ')+'</div>':'')})}
        var rows=[translate(en,'en|es').then(function(r){return {k:'',t:cleanEs(r.main)}})];
        if(pos.indexOf('verb')>-1&&pos.indexOf('noun')>-1){
          rows.push(translate('to '+w,'en|es').then(function(r){return {k:'verb',t:cleanEs(r.main,'verb')}}).catch(function(){return null}));
          rows.push(translate('the '+w,'en|es').then(function(r){return {k:'noun',t:cleanEs(r.main)}}).catch(function(){return null}))}
        return Promise.all(rows).then(function(rs){if(my!==seq)return;
          var main=rs[0],extra=rs.slice(1).filter(Boolean);
          $('d-es').innerHTML='<div class="des-main">'+esc(main.t)+'</div>'+
            (extra.length?'<div class="des-alt">'+extra.map(function(r){return '<b>as a '+esc(r.k)+':</b> '+esc(r.t)}).join(' · ')+'</div>':'')})
      }).catch(function(){if(my!==seq)return;$('d-es').innerHTML=NOTR});

      Promise.all([dictP,synP]).then(function(res){
        if(my!==seq)return;
        var entries=Array.isArray(res[0])?res[0]:[],syn=res[1],exs=[],dsyn=[];
        // phonetics + native audio
        var phon='',aud=[];
        entries.forEach(function(en1){if(!phon&&en1.phonetic)phon=en1.phonetic;
          (en1.phonetics||[]).forEach(function(p){if(!phon&&p.text)phon=p.text;
            if(p.audio){var u=p.audio.indexOf('//')===0?'https:'+p.audio:p.audio,m=u.match(/-(us|uk|au|ca)\.mp3/i),
              lab=m?m[1].toUpperCase():'Audio';if(!aud.some(function(a){return a.lab===lab}))aud.push({u:u,lab:lab})}})});
        $('d-phon').textContent=phon;
        $('d-native').innerHTML=aud.slice(0,2).map(function(a){return '<button type="button" class="dplay" data-url="'+esc(a.u)+'" title="Real recording">'+SPK+esc(a.lab)+'</button>'}).join('');
        // definitions grouped by part of speech
        var groups={},order=[];
        entries.forEach(function(e1){(e1.meanings||[]).forEach(function(m){
          var k=m.partOfSpeech||'';if(!groups[k]){groups[k]=[];order.push(k)}
          (m.definitions||[]).forEach(function(d){var dn=lc(d.definition).replace(/[.!]+$/,'');
            if(dn!==lc(en)&&dn!=='to '+lc(en)&&dn!=='a '+lc(en))groups[k].push(d.definition);if(d.example)exs.push(d.example);(d.synonyms||[]).forEach(function(s){dsyn.push(s)})});
          (m.synonyms||[]).forEach(function(s){dsyn.push(s)})})});
        order=order.filter(function(k){return groups[k].length});
        if(order.length){
          $('d-def').innerHTML=order.slice(0,4).map(function(k){return '<div class="dpos">'+esc(k)+'</div><ol class="ddefs">'+
            groups[k].slice(0,3).map(function(d){return '<li>'+esc(d)+'</li>'}).join('')+'</ol>'}).join('');
        }else{
          $('d-def').innerHTML='<span class="dnote">No dictionary entry found'+(en.indexOf(' ')>-1?' for this phrase (the free dictionary mostly covers single words)':'')+'. Check the Spanish meaning, your phrase list and the links below.</span>'}
        // synonyms: dictionary first, then Datamuse
        var all=[],seen={};dsyn.concat(syn.w.map(function(w){return w.word})).forEach(function(s){var k=lc(s);if(k&&!seen[k]&&k!==lc(en)){seen[k]=1;all.push(s)}});
        if(syn.kind==='rel'&&!dsyn.length)$('d-syn-h').textContent='Related words';
        $('d-syn').innerHTML=all.length?all.slice(0,14).map(function(s){return '<button type="button" class="dchip" data-look="'+esc(s)+'" title="Look up">'+esc(s)+'</button>'}).join(''):'<span class="dnote">No synonyms found.</span>';
        // examples: dictionary examples, then phrases from your list
        var exHtml=exs.slice(0,6).map(function(t){return exItem(t,'','',true)});
        var used=exHtml.length<3?Math.min(mine.length,3-exHtml.length):0;
        mine.slice(0,used).forEach(function(m){exHtml.push(exItem(m.en,m.es,'From your phrase list',false))});
        var rest=mine.slice(used);
        if(rest.length){$('d-list').innerHTML=rest.map(function(m){return exItem(m.en,m.es,'',false)}).join('');$('d-list-s').style.display=''}
        $('d-ex').innerHTML=exHtml.length?exHtml.join(''):'<li class="dnote" style="background:none;padding-left:0">No examples found. Try YouGlish below to hear it used in real videos.</li>';
      });
    }).catch(function(){if(my!==seq)return;
      out.innerHTML='<div class="dempty"><p>Couldn’t translate “'+esc(term)+'” to English right now.</p><p>Check your connection, or switch to <b>EN → ES</b> and type the English word.</p></div>'});
  }

  // open from a link like ...#dict=deadline
  function fromHash(){var h=location.hash;
    if(h.indexOf('#dict=')===0){var t=decodeURIComponent(h.slice(6));if(t&&lc(t)!==lc(inp.value)){setDir('en');open(t)}else if(t)open()}
    else if(h==='#dict')open()}
  setTimeout(fromHash,0);addEventListener('hashchange',fromHash);
})();
"""

ICON_BOOK = '<svg viewBox="0 0 24 24"><path d="M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a3 3 0 0 1-3-3V5a3 3 0 0 1 3-3zm0 2a1 1 0 0 0-1 1v11.2c.3-.1.6-.2 1-.2h12V4H6zm0 14a1 1 0 0 0 0 2h12v-2H6zm2-12h8v2H8V6zm0 4h6v2H8v-2z"/></svg>'
ICON_CLOSE = '<svg viewBox="0 0 24 24"><path d="M6.4 5 12 10.6 17.6 5 19 6.4 13.4 12 19 17.6 17.6 19 12 13.4 6.4 19 5 17.6 10.6 12 5 6.4z"/></svg>'

DICT_HTML = f"""<div class="dict" id="dict" role="dialog" aria-modal="true" aria-labelledby="dict-h">
<div class="dict-box">
<div class="dict-top">
<div class="dict-title"><h2 id="dict-h">{ICON_BOOK}Dictionary</h2>
<button class="btn icon" id="dclose" type="button" aria-label="Close dictionary" title="Close (Esc)">{ICON_CLOSE}</button></div>
<form class="dform" id="dform" autocomplete="off">
<label class="search">{ICON_SEARCH}<input id="dq" type="search" enterkeyhint="search" autocapitalize="off" spellcheck="false" placeholder="Type an English word or phrase…"></label>
<button class="btn" id="ddir" type="button">EN → ES</button>
<button class="btn" type="submit" aria-pressed="true">Search</button>
</form>
<div class="dhist" id="dhist"></div>
</div>
<div class="dout" id="dout"></div>
</div>
</div>"""

intro_html = "".join(intro)
page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{html.escape(title)}</title>
<style>{CSS}{DICT_CSS}</style>
</head>
<body>
<header class="hero"><div class="hero-in">
<span class="eyebrow">English chunking</span>
<h1>{inline(title)}</h1>
<p>Learn whole phrases, not single words. Use the search, listen to each phrase, hide a language to test yourself, and look up any word in the Dictionary.</p>
{intro_html}
<div class="stats">
<div class="stat"><b>{total}</b>phrases</div>
<div class="stat"><b>{len(sections)}</b>sections</div>
<div class="stat"><b>7</b>daily drills</div>
</div>
</div></header>

<div class="toolbar"><div class="toolbar-in">
<button class="btn icon" id="toc-btn" type="button" aria-label="Contents">{ICON_MENU}<span class="lbl">Contents</span></button>
<button class="btn" id="dict-btn" type="button" title="Dictionary (d)">{ICON_BOOK}<span>Dictionary</span></button>
<label class="search">{ICON_SEARCH}<input id="q" type="search" placeholder="Search phrases…" autocomplete="off"></label>
<button class="btn" id="hide-en" type="button" aria-pressed="false">{ICON_EYE}<span>Hide English</span></button>
<button class="btn" id="hide-es" type="button" aria-pressed="false">{ICON_EYE}<span>Hide Spanish</span></button>
<button class="btn icon" id="theme" type="button" aria-label="Toggle dark mode" title="Toggle dark mode">{ICON_MOON}</button>
<div class="result" id="result"></div>
</div></div>

<div class="layout">
<nav class="toc" aria-label="Contents"><h4>Contents</h4><ol>{"".join(toc)}</ol></nav>
<div class="scrim"></div>
<main>
{"".join(body)}
<div class="empty" id="empty">No phrases match your search.</div>
</main>
</div>
<footer>{html.escape(updated)} · Tap a hidden phrase to reveal it · Tap the speaker to hear it<br>Dictionary data: Free Dictionary API, Datamuse and MyMemory</footer>
{DICT_HTML}
<button id="top" type="button" aria-label="Back to top">{ICON_UP}</button>
<script>{JS}</script>
<script>{DICT_JS}</script>
</body>
</html>
"""

(ROOT / "index.html").write_text(page, encoding="utf-8", newline="\n")
print(f"index.html written: {len(sections)} sections, {total} phrases")
