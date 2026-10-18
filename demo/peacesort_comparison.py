"""ManimGL algorithm comparison, synchronized by key comparisons, not CPU time.

From demo/: uv run manimgl peacesort_comparison.py PeacesortComparison -w
Optional: PEACESORT_N=24 PEACESORT_PATTERN=random PEACESORT_SEED=17
          PEACESORT_FRAMES=150 PEACESORT_SECONDS=16
Scene PeacesortComparisonAll includes heap, Timsort variant and both LC directions.
"""
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.comparison_trace import DEFAULT_ALGORITHMS, NAMES, build_trace, dataset, comparison_counts, playback_schedule
from PIL import Image, ImageDraw, ImageFont
from manimlib import Scene, ImageMobject, FRAME_WIDTH, ORIGIN

W, H = 1600, 900
BG, CARD, FG, MUTED = '#0b1220', '#131f32', '#edf3ff', '#93a5bf'
BLUE, GOLD, GREEN = '#67adff', '#ffd166', '#5bdbab'
COLORS = ['#67adff', '#ba9aff', '#ff9980', '#65dac7', '#e99bc9', '#c6d675']


def font(size, bold=False):
    paths = (['/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
             if bold else ['/System/Library/Fonts/Supplemental/Arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for path in paths:
        if Path(path).exists(): return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def bars(draw, values, box, maximum, compared=(), colors=None, color=BLUE, slots=None):
    x, y, width, height = box
    if not values: return
    slots = len(values) if slots is None else slots
    columns = min(slots, max(1, int(width // 2)))
    step = width / columns
    for column in range(columns):
        begin = column * slots // columns
        end = min(len(values), (column + 1) * slots // columns)
        if begin >= len(values): break
        chunk = values[begin:end]
        value = sum(chunk) / len(chunk)
        fill = GOLD if any(v in compared for v in chunk) else (colors[begin] if colors else color)
        bar_height = max(2, height * value / maximum)
        draw.rectangle((x + column * step, y + height - bar_height,
                        x + (column + 1) * step - max(.5, step * .12), y + height), fill=fill)


def render_frame(values, traces, budget, pattern, seed, focus=False):
    image = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(image)
    d.text((42, 24), 'PEACESORT  /  SORTING COMPARISON', font=font(34, True), fill=FG)
    d.text((44, 73), f'Same input: n={len(values)}  |  {pattern}  |  seed={seed}  |  comparison budget={budget}', font=font(21), fill=MUTED)
    rows = (len(traces) + 2) // 3
    card_w, card_h = 492, (686 - (rows - 1) * 16) // rows
    for index, trace in enumerate(traces):
        x, y = 42 + (index % 3) * 512, 126 + (index // 3) * (card_h + 16)
        state = trace.at(budget)
        accent = GREEN if state.done else (COLORS[1] if trace.name.startswith('peacesort') else '#33465f')
        d.rounded_rectangle((x, y, x + card_w, y + card_h), radius=16, fill=CARD, outline=accent, width=2)
        d.text((x + 18, y + 14), NAMES[trace.name], font=font(23, True), fill=FG)
        count = min(budget, trace.comparisons)
        status = f'DONE / {count:,} comparisons' if state.done else f'{count:,} / {trace.comparisons:,} comparisons'
        d.text((x + 18, y + 46), status, font=font(18), fill=GREEN if state.done else MUTED)
        bar_height = card_h - 170
        colors = None
        if state.runs:
            colors = [COLORS[i % len(COLORS)] for i, run in enumerate(state.runs) for _ in run]
            colors += ['#33465f'] * (len(state.values) - len(colors))
        bars(d, state.values, (x + 18, y + 80, card_w - 36, bar_height), max(values),
             state.compared, colors, GREEN if state.done else BLUE)
        d.text((x + 18, y + card_h - 84), state.phase, font=font(15), fill=MUTED)
        if state.output:
            # Fixed N slots reveal partial output, rather than stretching it.
            out_y = y + card_h - 52
            bars(d, state.output, (x + 18, out_y, card_w - 36, 24),
                 max(values), color=GREEN, slots=len(values))
        elif state.runs:
            d.text((x + 18, y + card_h - 47), f'{len(state.runs)} LCs  /  output: 0 values', font=font(16), fill=MUTED)
        progress = 1 if state.done else count / max(1, trace.comparisons)
        d.rectangle((x + 18, y + card_h - 12, x + 18 + (card_w - 36) * progress, y + card_h - 9), fill=accent)
    d.text((44, 836), 'Shared comparison budget / EARLY PHASE SLOWED / not CPU time' if focus else 'One shared comparison budget. This is NOT a wall-clock speed benchmark.', font=font(22, True), fill=GOLD)
    d.text((44, 869), 'Yellow: compared values   |   Green: output / finished   |   Large N: bars average adjacent values   |   Frames sampled', font=font(17), fill=MUTED)
    return image


class PeacesortComparison(Scene):
    algorithms = DEFAULT_ALGORITHMS

    def construct(self):
        n = int(os.environ.get('PEACESORT_N', '24'))
        frames = int(os.environ.get('PEACESORT_FRAMES', '150'))
        seconds = float(os.environ.get('PEACESORT_SECONDS', '16'))
        if not 4 <= n <= 2000 or not 2 <= frames <= 600 or not 1 <= seconds <= 120:
            raise ValueError('Require N=4..2000, FRAMES=2..600, SECONDS=1..120')
        pattern = os.environ.get('PEACESORT_PATTERN', 'random')
        seed = int(os.environ.get('PEACESORT_SEED', '17'))
        values = dataset(n, pattern, seed)
        counts = comparison_counts(self.algorithms, values)
        timeline = os.environ.get('PEACESORT_TIMELINE', 'focus' if n > 96 else 'linear')
        if timeline not in ('linear', 'focus'):
            raise ValueError('PEACESORT_TIMELINE must be linear or focus')
        hold = float(os.environ.get('PEACESORT_HOLD', '1' if timeline == 'focus' else '0'))
        if not 0 <= hold <= 10:
            raise ValueError('PEACESORT_HOLD must be 0..10 seconds')
        budgets, times, cutoff = playback_schedule(counts, frames, seconds, timeline == 'focus')
        focus = cutoff < max(counts.values()) + 1
        completions = {count + 1 for count in counts.values()}
        # Only these snapshots are stored. Every comparison still executes.
        traces = [build_trace(name, values, budgets) for name in self.algorithms]
        print('Verified comparison counts:', {t.name: t.comparisons for t in traces})
        if any(t.comparisons != counts[t.name] for t in traces):
            raise AssertionError('Trace count changed between passes')
        current = None
        with tempfile.TemporaryDirectory(prefix='peacesort-comparison-') as directory:
            for i, budget in enumerate(budgets):
                path = Path(directory) / f'{i:04d}.png'
                render_frame(values, traces, budget, pattern, seed, focus).save(path)
                frame = ImageMobject(str(path))
                frame.set_width(FRAME_WIDTH).move_to(ORIGIN)
                if current is not None: self.remove(current)
                self.add(frame)
                current = frame
                if i == 0: self.wait(2)
                if budget in completions and hold: self.wait(hold)
                if i + 1 < len(budgets):
                    self.wait(times[i + 1] - times[i])
            self.wait(4)


class PeacesortComparisonAll(PeacesortComparison):
    algorithms = ('peacesort_ascending', 'peacesort_descending', 'quick_3way',
                  'merge', 'heap', 'timsort_no_gallop', 'insertion', 'bubble', 'selection')
