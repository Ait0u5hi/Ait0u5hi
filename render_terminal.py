#!/usr/bin/env python3
"""Self-contained terminal-stats card generator for a GitHub profile README.
Fetches live stats via the GitHub API and renders isometric-calendar SVGs
for dark and light themes. Env: GH_USER, GH_TOKEN (classic PAT)."""
import os, json, sys, time, datetime, urllib.request, urllib.error
from collections import defaultdict

USER  = os.environ.get("GH_USER", "Ait0u5hi")
TOKEN = os.environ["GH_TOKEN"]
TODAY = datetime.date.today()
W = 540

def _req(url, data=None, headers=None):
    h = {"Authorization": f"bearer {TOKEN}", "User-Agent": "terminal-card"}
    if headers: h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h)
    for attempt in range(5):  # GitHub raw/API intermittently 429/5xx; back off and retry
        try:
            return json.load(urllib.request.urlopen(r, timeout=30))
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and attempt < 4:
                time.sleep(2 ** attempt); continue
            raise

def gql(query):
    body = json.dumps({"query": query}).encode()
    return _req("https://api.github.com/graphql", body,
                {"Content-Type": "application/json"})["data"]

def rest(path):
    return _req(f"https://api.github.com/{path}")

# ---- fetch ----
u = gql(f'''query {{ user(login:"{USER}") {{
  login name createdAt followers {{ totalCount }}
  contributionsCollection {{
    totalCommitContributions totalPullRequestContributions
    totalPullRequestReviewContributions totalIssueContributions
    contributionCalendar {{ totalContributions
      weeks {{ contributionDays {{ contributionCount weekday }} }} }} }} }} }}''')["user"]
cc = u["contributionsCollection"]
weeks = cc["contributionCalendar"]["weeks"]

prof = rest(f"users/{USER}")
repos = rest(f"users/{USER}/repos?per_page=100")
stars = sum(r["stargazers_count"] for r in repos)
forks = sum(r["forks_count"] for r in repos)
nrepos = len(repos)
# Language bar: owner-affiliated, non-fork repos of the token owner (incl.
# private) via GraphQL -- so it reflects code we actually write, not forks.
# NOTE: keeps the public `repos` list above for stars/forks/nrepos counts,
# so only language *proportions* (not the private repo count) are disclosed.
lang_bytes = defaultdict(int)
cursor = None
while True:
    after = f', after:"{cursor}"' if cursor else ""
    page = gql(f'''query {{ viewer {{
      repositories(first:100, ownerAffiliations:[OWNER], isFork:false{after}) {{
        pageInfo {{ hasNextPage endCursor }}
        nodes {{ languages(first:25, orderBy:{{field:SIZE, direction:DESC}}) {{
          edges {{ size node {{ name }} }} }} }} }} }} }}''')["viewer"]["repositories"]
    for repo in page["nodes"]:
        for e in repo["languages"]["edges"]:
            lang_bytes[e["node"]["name"]] += e["size"]
    if not page["pageInfo"]["hasNextPage"]:
        break
    cursor = page["pageInfo"]["endCursor"]
top = sorted(lang_bytes.items(), key=lambda x: -x[1])[:6]
tot = sum(v for _, v in top) or 1
langs = [(k, 100*v/tot) for k, v in top]

created = datetime.date.fromisoformat(u["createdAt"][:10])
age = (TODAY - created).days // 365
allc = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
streak = 0
for c in reversed(allc):
    if c > 0: streak += 1
    else: break
total_year = cc["contributionCalendar"]["totalContributions"]
bio = (prof.get("bio") or "").replace(" — ", " · ").replace("—", "-").strip()
# featured/pinned projects (name, short descriptor) -- edit to change what's shown
FEATURED = [("hermes-agent", "agent framework"),
            ("gh-workflows", "reusable CI/CD"),
            ("hermes-plugin-workspace-guard", "agent sandbox")]
