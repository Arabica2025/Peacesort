"""ManimGL four-panel animation of Peacesort.

Usage:
  uv run manimgl peacesort_manim_interactive_style.py PeacesortVisualizer
  uv run manimgl peacesort_manim_interactive_style.py PeacesortVisualizer -w

Configure with environment variables:
  PEACESORT_N=2000              (default; 8..2000)
  PEACESORT_PATTERN=random      (random|ascending|descending|near|two|duplicates)
  PEACESORT_TOP_K=100           (optional; default all output)
  PEACESORT_FRAMES=130          (approx. maximum displayed frames)
  PEACESORT_SEED=20261017

This is a scripted ManimGL scene, not a browser widget. Play/pause via the
ManimGL window; edit environment variables to generate another animation.
"""
import os
import tempfile
from pathlib import Path
import random
import heapq
from bisect import bisect_left
from math import ceil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from manimlib import Scene, ImageMobject, FRAME_WIDTH, ORIGIN

W, H = 1600, 900
BG = (15, 23, 42)
PANEL = (25, 36, 57)
GRID = (62, 76, 100)
FG = (236, 244, 255)
SECOND = (168, 188, 215)
BLUE = (83, 155, 245)
YELLOW = (255, 208, 73)
GREEN = (74, 211, 145)
COLORS = [(87,155,250),(255,151,78),(167,139,250),(52,211,153),
          (245,114,177),(250,204,21),(45,212,191),(165,180,252),
          (251,146,60),(132,204,22),(244,114,182),(56,189,248)]


def font(size, bold=False):
    paths = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else
             ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf"])
    for path in paths:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

F_BIG, F_HEAD, F_BODY, F_SMALL = font(34, True), font(23, True), font(20), font(17)


