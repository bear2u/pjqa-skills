# -*- coding: utf-8 -*-
"""PJQA 프로젝트 폴더(00~05.md) → report.html 단일 파일 종합 보고서.
사용법: python3 build_report.py <프로젝트 폴더>
산출물 계약(pjqa-* 스킬의 형식)을 따르는 마크다운을 파싱한다. 못 읽은 항목은 비워 둔다."""
import re, sys, os, html

COLORS = ['#2fd4b6', '#ff9f43', '#4dd0e1', '#a55eea']
PINK, AMBER, DIM = '#ff6b9d', '#ffc24b', '#9aa7b4'

def esc(x):
    return html.escape(str(x), quote=False)

def read(d, name):
    p = os.path.join(d, name)
    return open(p, encoding='utf8').read() if os.path.exists(p) else ''

def sections(md):
    out, cur, buf = {}, None, []
    for line in md.splitlines():
        if line.startswith('## '):
            if cur: out[cur] = '\n'.join(buf)
            cur, buf = line[3:].strip(), []
        elif cur:
            buf.append(line)
    if cur: out[cur] = '\n'.join(buf)
    return out

def bullets(txt):
    return [re.sub(r'^\s*[-*]\s*', '', l).strip() for l in txt.splitlines() if l.strip().startswith(('-', '*'))]

def clean(s):
    return s.replace('**', '').strip()

# ---------- parse ----------
def parse_brief(md):
    for l in md.splitlines():
        if '아이디어:' in l:
            return clean(l.split('아이디어:', 1)[1])
    m = re.search(r'#\s*(.+)', md)
    return clean(m.group(1)) if m else ''

def parse_personas(md):
    people, others = [], []
    blocks = re.split(r'^###\s*', md, flags=re.M)[1:]
    for b in blocks:
        head, _, rest = b.partition('\n')
        m = re.match(r'(.+?)\s*\((.+)\)', head.strip())
        name = clean(m.group(1)) if m else clean(head)
        role = m.group(2) if m else ''
        does, pain, center = [], '', False
        for l in rest.splitlines():
            l = l.strip()
            if '하는 일:' in l:
                does = [x.strip() for x in clean(l.split('하는 일:', 1)[1]).split('/') if x.strip()]
            if '대표 불편:' in l:
                pain = clean(l.split('대표 불편:', 1)[1])
            if '※' in l or '결제하지 않지만' in l:
                center = True
        people.append(dict(name=name, role=role, does=does, pain=pain, center=center))
    sec = sections(md)
    for k, v in sec.items():
        if '주변' in k:
            others = [clean(b) for b in bullets(v)]
    return people, others

EMO = {'높음': 0.85, '중간': 0.5, '낮음': 0.18, '회복': 0.65}
def emo_val(s):
    s = clean(s)
    if '→' in s:
        a, b = s.split('→')
        return (emo_val(a) + emo_val(b)) / 2
    for k, v in EMO.items():
        if k in s: return v
    return 0.5

def parse_journey(md):
    sec = sections(md)
    stages = []
    for k, v in sec.items():
        if '공통 단계' in k:
            txt = ' '.join(l.strip() for l in v.splitlines() if l.strip())
            stages = [clean(x) for x in re.split(r'\s*\d+\.\s*', ' ' + txt) if x.strip()]
    curves = {}
    for m in re.finditer(r'^###\s*(.+)$', md, flags=re.M):
        name = clean(m.group(1))
        tail = md[m.end():]
        rows = []
        for l in tail.splitlines():
            if l.startswith('###'): break
            cells = [c.strip() for c in l.strip().strip('|').split('|')]
            if len(cells) >= 3 and cells[0] and '단계' not in cells[0] and '---' not in cells[0]:
                rows.append((cells[0], cells[1], cells[2]))
        if rows: curves[name] = [(emo_val(e), why) for _, e, why in rows]
    floors, main_floor, meet, problem = [], '', '', ''
    for k, v in sec.items():
        if k.startswith('바닥'):
            for b in bullets(v):
                if '주 바닥' in b:
                    main_floor = clean(b.split(':', 1)[-1] if ':' in b else b)
                    main_floor = re.sub(r'\s*\(.*$', '', main_floor).strip(' *')
                else:
                    floors.append(clean(b))
        if k.startswith('접점'):
            meet = clean(' '.join(l.strip() for l in v.splitlines() if l.strip()))
        if '진짜 문제' in k:
            problem = clean(' '.join(l.strip() for l in v.splitlines() if l.strip()))
    if not main_floor and floors:
        main_floor = floors[0].split(':')[-1].strip()
    return stages, curves, floors, main_floor, meet, problem