featured = FEATURED
DATA = dict(name=u["name"] or USER, followers=u["followers"]["totalCount"],
            following=prof.get("following", 0), age=age, location=prof.get("location") or "",
            bio=bio, featured=featured,
            commits=cc["totalCommitContributions"], prs=cc["totalPullRequestContributions"],
            reviews=cc["totalPullRequestReviewContributions"], issues=cc["totalIssueContributions"],
            repos=nrepos, stars=stars, forks=forks, langs=langs, weeks=weeks,
            total_year=total_year, streak=streak, avg=total_year/365.0)

# ---- render ----
PAL = {
 "dark":  dict(fg="#c9d1d9", muted="#8b949e", green="#3fb950", blue="#58a6ff",
               ground="#2d333b", cal=["#0e4429","#006d32","#26a641","#39d353"], bar="#21262d"),
 "light": dict(fg="#1f2328", muted="#656d76", green="#1a7f37", blue="#0969da",
               ground="#d0d7de", cal=["#9be9a8","#40c463","#30a14e","#216e39"], bar="#eaeef2"),
}
FS=13; LH=20; CW=7.8; PADX=14; W=540
def esc(s): return str(s).replace("&","&amp;").replace("<","&lt;")
def shade(h,f): r,g,b=int(h[1:3],16),int(h[3:5],16),int(h[5:7],16); return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"
def lvl(c,mx):
    if c<=0: return -1
    q=c/max(mx,1); return 0 if q<.25 else 1 if q<.5 else 2 if q<.75 else 3