def dataset(n, pattern, seed):
    rng = random.Random(seed)
    a = list(range(1, n+1))
    if pattern == 'random':
        rng.shuffle(a)
    elif pattern == 'ascending':
        pass
    elif pattern == 'descending':
        a.reverse()
    elif pattern == 'near':
        for _ in range(max(1, n//100)):
            i, j = rng.randrange(n), rng.randrange(n)
            a[i], a[j] = a[j], a[i]
    elif pattern == 'two':
        a = [v for i in range(1, n+1, 2) for v in (i+1, i) if v <= n]
    elif pattern == 'duplicates':
        a = [rng.randrange(1, min(100, n)+1) for _ in range(n)]
    else:
        raise ValueError(f'Unknown pattern: {pattern}')
    return a


def assign_runs(values):
    camps, tails, assignment = [], [], []
    for x in values:
        j = bisect_left(tails, -x)
        if j == len(camps):
            camps.append([x]); tails.append(-x)
        else:
            camps[j].append(x); tails[j] = -x
        assignment.append(j)
    return camps, assignment


def choose_direction(a):
    n = len(a)
    if n <= 128:
        return a, 'forward'
    sample = a[:min(n,512)]
    prefer_back = 1.5 * len(assign_runs(list(reversed(sample)))[0]) < len(assign_runs(sample)[0])
    if not prefer_back:
        return a, 'forward'
    backward = list(reversed(a))
    back_count = len(assign_runs(backward)[0])
    if back_count <= max(8, n//256):
        return backward, 'backward'
    forward_count = len(assign_runs(a)[0])
    if back_count < forward_count:
        return backward, 'backward'
    return a, 'forward'


def event_trace(a, limit, budget):
    order, direction = choose_direction(a)
    runs, assignment = assign_runs(order)
    n = len(order)
    # Keep complete logical trace, with small cheap event tuples.
    # Merge outputs are accumulated once, then sliced at sampled indices.
    heap = [(r[0], i, 0) for i, r in enumerate(runs)]
    heapq.heapify(heap)
    output, merge_states = [], []
    for _ in range(limit):
        value, run_id, offset = heapq.heappop(heap)
        output.append(value)
        if offset+1 < len(runs[run_id]):
            heapq.heappush(heap, (runs[run_id][offset+1], run_id, offset+1))
        # save only heads (run index and value). At 2000 elems and ~100 runs,
        # this is modest; one frame samples the nearest real state.
        merge_states.append((run_id, value, sorted([(v,r) for v,r,_ in heap])))
    # Runtime trace correctness (including duplicates)
    assert output == sorted(a)[:limit]
    part_steps = max(2, budget//2)
    merge_steps = max(2, budget-part_steps)
    sample = lambda amount, steps: sorted(set([0, amount] + [round(i*amount/steps) for i in range(steps+1)]))
    events = [('partition', i) for i in sample(n, part_steps)]
    events += [('merge', i) for i in sample(limit, merge_steps)]
    events += [('complete', limit)]
    return {'order': order, 'runs':runs, 'assigned':assignment,
            'output':output, 'merge_states':merge_states, 'direction':direction,
            'events':events, 'limit':limit}


def draw_bars(d, values, rect, vmax, colors, highlight=-1, count=None):
    x0,y0,x1,y1 = rect
    count = count if count is not None else len(values)
    if count <= 0: return
    ww, hh = x1-x0, y1-y0
    for i, value in enumerate(values):
        x = x0+round(i*ww/count)
        nx = x0+round((i+1)*ww/count)
        bh = max(2, int(hh*value/max(1,vmax)))
        color = YELLOW if i == highlight else (colors[i] if isinstance(colors,list) else colors)
        d.rectangle((x,y1-bh,max(x,nx-1),y1), fill=color)


def render_frame(a, t, phase, step, total):
    order = t['order']; n=len(a); limit=t['limit']; k=len(t['runs'])
    im = Image.new('RGB', (W,H), BG); d=ImageDraw.Draw(im)
    d.text((48,26),'Peacesort',font=F_BIG,fill=FG)
    d.text((48,76),'Binary-search LC partition  /  lazy k-way merge',font=F_BODY,fill=SECOND)
    d.text((1180,40),f'n = {n:,}   k = {k}   {t["direction"]}',font=F_BODY,fill=SECOND)
    # Four separate regions, fixed heights; labels never overlap graph axes.
    panels=[(48,139,1552,296,'INPUT ARRAY'),
            (48,310,1552,468,'LC PARTITION / ASSIGNMENT'),
            (48,482,1552,640,'CURRENT MERGE CANDIDATES'),
            (48,654,1552,812,'SORTED OUTPUT STREAM')]
    for x0,y0,x1,y1,name in panels:
        d.rounded_rectangle((x0,y0,x1,y1),radius=12,fill=PANEL,outline=GRID,width=2)
        d.text((x0+18,y0+12),name,font=F_SMALL,fill=SECOND)
    maxval=max(a)
    active = step-1 if phase=='partition' and step else -1
    input_colors = [BLUE if i>=step and phase=='partition' else (83,105,139) for i in range(n)] if phase=='partition' else BLUE
    draw_bars(d,order,(70,182,1530,276),maxval,input_colors,active)
    available = step if phase=='partition' else n
    if available:
        assigned_colors=[COLORS[t['assigned'][i]%len(COLORS)] for i in range(available)]
        draw_bars(d,order[:available],(70,354,1530,448),maxval,assigned_colors,count=n)
    d.text((1270,321),f'{len(set(t["assigned"][:available]))} LCs built',font=F_SMALL,fill=FG)
    if phase=='partition':
        heads=[]
    elif step>0 and t['merge_states']:
        heads=t['merge_states'][step-1][2]
    else:
        heads=sorted((r[0],i) for i,r in enumerate(t['runs']))
    if heads:
        vals=[v for v,_ in heads]
        clrs=[YELLOW if i==0 else COLORS[r%len(COLORS)] for i,(_,r) in enumerate(heads)]
        draw_bars(d,vals,(70,526,1530,620),maxval,clrs,count=len(vals))
    d.text((1250,494),f'{len(heads)} active heads',font=F_SMALL,fill=FG)
    produced=step if phase in ('merge','complete') else 0
    if produced:
        draw_bars(d,t['output'][:produced],(70,698,1530,792),maxval,GREEN,count=n)
    d.text((1238,666),f'{produced:,} / {limit:,} yielded',font=F_SMALL,fill=FG)
    if phase=='partition':
        desc=f'Partitioning {step:,}/{n:,} elements — binary-search placement into LCs'
    elif phase=='merge':
        desc=f'Lazy merge: yielded {step:,}/{limit:,} elements; next head is consumed on demand'
    else:
        desc=('Complete — all elements emitted' if limit==n else f'Top-{limit:,} consumed — remaining values not requested')
    d.text((48,835),desc,font=F_BODY,fill=FG)
    d.rectangle((48,873,1552,880),fill=GRID)
    fraction=total and min(1, (t['events'].index((phase,step)))/(max(1,total-1)))
    d.rectangle((48,873,48+round(1504*fraction),880),fill=GREEN)
    return np.asarray(im)


class PeacesortVisualizer(Scene):
    def construct(self):
        n = max(8,min(2000,int(os.environ.get('PEACESORT_N','2000'))))
        pattern=os.environ.get('PEACESORT_PATTERN','random').lower()
        budget=max(12,min(500,int(os.environ.get('PEACESORT_FRAMES','130'))))
        seed=int(os.environ.get('PEACESORT_SEED','20261017'))
        data=dataset(n,pattern,seed)
        top_k=os.environ.get('PEACESORT_TOP_K','').strip()
        limit=n if not top_k else max(1,min(n,int(top_k)))
        trace=event_trace(data,limit,budget)
        events=trace['events']
        # At n=2,000 this uses approximately 130 fully rendered bar states;
        # the underlying algorithm processes and emits ALL 2,000 items.
        current=None
        temp_frames = tempfile.TemporaryDirectory(prefix="lcs_manim_")
        frame_dir = Path(temp_frames.name)
        try:
            for i,(phase,step) in enumerate(events):
                rgb=render_frame(data,trace,phase,step,len(events))
                image_file = frame_dir / f"frame_{i:05d}.png"
                Image.fromarray(rgb, mode="RGB").save(image_file)
                frame=ImageMobject(str(image_file))
                frame.set_width(FRAME_WIDTH)
                frame.move_to(ORIGIN)
                if current is not None:
                    self.remove(current)
                self.add(frame)
                current=frame
                self.wait(0.055 if i>0 else 0.3)
            self.wait(1.5)
        finally:
            temp_frames.cleanup()