def curve_path(vals, W=1160, H=340, pad=50):
    xs = [pad + i * (W - 2 * pad) / max(len(vals) - 1, 1) for i in range(len(vals))]
    pts = [(x, H - 40 - v * (H - 90)) for x, v in zip(xs, vals)]
    P = [pts[0]] + pts + [pts[-1]]
    d = f'M {pts[0][0]:.0f} {pts[0][1]:.0f}'
    for i in range(len(P) - 3):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f' C {c1[0]:.0f} {c1[1]:.0f}, {c2[0]:.0f} {c2[1]:.0f}, {p2[0]:.0f} {p2[1]:.0f}'
    dots = ''.join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="currentColor"/>' for x, y in pts)
    return d, dots, xs

def parse_quadrant(md):
    items = []
    for l in md.splitlines():
        cells = [c.strip() for c in l.strip().strip('|').split('|')]
        if len(cells) >= 3 and cells[0] and '후보' not in cells[0] and '---' not in cells[0]:
            items.append((clean(cells[0]), clean(cells[1]), clean(cells[2])))
    sec = sections(md)
    adopted, deferred, dropped = [], [], []
    for k, v in sec.items():
        if '채택' in k: adopted = [clean(b) for b in bullets(v)]
        if '미룸' in k or '2차' in k: deferred = [clean(b) for b in bullets(v)]
        if '탈락' in k: dropped = [clean(b) for b in bullets(v) if '없음' not in b]
    return items, adopted, deferred, dropped

def split_flow(txt):
    txt = ' '.join(l.strip() for l in txt.splitlines() if l.strip())
    parts = [clean(p) for p in txt.split('→')]
    out = []
    for p in parts:
        p = re.sub(r'^\d+\.\s*', '', p).strip()
        p = re.sub(r'\s*\d+\.$', '', p).strip()
        if p: out.append(p)
    return out

def parse_arrow(md):
    sec = sections(md)
    asis, tobe, changed, why, keep = [], '', '', '', []
    for k, v in sec.items():
        if 'AS-IS' in k: asis = split_flow(v)
        if '바꾸는 화살표' in k:
            lines = [clean(l) for l in v.splitlines() if l.strip()]
            changed = lines[0] if lines else ''
            for l in lines[1:]:
                if '근거' in l: why = l
        if '그대로' in k: keep = [clean(b) for b in bullets(v)]
        if 'TO-BE' in k: tobe = clean(' '.join(l.strip() for l in v.splitlines() if l.strip()))
    m = re.search(r'(\d+)\s*→\s*(\d+)', changed)
    hl = int(m.group(1)) - 1 if m else -1
    return asis, changed, why, keep, tobe, hl

def parse_mvp(md):
    sec = sections(md)
    get = lambda key: clean(' '.join(l.strip() for l in sec.get(key, '').splitlines() if l.strip()))
    defi = get('정의문')
    inc = [clean(b) for b in bullets(sec.get('포함 (첫 버전)', sec.get('포함', '')))]
    exc = [clean(b) for b in bullets(sec.get('제외 (2차)', sec.get('제외', '')))]
    signal, trace = get('성공 신호'), get('근거 추적')
    plan_steps, plan_screens, plan_decide = [], [], []
    plan = sec.get('추천 MVP 기획', '')
    sub = sections('## 추천\n' + plan) if plan else {}
    cur = None
    for l in plan.splitlines():
        if l.startswith('### '):
            cur = l[4:].strip()
        elif cur and '순서' in cur and re.match(r'\s*\d+\.', l):
            plan_steps.append(clean(re.sub(r'^\s*\d+\.\s*', '', l)))
        elif cur and '화면' in cur and l.strip().startswith('-'):
            plan_screens.append(clean(re.sub(r'^\s*[-*]\s*', '', l)))
        elif cur and '결정' in cur and l.strip().startswith('-'):
            plan_decide.append(clean(re.sub(r'^\s*[-*]\s*', '', l)))
    return defi, inc, exc, signal, trace, plan_steps, plan_screens, plan_decide

