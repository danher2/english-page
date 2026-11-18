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

intro_html = "".join(intro)
page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header class="hero"><div class="hero-in">
<span class="eyebrow">English chunking</span>
<h1>{inline(title)}</h1>
<p>Learn whole phrases, not single words. Use the search, listen to each phrase, and hide a language to test yourself.</p>
{intro_html}
<div class="stats">
<div class="stat"><b>{total}</b>phrases</div>
<div class="stat"><b>{len(sections)}</b>sections</div>
<div class="stat"><b>7</b>daily drills</div>
</div>
</div></header>

<div class="toolbar"><div class="toolbar-in">
<button class="btn icon" id="toc-btn" type="button" aria-label="Contents">{ICON_MENU}<span class="lbl">Contents</span></button>
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
<footer>{html.escape(updated)} · Tap a hidden phrase to reveal it · Tap the speaker to hear it</footer>
<button id="top" type="button" aria-label="Back to top">{ICON_UP}</button>
<script>{JS}</script>
</body>
</html>
"""

(ROOT / "index.html").write_text(page, encoding="utf-8", newline="\n")
print(f"index.html written: {len(sections)} sections, {total} phrases")
