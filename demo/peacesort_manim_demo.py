"""Readable 16:9 ManimGL demonstration of Peacesort (LC partition + lazy merge).

    uv run manimgl peacesort_manim_demo.py PeacesortStepByStep
    uv run manimgl peacesort_manim_demo.py PeacesortOverview -w

Uses the 3b1b `manimgl` distribution (`from manimlib import *`).
"""
from manimlib import *

DATA = [8, 3, 6, 1, 7, 2, 5, 4, 12, 9, 11, 10]
COLORS = [BLUE_B, TEAL_B, PURPLE_B, ORANGE, PINK, GREEN_B, YELLOW_B]


def partition(data):
    camps, neg_tails, placements = [], [], []
    for x in data:
        low, high = 0, len(neg_tails)
        while low < high:
            mid = (low + high)//2
            if neg_tails[mid] < -x:
                low = mid + 1
            else:
                high = mid
        if low == len(camps):
            camps.append([x]); neg_tails.append(-x)
        else:
            camps[low].append(x); neg_tails[low] = -x
        placements.append(low)
    return camps, placements


def merge_trace(camps, take=None):
    # Values are yielded on demand. This emits the same order as a lazy min-heap.
    import heapq
    q = [(camp[0], idx, 0) for idx, camp in enumerate(camps) if camp]
    heapq.heapify(q)
    events=[]
    limit=sum(map(len,camps)) if take is None else min(take,sum(map(len,camps)))
    for _ in range(limit):
        val, camp_i, off=heapq.heappop(q)
        events.append((val,camp_i,off))
        if off + 1 < len(camps[camp_i]):
            heapq.heappush(q,(camps[camp_i][off+1],camp_i,off+1))
    return events


class PeacesortBase(Scene):
    data = DATA
    top_k = None
    pace = 0.24

    def bar(self, value, color, width=0.40, maxheight=0.95):
        shape=Rectangle(width=width,height=max(0.12,value/max(self.data)*maxheight))
        shape.set_fill(color,opacity=1).set_stroke(WHITE,width=0.7)
        return shape

    def status(self, message):
        txt=Text(message,font_size=21)
        txt.set_color(GREY_A)
        txt.move_to([0,-3.53,0])
        if txt.get_width()>12.5: txt.set_width(12.5)
        if hasattr(self,'status_text'):
            self.remove(self.status_text)
        self.status_text=txt
        self.add(txt)

    def construct(self):
        camps, assign=partition(self.data)
        trace=merge_trace(camps,self.top_k)
        n=len(self.data)
        assert [x for x,_,_ in merge_trace(camps)]==sorted(self.data)

        title=Text('Peacesort',font_size=39)
        title.move_to([0,3.52,0])
        subtitle=Text('Preserve every element  |  LC partition  |  Lazy merge',font_size=19)
        subtitle.set_color(GREY_A).move_to([0,3.04,0])
        self.add(title,subtitle)

        panel_color=GREY_D
        def panel(label, y, height):
            frame=Rectangle(width=12.8,height=height)
            frame.set_stroke(panel_color,width=1).set_fill(BLACK,opacity=0)
            frame.move_to([0,y,0])
            tag=Text(label,font_size=20)
            tag.set_color(GREY_A)
            tag.move_to([-5.55,y+height/2-0.25,0])
            self.add(frame,tag)
            return frame

        panel('Input',1.85,1.64)   # y: 1.03..2.67
        panel('LC partition',-0.19,2.28) # y: -1.33..0.95
        panel('Lazy output',-2.57,1.52) # y: -3.33..-1.81

        input_bars=[]
        left=-4.4; span=8.95/max(1,n-1)
        for i,x in enumerate(self.data):
            b=self.bar(x,BLUE_C,0.45,0.91)
            b.move_to([left+i*span,1.20+b.get_height()/2,0])
            input_bars.append(b)
            label=Integer(x,font_size=16).move_to([left+i*span,1.11,0])
            self.add(b,label)
        self.status('Binary-search placement into nondecreasing LCs')
        # Camp rows use fixed horizontal slots; bars share a baseline per row.
        row_count=len(camps)
        row_y=[0.52- i*(1.58/max(1,row_count-1)) for i in range(row_count)]
        run_bars=[[] for _ in camps]
        for ci, y in enumerate(row_y):
            tag=Text(f'LC {ci+1}',font_size=18)
            tag.set_color(COLORS[ci%len(COLORS)])
            tag.move_to([-5.3,y,0])
            self.add(tag)
            guide=Line([-4.65,y-0.29,0],[5.9,y-0.29,0],stroke_color=GREY_D,stroke_width=0.8)
            self.add(guide)

        for i,(val,ci) in enumerate(zip(self.data,assign)):
            source=input_bars[i]
            source.set_fill(YELLOW,opacity=1)
            bar=self.bar(val,COLORS[ci%len(COLORS)],0.33,0.49)
            x=-4.23+0.60*len(run_bars[ci]); y=row_y[ci]
            bar.move_to([x,y-0.29+bar.get_height()/2,0])
            run_bars[ci].append(bar)
            self.status(f'Element {val} joins LC {ci+1}')
            self.play(TransformFromCopy(source,bar),run_time=self.pace)
            source.set_fill(BLUE_C,opacity=1)
        self.status('LCs are sorted internally; merge begins on consumer demand')
        self.wait(.4)

        out_y=-3.18
        output_bars=[]
        for j,(val,ci,offset) in enumerate(trace):
            src=run_bars[ci][offset]
            src.set_fill(YELLOW,opacity=1)
            b=self.bar(val,GREEN_C,0.39,0.84)
            xpos=-4.5+9.0*j/max(1,n-1)
            b.move_to([xpos,out_y+b.get_height()/2,0])
            output_bars.append(b)
            self.status(f'Yield {val} from LC {ci+1}  ({j+1}/{len(trace)})')
            self.play(TransformFromCopy(src,b),run_time=self.pace)
            src.set_fill(COLORS[ci%len(COLORS)],opacity=1)
        if len(trace)==n:
            self.status('Complete: all elements preserved and sorted')
        else:
            self.status(f'Top-{len(trace)} requested: stream stops on demand')
        self.wait(1)


class PeacesortStepByStep(PeacesortBase):
    pace=0.42


class PeacesortOverview(PeacesortBase):
    pace=0.12


class PeacesortTopKDemo(PeacesortBase):
    top_k=5
    pace=0.24