# ---------- render ----------
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#e9eef5;font-family:-apple-system,'Segoe UI','Malgun Gothic','Apple SD Gothic Neo',sans-serif;display:flex;min-height:100vh}
nav{width:230px;flex:none;background:#0a0e14;border-right:1px solid #2a3242;padding:28px 18px;position:sticky;top:0;height:100vh}
nav .logo{font-size:15px;color:#9aa7b4;letter-spacing:2px;margin-bottom:6px}
nav .proj{font-size:20px;font-weight:800;line-height:1.35;margin-bottom:26px}
nav button{display:block;width:100%;text-align:left;background:none;border:0;color:#9aa7b4;font-size:16.5px;padding:11px 12px;border-radius:10px;cursor:pointer;margin-bottom:4px}
nav button.on{background:#161c26;color:#fff;font-weight:700}
nav button b{font-family:ui-monospace,monospace;margin-right:8px}
main{flex:1;padding:44px 52px;max-width:1240px}
.page{display:none}.page.on{display:block}
h1{font-size:34px;margin-bottom:8px}h2{font-size:24px;margin:30px 0 14px}
.sub{color:#9aa7b4;font-size:16px;line-height:1.6}
.card{background:#11161d;border:1.5px solid #2a3242;border-radius:16px;padding:24px 26px}
.def{font-size:30px;font-weight:800;line-height:1.5}
.grid{display:grid;gap:18px}
.g3{grid-template-columns:repeat(3,1fr)}.g2{grid-template-columns:1fr 1fr}
.kpi .n{font-size:15px;color:#9aa7b4}.kpi .v{font-size:21px;font-weight:800;margin-top:6px;line-height:1.4}
ul{list-style:none}li{font-size:16.5px;line-height:1.65;padding:3px 0}
.tag{display:inline-block;font-size:13.5px;font-weight:800;padding:4px 12px;border-radius:999px;border:2px solid}
.flow{display:flex;align-items:stretch;gap:0;flex-wrap:wrap}
.step{background:#11161d;border:1.5px solid #2a3242;border-radius:14px;padding:18px 16px;font-size:16.5px;font-weight:700;max-width:230px;display:flex;align-items:center}
.arr{display:flex;align-items:center;padding:0 7px;color:#5c6875;font-size:22px;font-weight:800}
.arr.hl{color:#ffc24b;text-shadow:0 0 14px rgba(255,194,75,.8)}
.quad{position:relative;height:430px;border:2px solid #2a3242;border-radius:14px;background:#0a0e14}
.quad .qx{position:absolute;left:50%;top:0;width:2px;height:100%;background:#2a3242}
.quad .qy{position:absolute;top:50%;left:0;height:2px;width:100%;background:#2a3242}
.quad .hi{position:absolute;left:0;top:0;width:50%;height:50%;background:rgba(255,194,75,.07);border-radius:14px 0 0 0}
.qi{position:absolute;font-size:16px;font-weight:700;white-space:nowrap}
.qi.dim{color:#5c6875;font-weight:600}
.ax{position:absolute;font-size:13.5px;color:#9aa7b4}
.step-tl{display:flex;gap:16px;margin-bottom:14px}
.step-tl .no{flex:none;width:38px;height:38px;border-radius:50%;background:#ffc24b;color:#111;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:18px}
footer{color:#5c6875;font-size:13.5px;margin-top:44px}
@media(max-width:860px){body{flex-direction:column}nav{width:100%;height:auto;position:static}main{padding:26px 20px}.g3,.g2{grid-template-columns:1fr}}
"""

def build(d):
    title = os.path.basename(os.path.abspath(d))
    brief = parse_brief(read(d, '00-brief.md'))
    people, others = parse_personas(read(d, '01-personas.md'))
    stages, curves, floors, main_floor, meet, problem = parse_journey(read(d, '02-journeys.md'))
    qitems, adopted, deferred, dropped = parse_quadrant(read(d, '03-quadrant.md'))
    asis, changed, why, keep, tobe, hl = parse_arrow(read(d, '04-arrow.md'))
    defi, inc, exc, signal, trace, steps, screens, decide = parse_mvp(read(d, '05-mvp.md'))
    pcolor = {p['name']: COLORS[i % len(COLORS)] for i, p in enumerate(people)}

    # overview
    ov = f"""<section class="page on" id="p0"><h1>{esc(title)}</h1><p class="sub">{esc(brief)}</p>
    <div class="card" style="margin-top:24px"><div style="color:{AMBER};font-weight:800;font-size:15px;letter-spacing:2px">MVP 정의문</div><div class="def" style="margin-top:10px">{esc(defi)}</div></div>
    <div class="card" style="margin-top:18px;border-color:{PINK}"><div style="color:{PINK};font-weight:800;font-size:15px;letter-spacing:2px">진짜 문제</div><div style="font-size:21px;font-weight:700;margin-top:8px;line-height:1.55">{esc(problem)}</div></div>
    <div class="grid g3" style="margin-top:18px">
      <div class="card kpi"><div class="n">주인공</div><div class="v">{esc(' · '.join(p['name'] for p in people))}</div></div>
      <div class="card kpi"><div class="n">채택 기능 (왼쪽 위)</div><div class="v">{esc(adopted[0].split('—')[0].strip() if adopted else '-')}</div></div>
      <div class="card kpi"><div class="n">바꾸는 화살표</div><div class="v">{esc(changed.split('—')[0].strip() if changed else '-')}</div></div>
    </div></section>"""

    # personas
    pcards = ''
    for p in people:
        c = pcolor[p['name']]
        badge = f'<span class="tag" style="border-color:{c};color:{c};margin-top:12px">결제하지 않지만 설계의 중심</span>' if p['center'] else ''
        does = ''.join(f'<li>· {esc(x)}</li>' for x in p['does'])
        pcards += f"""<div class="card" style="border-top:5px solid {c}"><div style="font-size:23px;font-weight:800;color:{c}">{esc(p['name'])}</div>
        <div style="color:{DIM};margin:4px 0 14px">{esc(p['role'])}</div><ul>{does}</ul>
        <div style="margin-top:12px;color:{DIM}">대표 불편 — {esc(p['pain'])}</div>{badge}</div>"""
    oth = ''.join(f'<li>· {esc(o)}</li>' for o in others)
    pp = f"""<section class="page" id="p1"><h1>P — 사람으로 펼치기</h1><div class="grid g3" style="margin-top:20px">{pcards}</div>
    {'<h2>주변 인물</h2><ul>' + oth + '</ul>' if others else ''}</section>"""

    # journey svg
    svg_curves, legend = '', ''
    floor_i = stages.index(main_floor.split('(')[0].strip()) if False else -1
    # floor band: between the stage where the main persona's min occurs — approximate with global min stage of first curve
    band = ''
    if curves and stages:
        first = list(curves.values())[0]
        mini = min(range(len(first)), key=lambda i: first[i][0])
        xs0 = 50 + max(mini - 1, 0) * (1160 - 100) / max(len(stages) - 1, 1)
        xs1 = 50 + min(mini + 1, len(stages) - 1) * (1160 - 100) / max(len(stages) - 1, 1)
        band = f'<rect x="{xs0:.0f}" y="20" width="{xs1 - xs0:.0f}" height="280" fill="{PINK}" fill-opacity="0.08"/>'
    for i, (name, rows) in enumerate(curves.items()):
        c = pcolor.get(name, COLORS[i % len(COLORS)])
        vals = [v for v, _ in rows]
        dpath, dots, xs = curve_path(vals)
        svg_curves += f'<g style="color:{c}"><path d="{dpath}" fill="none" stroke="{c}" stroke-width="4.5" stroke-linecap="round"/>{dots}</g>'
        legend += f'<span class="tag" style="border-color:{c};color:{c};margin-right:10px">{esc(name)}</span>'
    stage_labels = ''
    if stages:
        for i, sname in enumerate(stages):
            x = 50 + i * (1160 - 100) / max(len(stages) - 1, 1)
            stage_labels += f'<text x="{x:.0f}" y="368" fill="{DIM}" font-size="17" text-anchor="middle">{esc(sname)}</text>'
    fl = ''.join(f'<li>· {esc(f)}</li>' for f in floors)
    jp = f"""<section class="page" id="p2"><h1>J — 여정을 겹쳐 보기</h1><div style="margin:18px 0">{legend}</div>
    <svg viewBox="0 0 1160 385" style="width:100%;background:#0a0e14;border:1.5px solid #2a3242;border-radius:14px">{band}{svg_curves}{stage_labels}</svg>
    <div class="grid g2" style="margin-top:18px"><div class="card"><div style="color:{PINK};font-weight:800">바닥</div><ul style="margin-top:8px">{fl}</ul>
    <div style="margin-top:10px">주 바닥 — <b>{esc(main_floor)}</b></div></div>
    <div class="card"><div style="color:{AMBER};font-weight:800">접점</div><div style="margin-top:8px;line-height:1.6">{esc(meet)}</div></div></div>
    <div class="card" style="margin-top:18px;border-color:{PINK}"><div style="color:{PINK};font-weight:800;font-size:15px;letter-spacing:2px">진짜 문제</div>
    <div style="font-size:21px;font-weight:700;margin-top:8px;line-height:1.55">{esc(problem)}</div></div></section>"""

    # quadrant
    qi, pos = '', {'왼쪽 위': [], '오른쪽 위': [], '아래': []}
    for nme, where, _g in qitems:
        pos.get(where if where in pos else '아래').append(nme)
    slots = {'왼쪽 위': [(4, 8), (4, 22), (4, 36)], '오른쪽 위': [(54, 8), (54, 22), (54, 36)],
             '아래': [(4, 58), (54, 58), (4, 74), (54, 74), (29, 88)]}
    for where, names in pos.items():
        for j, nme in enumerate(names):
            if j >= len(slots[where]): break
            x, y = slots[where][j]
            star = where == '왼쪽 위'
            qi += f'<div class="qi {"dim" if not star else ""}" style="left:{x}%;top:{y}%;color:{AMBER if star else ""}">{"● " if star else "· "}{esc(nme)}</div>'
    ad = ''.join(f'<li>· {esc(a)}</li>' for a in adopted)
    df = ''.join(f'<li>· {esc(a)}</li>' for a in deferred)
    dr = ''.join(f'<li>· {esc(a)}</li>' for a in dropped)
    qp = f"""<section class="page" id="p3"><h1>Q — 왼쪽 위만 남기기</h1>
    <div class="quad" style="margin-top:20px"><div class="hi"></div><div class="qx"></div><div class="qy"></div>{qi}
    <div class="ax" style="left:10px;top:-24px">영향 큼</div><div class="ax" style="left:10px;bottom:-24px">영향 작음</div><div class="ax" style="left:45%;bottom:-24px">쉬움 →</div>
    <div class="ax" style="left:10px;bottom:-24px;top:auto"></div><div class="ax" style="right:10px;bottom:-24px">어려움</div></div>
    <div class="grid g2" style="margin-top:44px"><div class="card"><div style="color:{AMBER};font-weight:800">채택 (왼쪽 위)</div><ul style="margin-top:8px">{ad}</ul></div>
    <div class="card"><div style="color:{DIM};font-weight:800">2차로 미룸</div><ul style="margin-top:8px">{df}</ul></div></div>
    {'<h2>탈락</h2><ul>' + dr + '</ul>' if dropped else ''}</section>"""

    # arrow
    flow = ''
    for i, st in enumerate(asis):
        flow += f'<div class="step">{esc(st)}</div>'
        if i < len(asis) - 1:
            flow += f'<div class="arr {"hl" if i == hl else ""}">→</div>'
    kp = ''.join(f'<li>· {esc(k)}</li>' for k in keep)
    ap = f"""<section class="page" id="p4"><h1>A — 화살표 하나만 바꾸기</h1><h2>AS-IS (지금 흐름)</h2><div class="flow">{flow}</div>
    <div class="card" style="margin-top:22px;border-color:{AMBER}"><div style="color:{AMBER};font-weight:800">바꾸는 화살표 (딱 1개)</div>
    <div style="font-size:19px;font-weight:700;margin-top:8px;line-height:1.55">{esc(changed)}</div><div style="color:{DIM};margin-top:8px">{esc(why)}</div></div>
    <div class="grid g2" style="margin-top:18px"><div class="card"><div style="font-weight:800">그대로 두는 구간</div><ul style="margin-top:8px">{kp}</ul></div>
    <div class="card"><div style="font-weight:800;color:{AMBER}">TO-BE</div><div style="margin-top:8px;line-height:1.65">{esc(tobe)}</div></div></div></section>"""

    # mvp + plan
    incl = ''.join(f'<li>· {esc(x)}</li>' for x in inc)
    excl = ''.join(f'<li>· {esc(x)}</li>' for x in exc)
    mp = f"""<section class="page" id="p5"><h1>MVP — 정의</h1>
    <div class="card" style="margin-top:20px"><div style="color:{AMBER};font-weight:800;font-size:15px;letter-spacing:2px">정의문</div><div class="def" style="margin-top:10px">{esc(defi)}</div></div>
    <div class="grid g2" style="margin-top:18px"><div class="card"><div style="font-weight:800;color:{COLORS[0]}">포함 (첫 버전)</div><ul style="margin-top:8px">{incl}</ul></div>
    <div class="card"><div style="font-weight:800;color:{DIM}">제외 (2차)</div><ul style="margin-top:8px">{excl}</ul></div></div>
    <div class="card" style="margin-top:18px"><div style="font-weight:800">성공 신호</div><div style="margin-top:8px;line-height:1.6">{esc(signal)}</div>
    <div style="color:{DIM};margin-top:12px;font-size:14.5px">근거 추적 — {esc(trace)}</div></div></section>"""

    tl = ''
    for i, sname in enumerate(steps):
        parts = sname.split(' / 완료 판정:')
        head = parts[0]
        judge = parts[1] if len(parts) > 1 else ''
        title_txt, _, desc = head.partition(' — ')
        tl += f"""<div class="step-tl"><div class="no">{i + 1}</div><div class="card" style="flex:1"><div style="font-size:19px;font-weight:800">{esc(title_txt.strip())}</div>
        <div style="color:{DIM};margin-top:5px;line-height:1.6">{esc(desc.strip())}</div>
        {'<div style="margin-top:8px">완료 판정 — <b>' + esc(judge.strip()) + '</b></div>' if judge else ''}</div></div>"""
    sc = ''.join(f'<li>· {esc(x)}</li>' for x in screens)
    dc = ''.join(f'<li>· {esc(x)}</li>' for x in decide)
    pl = f"""<section class="page" id="p6"><h1>추천 MVP 기획</h1><h2>만들 순서</h2>{tl}
    <div class="grid g2"><div class="card"><div style="font-weight:800">핵심 화면·흐름</div><ul style="margin-top:8px">{sc}</ul></div>
    <div class="card"><div style="font-weight:800">착수 전 결정할 것</div><ul style="margin-top:8px">{dc}</ul></div></div></section>"""

    nav_items = [('p0', '개요', ''), ('p1', '페르소나', 'P'), ('p2', '여정', 'J'), ('p3', '사분면', 'Q'), ('p4', '화살표', 'A'), ('p5', 'MVP', ''), ('p6', '추천 기획', '')]
    nav = ''.join(f'<button data-p="{i}" class="{"on" if k == 0 else ""}"><b>{esc(l)}</b>{esc(n)}</button>' for k, (i, n, l) in enumerate(nav_items))
    doc = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PJQA 보고서 — {esc(title)}</title><style>{CSS}</style></head><body>
<nav><div class="logo">PJQA REPORT</div><div class="proj">{esc(title)}</div>{nav}
<div style="color:#5c6875;font-size:13px;margin-top:22px;line-height:1.6">{esc(brief)}</div></nav>
<main>{ov}{pp}{jp}{qp}{ap}{mp}{pl}<footer>PJQA 종합 보고서 — 산출물 00~05에서 자동 생성. 원본 마크다운이 근거이며 이 보고서는 요약본이다.</footer></main>
<script>document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on'));b.classList.add('on');document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));document.getElementById(b.dataset.p).classList.add('on');window.scrollTo(0,0)}})</script>
</body></html>"""
    out = os.path.join(d, 'report.html')
    open(out, 'w', encoding='utf8').write(doc)
    print('wrote', out, len(doc), 'bytes')

if __name__ == '__main__':
    build(sys.argv[1])
