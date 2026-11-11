import json
import math
import os
import urllib.request
from datetime import date, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter

USER = os.environ.get("GH_USER", "ninjaarara")
TOKEN = os.environ["GITHUB_TOKEN"]
TODAY = date.today()
START = TODAY - timedelta(days=364)
QUERY = """query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}"""
payload = json.dumps({"query": QUERY, "variables": {
    "login": USER, "from": START.isoformat()+"T00:00:00Z",
    "to": TODAY.isoformat()+"T23:59:59Z"
}}).encode()
req = urllib.request.Request("https://api.github.com/graphql", data=payload, headers={
    "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
    "User-Agent": "sura-activity-universe"
})
with urllib.request.urlopen(req) as response:
    result = json.load(response)
if result.get("errors"):
    raise RuntimeError(json.dumps(result["errors"]))
calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
total = calendar["totalContributions"]

W, H = 1000, 520
frames = []
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font = ImageFont.truetype(font_path, 17)
small = ImageFont.truetype(font_path, 13)
large = ImageFont.truetype(bold_path, 34)
title = ImageFont.truetype(bold_path, 22)
colors = {"NONE": (29, 40, 62), "FIRST_QUARTILE": (30, 105, 112),
          "SECOND_QUARTILE": (36, 157, 153), "THIRD_QUARTILE": (80, 215, 185),
          "FOURTH_QUARTILE": (191, 255, 224)}
# Galaxy nodes encode actual daily contribution counts and dates.
cx, cy = 500, 270
positions = []
for i, day in enumerate(days):
    angle = (i / max(1, len(days)-1)) * math.pi * 9.0 - math.pi/2
    radius = 45 + (i / max(1, len(days)-1)) * 180
    positions.append((cx + math.cos(angle)*radius, cy + math.sin(angle)*radius))

for frame in range(24):
    base = Image.new("RGB", (W, H), (7, 12, 25))
    pix = base.load()
    for y in range(H):
        for x in range(W):
            glow = max(0, 1 - math.sqrt(((x-cx)/680)**2 + ((y-cy)/430)**2))
            pix[x,y] = (7+int(glow*7), 12+int(glow*10), 25+int(glow*24))
    d = ImageDraw.Draw(base, "RGBA")
    # Fixed star field.
    for s in range(150):
        sx = (s*173+37) % W
        sy = (s*97+19) % H
        alpha = 80 + int(90*(0.5+0.5*math.sin(frame*0.35+s)))
        d.ellipse((sx,sy,sx+2,sy+2), fill=(155,205,255,alpha))
    # Orbital rings with a slowly rotating highlight.
    for rad in (72, 132, 195, 252):
        d.ellipse((cx-rad,cy-rad,cx+rad,cy+rad), outline=(66,115,170,65), width=1)
    a = frame * math.pi / 12
    d.arc((cx-252,cy-252,cx+252,cy+252), start=math.degrees(a), end=math.degrees(a)+48,
          fill=(93,234,212,190), width=3)
    # Contribution nodes: color intensity is sourced from GitHub's own level/count.
    for i, (day, (x,y)) in enumerate(zip(days, positions)):
        level = day["contributionLevel"]
        count = day["contributionCount"]
        col = colors.get(level, colors["NONE"])
        pulse = 1.0 + (0.25*math.sin(frame*math.pi/6+i*0.18) if count else 0)
        r = (2.1 + min(5, math.log1p(count)*1.3)) * pulse
        if count:
            d.ellipse((x-r*2.6,y-r*2.6,x+r*2.6,y+r*2.6), fill=(*col,35))
        d.ellipse((x-r,y-r,x+r,y+r), fill=(*col,245), outline=(190,255,240,150))
    # Central glowing core.
    core_r = 22 + 3*math.sin(frame*math.pi/6)
    d.ellipse((cx-core_r*2,cy-core_r*2,cx+core_r*2,cy+core_r*2), fill=(47,211,194,24))
    d.ellipse((cx-core_r,cy-core_r,cx+core_r,cy+core_r), fill=(20,55,83,255), outline=(94,234,212,230), width=3)
    d.ellipse((cx-5,cy-5,cx+5,cy+5), fill=(205,255,244,255))
    # Labels and actual total.
    d.text((42,32), "SURA / ACTIVITY UNIVERSE", font=title, fill=(229,244,255,255))
    d.text((44,68), f"@{USER}  •  LAST 365 DAYS", font=small, fill=(116,174,205,255))
    d.text((42,438), f"{total:,}", font=large, fill=(94,234,212,255))
    d.text((44,482), "CONTRIBUTIONS", font=small, fill=(163,190,215,255))
    d.text((790,450), "REAL GITHUB DATA", font=small, fill=(167,139,250,255))
    d.text((790,474), TODAY.isoformat(), font=small, fill=(116,145,180,255))
    frames.append(base.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))

os.makedirs("assets", exist_ok=True)
frames[0].save("assets/activity-universe.gif", save_all=True, append_images=frames[1:],
               duration=100, loop=0, optimize=True, disposal=2)
print(f"Generated Activity Universe: {total} contributions across {len(days)} days.")