def render(theme, out):
    P=PAL[theme]; D=DATA; s=[]
    def prompt(y,cmd):
        s.append(f'<text x="{PADX}" y="{y}" font-size="{FS}" font-family="monospace" xml:space="preserve">'
                 f'<tspan fill="{P["green"]}">{USER.lower()}@worldsim</tspan><tspan fill="{P["muted"]}">:</tspan>'
                 f'<tspan fill="{P["blue"]}">~</tspan><tspan fill="{P["muted"]}">$ </tspan>'
                 f'<tspan fill="{P["fg"]}">{esc(cmd)}</tspan></text>')
    def out_(y,t,c=None):
        s.append(f'<text x="{PADX}" y="{y}" font-size="{FS}" font-family="monospace" fill="{c or P["muted"]}" xml:space="preserve">{esc(t)}</text>')
    maxc = int((W - 2*PADX) / CW)
    def wrap(t, n):
        words=t.split(); lines=[]; cur=""
        for w in words:
            if len(cur)+len(w)+1 <= n: cur=(cur+" "+w).strip()
            else: lines.append(cur); cur=w
        if cur: lines.append(cur)
        return lines[:2]
    y=34
    prompt(y,"whoami"); y+=LH
    loc = f" · {D['location']}" if D['location'] else ""
    out_(y,f"{D['name']}{loc} · registered {D['age']}y",P["fg"]); y+=int(LH*1.4)
    if D['bio']:
        prompt(y,"cat ~/.plan"); y+=LH
        for ln in wrap(D['bio'], maxc):
            out_(y,ln,P["fg"]); y+=LH
        y+=int(LH*0.4)
    prompt(y,"git log --oneline | wc -l"); y+=LH
    out_(y,f"{D['commits']} commits · {D['prs']} PRs · {D['reviews']} reviews · {D['issues']} issues",P["fg"]); y+=int(LH*1.4)
    prompt(y,"ls -l repos/"); y+=LH
    out_(y,f"{D['repos']} repos · {D['stars']} stars · {D['forks']} forks · {D['followers']} followers · {D['following']} following",P["fg"]); y+=int(LH*1.4)
    if D['featured']:
        prompt(y,"ls ~/projects"); y+=LH
        for name, desc in D['featured']:
            s.append(f'<text x="{PADX}" y="{y}" font-size="{FS}" font-family="monospace" fill="{P["green"]}">{esc(name)}</text>')
            s.append(f'<text x="{PADX+31*CW:.0f}" y="{y}" font-size="{FS}" font-family="monospace" fill="{P["muted"]}">{esc(desc)}</text>')
            y+=LH
        y+=int(LH*0.4)
    prompt(y,"cat languages"); y+=LH
    bx=PADX+12*CW; bw=W-bx-PADX-60
    for name,pct in D["langs"]:
        out_(y,name[:11].ljust(11),P["fg"])
        s.append(f'<rect x="{bx}" y="{y-10}" width="{bw}" height="9" rx="2" fill="{P["bar"]}"/>')
        s.append(f'<rect x="{bx}" y="{y-10}" width="{bw*pct/100:.1f}" height="9" rx="2" fill="{P["green"]}"/>')
        s.append(f'<text x="{bx+bw+8}" y="{y}" font-size="{FS-1}" font-family="monospace" fill="{P["muted"]}">{pct:4.1f}%</text>')
        y+=LH
    y+=int(LH*0.5)
    prompt(y,"cal --contributions"); y+=int(LH*1.1)
    recent=D["weeks"][-16:]
    mx=max((d["contributionCount"] for w in recent for d in w["contributionDays"]),default=1)
    a,b=9,4.5; baseH=4; MAX=40
    ix=[(wi-wd) for wi in range(len(recent)) for wd in range(7)]
    originX=(W-(max(ix)-min(ix))*a)/2-min(ix)*a
    originY=y+6+baseH+MAX                        # reserve headroom so towers rise up
    cubes=[]
    for wi,w in enumerate(recent):
        for d in w["contributionDays"]:
            c=d["contributionCount"]; H=baseH+(c/mx)*MAX
            px=originX+(wi-d["weekday"])*a; py=originY+(wi+d["weekday"])*b
            L=lvl(c,mx); top=P["ground"] if L<0 else P["cal"][L]
            cubes.append((py,px,H,top))
    cubes.sort(key=lambda c:c[0]); front=0       # painter's: back(low py) -> front
    for py,px,H,top in cubes:
        front=max(front,py+b)
        N=(px,py-b);E=(px+a,py);S=(px,py+b);Wp=(px-a,py)          # ground footprint
        Nt=(px,py-b-H);Et=(px+a,py-H);St=(px,py+b-H);Wt=(px-a,py-H)  # elevated top (rises up)
        s.append(f'<polygon points="{Wp[0]:.1f},{Wp[1]:.1f} {S[0]:.1f},{S[1]:.1f} {St[0]:.1f},{St[1]:.1f} {Wt[0]:.1f},{Wt[1]:.1f}" fill="{shade(top,.55)}"/>')
        s.append(f'<polygon points="{S[0]:.1f},{S[1]:.1f} {E[0]:.1f},{E[1]:.1f} {Et[0]:.1f},{Et[1]:.1f} {St[0]:.1f},{St[1]:.1f}" fill="{shade(top,.78)}"/>')
        s.append(f'<polygon points="{Nt[0]:.1f},{Nt[1]:.1f} {Et[0]:.1f},{Et[1]:.1f} {St[0]:.1f},{St[1]:.1f} {Wt[0]:.1f},{Wt[1]:.1f}" fill="{top}"/>')
    y=front+34
    out_(y,f"{D['total_year']} contributions · {D['streak']}-day streak · ~{D['avg']:.1f}/day",P["fg"]); y+=int(LH*1.4)
    s.append(f'<text x="{PADX}" y="{y}" font-size="{FS}" font-family="monospace" xml:space="preserve">'
             f'<tspan fill="{P["green"]}">{USER.lower()}@worldsim</tspan><tspan fill="{P["muted"]}">:</tspan>'
             f'<tspan fill="{P["blue"]}">~</tspan><tspan fill="{P["muted"]}">$ </tspan>'
             f'<tspan fill="{P["green"]}">▋<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.06s" repeatCount="indefinite"/></tspan></text>')
    y+=14; Hpx=int(y)
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hpx}" viewBox="0 0 {W} {Hpx}" font-family="monospace">'
         + "".join(s) + "</svg>")
    open(out,"w").write(svg); print("wrote",out,f"({W}x{Hpx})")

render("dark",  os.environ.get("OUT_DARK","github-terminal-dark.svg"))
render("light", os.environ.get("OUT_LIGHT","github-terminal-light.svg"))
