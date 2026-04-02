"""
GRID CHALLENGE  –  QUESTION_2_final.py
========================================
MOUSE-ONLY click-based gameplay.

Pattern 1 : HORIZONTAL hourglass X-shapes scroll DOWN the grid.
            The X is wide at left/right edges, narrow at the centre column.
            BLUE point cells are scattered RANDOMLY across the whole grid
            (some inside the hourglass, some outside) — like the screenshot.
            Click BLUE → +10.  Click RED → blink + lose life.

Pattern 2 : RED cells move randomly across grid with GREEN safe boundaries.
            GREEN cells form safe zones (boundaries and stripes).
            BLUE point cells spawn randomly in GREEN safe cells.
            Click BLUE → +10.  Click RED → blink + lose life.
"""

import pygame, sys, random, time, math
from enum import Enum

pygame.init()

# ── Screen ───────────────────────────────────────────────────────────────────
SCREEN_W = 1100
SCREEN_H = 820
screen   = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("GRID CHALLENGE")

# ── Palette ───────────────────────────────────────────────────────────────────
BG         = (8,   10,  18)
PANEL_BG   = (14,  16,  28)
PANEL_EDGE = (38,  42,  68)
C_BLACK    = (14,  16,  28)
C_BLACK_E  = (28,  30,  48)
C_RED      = (210,  30,  30)
C_RED_E    = (255,  75,  75)
C_RED_G    = (100,   8,   8)
C_BLUE     = (35,  105, 250)
C_BLUE_E   = (95,  165, 255)
C_BLUE_G   = (12,   45, 155)
C_GREEN    = (30,  185,  75)
C_GREEN_E  = (55,  230, 115)
C_GREEN_G  = (12,  100,  42)
WHITE  = (255, 255, 255)
GRAY   = (100, 105, 130)
LGRAY  = (170, 175, 200)
YELLOW = (255, 215,   0)
CYAN   = (  0, 220, 220)
RED    = (210,  30,  30)
GREEN  = ( 30, 185,  75)

# ── Fonts ─────────────────────────────────────────────────────────────────────
F10 = pygame.font.Font(None, 18)
F14 = pygame.font.Font(None, 22)
F18 = pygame.font.Font(None, 28)
F24 = pygame.font.Font(None, 36)
F32 = pygame.font.Font(None, 46)
F64 = pygame.font.Font(None, 86)

PANEL_W = 240
GRID_W  = SCREEN_W - PANEL_W
GRID_H  = SCREEN_H

EMPTY  = 0
DANGER = 1
POINT  = 2
SAFE   = 3

class GS(Enum):
    PLAYING = 0; WIN = 1; LOSE = 2

# ═════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═════════════════════════════════════════════════════════════════════════════
def rrect(surf, color, rect, r=8, bw=0, bc=None):
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if bw and bc:
        pygame.draw.rect(surf, bc, rect, bw, border_radius=r)

def lerp_color(a, b, t):
    return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

def pulse(t, spd=2.0):
    return 0.5 + 0.5*math.sin(t*spd)

# ═════════════════════════════════════════════════════════════════════════════
#  Particle
# ═════════════════════════════════════════════════════════════════════════════
class Particle:
    def __init__(self, x, y, color):
        a = random.uniform(0, math.tau); s = random.uniform(2.0, 5.5)
        self.x=float(x); self.y=float(y)
        self.vx=math.cos(a)*s; self.vy=math.sin(a)*s-random.uniform(0,2.5)
        self.life=self.max_life=random.randint(18,38)
        self.color=color; self.sz=random.randint(2,5)
    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.vy+=0.18; self.life-=1
    def draw(self, surf):
        if self.life<=0: return
        al=int(255*self.life/self.max_life)
        s=pygame.Surface((self.sz*2,self.sz*2),pygame.SRCALPHA)
        pygame.draw.circle(s,(*self.color,al),(self.sz,self.sz),self.sz)
        surf.blit(s,(int(self.x)-self.sz,int(self.y)-self.sz))

# ═════════════════════════════════════════════════════════════════════════════
#  PATTERN 1 – Horizontal Hourglass scrolling DOWN + random blue scatter
#
#  The hourglass X shape is HORIZONTAL:
#    • The X arms go from LEFT edge → pinch at CENTRE COLUMN → RIGHT edge
#    • Wide at top row, narrowing to meet at mid row, widening to bottom row
#
#  Example (HOUR_ROWS=9, cols=10, centre col=4.5):
#
#    row 0:  R . . . . . . . . R    ← arms at col 0 and col 9 (far edges)
#    row 1:  . R . . . . . . R .    ← arms move inward
#    row 2:  . . R . . . . R . .
#    row 3:  . . . R . . R . . .
#    row 4:  . . . . R R . . . .    ← waist at centre (arms touch)
#    row 5:  . . . R . . R . . .
#    row 6:  . . R . . . . R . .
#    row 7:  . R . . . . . . R .
#    row 8:  R . . . . . . . . R    ← arms back at edges
#
#  BLUE cells are randomly scattered across ALL non-danger cells,
#  both inside the X and in the gap rows.
# ═════════════════════════════════════════════════════════════════════════════
class Pattern1Game:
    SCROLL_SPEED         = 48    # px / second  (scrolls DOWN)
    HOUR_ROWS            = 10    # rows per hourglass block
    GAP_ROWS             = 5     # rows of gap between blocks
    ARM_THICKNESS        = 1.2   # arm half-width in cells
    BLUE_DENSITY_HOURGLASS = 0.18  # fraction of safe cells inside X → blue
    BLUE_DENSITY_GAP       = 0.28  # fraction of gap cells → blue

    def __init__(self, rows, cols, cw, ch):
        self.rows=rows; self.cols=cols; self.cw=cw; self.ch=ch
        self.score=0; self.lives=5; self.time_left=50.0
        self.last_t=time.time(); self.state=GS.PLAYING
        self.anim_t=0.0; self.scroll_px=0.0
        self.points_clicked=0; self.target_points=25
        self.blink={}; self.particles=[]; self.flash_col=None; self.flash_a=0

        # Build a tall world strip we scroll through
        self.WORLD_ROWS = (self.HOUR_ROWS + self.GAP_ROWS) * 7
        self._build_world()

    # ── hourglass danger check ────────────────────────────────────────────────
    def _is_danger(self, local_row, col):
        """
        Within one hourglass block (HOUR_ROWS rows × self.cols cols):
        The X arms travel from left→centre and right→centre.
        At local_row=0 and local_row=HOUR_ROWS-1 the arms are at col 0 and
        col cols-1.  At local_row=mid they meet at the centre column.
        """
        mid_row = (self.HOUR_ROWS - 1) / 2.0
        mid_col = (self.cols - 1) / 2.0
        # How far this row is from the centre (0 at waist, 1 at top/bottom)
        t = abs(local_row - mid_row) / mid_row if mid_row > 0 else 0
        # Arm positions: at t=1 → col 0 and col cols-1; at t=0 → mid_col
        arm_left  = mid_col * (1.0 - t)
        arm_right = (self.cols - 1) - arm_left
        th = self.ARM_THICKNESS
        return abs(col - arm_left) <= th or abs(col - arm_right) <= th

    # ── world generation ──────────────────────────────────────────────────────
    def _build_world(self):
        cols   = self.cols
        period = self.HOUR_ROWS + self.GAP_ROWS
        rng    = random.Random(99)   # reproducible world

        self.world = [[EMPTY]*cols for _ in range(self.WORLD_ROWS)]

        for wr in range(self.WORLD_ROWS):
            p = wr % period
            if p < self.HOUR_ROWS:
                # ── hourglass block ───────────────────────────────────────
                local_row = p
                for c in range(cols):
                    if self._is_danger(local_row, c):
                        self.world[wr][c] = DANGER
                    else:
                        # randomly scatter blue inside the X
                        if rng.random() < self.BLUE_DENSITY_HOURGLASS:
                            self.world[wr][c] = POINT
            else:
                # ── gap between hourglasses ───────────────────────────────
                for c in range(cols):
                    if rng.random() < self.BLUE_DENSITY_GAP:
                        self.world[wr][c] = POINT

        # mutable live copy (so clicks can consume blue cells)
        self.world_live = [row[:] for row in self.world]

    # ── visible slice ─────────────────────────────────────────────────────────
    def get_grid(self):
        start_wr = int(self.scroll_px / self.ch)
        sub_py   = self.scroll_px - start_wr * self.ch
        grid = [
            self.world_live[(start_wr + r) % self.WORLD_ROWS][:]
            for r in range(self.rows)
        ]
        return grid, int(sub_py)

    # ── update ────────────────────────────────────────────────────────────────
    def update(self, dt):
        self.anim_t += dt
        if self.state == GS.PLAYING:
            now = time.time()
            self.time_left -= now - self.last_t; self.last_t = now
            if self.time_left <= 0:
                self.time_left = 0; self.state = GS.LOSE
            self.scroll_px += self.SCROLL_SPEED * dt

        for k in list(self.blink):
            self.blink[k] -= 1
            if self.blink[k] <= 0: del self.blink[k]
        self.flash_a = max(0, self.flash_a - 10)
        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    # ── click ─────────────────────────────────────────────────────────────────
    def handle_click(self, px, py):
        if self.state != GS.PLAYING: return
        scol = px // self.cw
        row  = py // self.ch
        if not (0<=row<self.rows and 0<=scol<self.cols): return

        grid, _ = self.get_grid()
        ct = grid[row][scol]

        start_wr = int(self.scroll_px / self.ch)
        wr = (start_wr + row) % self.WORLD_ROWS

        sx = scol*self.cw + self.cw//2
        sy = row *self.ch + self.ch//2

        if ct == POINT:
            self.world_live[wr][scol] = EMPTY
            self.score += 10; self.points_clicked += 1
            self.flash_col = C_BLUE_E; self.flash_a = 130
            for _ in range(18): self.particles.append(Particle(sx, sy, C_BLUE))
            if self.points_clicked >= self.target_points:
                self.state = GS.WIN

        elif ct == DANGER:
            self.lives -= 1
            self.blink[(row, scol)] = 22
            self.flash_col = C_RED_E; self.flash_a = 180
            for _ in range(20): self.particles.append(Particle(sx, sy, C_RED))
            if self.lives <= 0: self.state = GS.LOSE

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        grid, sub_py = self.get_grid()
        at = self.anim_t
        oy = -(sub_py % self.ch)   # smooth vertical scroll offset

        for r in range(self.rows):
            for c in range(self.cols):
                x    = c * self.cw
                y    = r * self.ch + oy
                rect = pygame.Rect(x, y, self.cw-1, self.ch-1)
                ct   = grid[r][c]
                blink_on = (r,c) in self.blink and (self.blink[(r,c)]//2)%2==0

                if blink_on:
                    base = WHITE; edge = (200,200,200)
                elif ct == DANGER:
                    t = pulse(at + r*0.09, 4.2)*0.38
                    base = lerp_color(C_RED, C_RED_E, t); edge = C_RED_G
                elif ct == POINT:
                    t = pulse(at + c*0.22 + r*0.14, 3.4)*0.45
                    base = lerp_color(C_BLUE, C_BLUE_E, t); edge = C_BLUE_G
                else:
                    base = C_BLACK; edge = C_BLACK_E

                pygame.draw.rect(screen, base, rect)
                pygame.draw.rect(screen, edge, rect, 1)

                if ct == POINT and not blink_on:
                    dr = max(2, min(self.cw, self.ch)//5)
                    gs = pygame.Surface((dr*6, dr*6), pygame.SRCALPHA)
                    al = int(55 + 60*pulse(at + c + r*0.6, 3.1))
                    pygame.draw.circle(gs, (*C_BLUE_E, al), (dr*3, dr*3), dr*2)
                    screen.blit(gs, (rect.centerx-dr*3, rect.centery-dr*3))
                    pygame.draw.circle(screen, C_BLUE_E, rect.center, dr)

                if self.cw >= 30 and self.ch >= 22:
                    ns = F10.render(str(r*self.cols+c+1), True, (45,48,72))
                    screen.blit(ns, (x+2, y+2))

        for p in self.particles: p.draw(screen)
        if self.flash_a > 0 and self.flash_col:
            fl = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
            fl.fill((*self.flash_col, min(self.flash_a, 75)))
            screen.blit(fl, (0, 0))
        pygame.draw.rect(screen, PANEL_EDGE, (0, 0, GRID_W, GRID_H), 2)


# ═════════════════════════════════════════════════════════════════════════════
#  PATTERN 2 – Random Moving Red + Green Safe Zones + Random Blue
# ═════════════════════════════════════════════════════════════════════════════
class Pattern2Game:
    MOVE_INTERVAL   = 0.45   # seconds between red cell moves
    SPAWN_INTERVAL  = 1.2    # seconds between new blue spawns
    NUM_RED_CELLS   = 0      # calculated from grid size
    MAX_BLUE_CELLS  = 0      # calculated

    def __init__(self, rows, cols, cell_w, cell_h):
        self.rows   = rows
        self.cols   = cols
        self.cell_w = cell_w
        self.cell_h = cell_h

        self.NUM_RED_CELLS  = max(4, (rows * cols) // 10)
        self.MAX_BLUE_CELLS = max(3, (rows * cols) // 15)

        self.score          = 0
        self.lives          = 5
        self.time_left      = 60.0
        self.last_t         = time.time()
        self.state          = GS.PLAYING
        self.particles      = []
        self.anim_t         = 0.0
        self.move_timer     = 0.0
        self.spawn_timer    = 0.0
        self.points_clicked = 0
        self.target_points  = max(10, (rows*cols)//12)
        self.blink          = {}
        self.flash_col      = None
        self.flash_a        = 0

        # grid: sets for each type
        self.green_cells = set()  # SAFE cells (green boundaries)
        self.red_cells   = set()
        self.blue_cells  = set()

        self._init_grid()

    def _all_cells(self):
        return {(r,c) for r in range(self.rows) for c in range(self.cols)}

    def _empty_cells(self):
        return self._all_cells() - self.green_cells - self.red_cells - self.blue_cells

    def _init_grid(self):
        """Initialize grid with green boundary pattern and red/blue cells."""
        # Create green boundaries (horizontal stripes and borders)
        for r in range(self.rows):
            for c in range(self.cols):
                # Top and bottom rows are green boundaries
                if r == 0 or r == self.rows - 1:
                    self.green_cells.add((r, c))
                # Left and right columns are green boundaries
                elif c == 0 or c == self.cols - 1:
                    self.green_cells.add((r, c))
                # Create horizontal green stripes every 3 rows
                elif r % 3 == 0:
                    self.green_cells.add((r, c))
                # Create vertical green stripes every 4 columns
                elif c % 4 == 0:
                    self.green_cells.add((r, c))
        
        # Add random red cells in non-green areas
        all_positions = list(self._all_cells() - self.green_cells)
        random.shuffle(all_positions)
        self.red_cells = set(all_positions[:self.NUM_RED_CELLS])
        
        # Add initial blue cells in green zones
        green_list = list(self.green_cells - self.red_cells)
        random.shuffle(green_list)
        blue_count = min(self.MAX_BLUE_CELLS, len(green_list))
        self.blue_cells = set(green_list[:blue_count])

    def _move_red(self):
        """Move each red cell to a random adjacent empty cell."""
        dirs = [(-1,0),(1,0),(0,-1),(0,1)]
        new_red = set()
        occupied = self.red_cells | self.blue_cells
        moved = set()

        red_list = list(self.red_cells)
        random.shuffle(red_list)

        for (r,c) in red_list:
            random.shuffle(dirs)
            moved_ok = False
            for dr,dc in dirs:
                nr,nc = r+dr, c+dc
                if 0<=nr<self.rows and 0<=nc<self.cols:
                    target = (nr,nc)
                    # Can move into green or empty, but not into other reds or blues
                    if target not in occupied and target not in new_red:
                        new_red.add(target)
                        moved.add((r,c))
                        moved_ok = True
                        break
            if not moved_ok:
                new_red.add((r,c))   # stay put

        self.red_cells = new_red

    def _spawn_blue(self):
        """Spawn a new blue cell in a random green safe cell."""
        if len(self.blue_cells) >= self.MAX_BLUE_CELLS:
            return
        # Only spawn in green cells that are not occupied
        available = self.green_cells - self.red_cells - self.blue_cells
        if available:
            self.blue_cells.add(random.choice(list(available)))

    # ── update ────────────────────────────────────────────────────────────────
    def update(self, dt):
        self.anim_t += dt
        if self.state == GS.PLAYING:
            now = time.time()
            self.time_left -= now - self.last_t
            self.last_t = now
            if self.time_left <= 0:
                self.time_left = 0
                self.state = GS.LOSE

            self.move_timer  += dt
            self.spawn_timer += dt

            if self.move_timer >= self.MOVE_INTERVAL:
                self.move_timer = 0.0
                self._move_red()

            if self.spawn_timer >= self.SPAWN_INTERVAL:
                self.spawn_timer = 0.0
                self._spawn_blue()

        for k in list(self.blink):
            self.blink[k] -= 1
            if self.blink[k] <= 0:
                del self.blink[k]

        if self.flash_a > 0:
            self.flash_a = max(0, self.flash_a - 12)

        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    # ── click ─────────────────────────────────────────────────────────────────
    def handle_click(self, px, py):
        if self.state != GS.PLAYING: return
        col = px // self.cell_w
        row = py // self.cell_h
        if not (0<=row<self.rows and 0<=col<self.cols): return
        cell = (row, col)
        sx = col*self.cell_w + self.cell_w//2
        sy = row*self.cell_h + self.cell_h//2

        if cell in self.blue_cells:
            self.blue_cells.remove(cell)
            self.score += 10
            self.points_clicked += 1
            self.flash_col = C_BLUE_E
            self.flash_a = 150
            for _ in range(18):
                self.particles.append(Particle(sx, sy, C_BLUE))
            if self.points_clicked >= self.target_points:
                self.state = GS.WIN
        elif cell in self.red_cells:
            self.lives -= 1
            self.blink[cell] = 20
            self.flash_col = C_RED_E
            self.flash_a = 180
            for _ in range(22):
                self.particles.append(Particle(sx, sy, C_RED))
            if self.lives <= 0:
                self.state = GS.LOSE

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        at = self.anim_t
        for r in range(self.rows):
            for c in range(self.cols):
                x = c * self.cell_w
                y = r * self.cell_h
                rect = pygame.Rect(x, y, self.cell_w-1, self.cell_h-1)
                cell = (r,c)

                blink_on = cell in self.blink and (self.blink[cell]//2)%2==0

                if blink_on:
                    base = (255,255,255)
                    edge = (200,200,200)
                elif cell in self.red_cells:
                    t = pulse(at + r*0.1 + c*0.07, 4.5)*0.35
                    base = lerp_color(C_RED, C_RED_E, t)
                    edge = C_RED_G
                elif cell in self.blue_cells:
                    t = pulse(at + c*0.22 + r*0.18, 3.2)*0.45
                    base = lerp_color(C_BLUE, C_BLUE_E, t)
                    edge = C_BLUE_G
                elif cell in self.green_cells:
                    t = pulse(at + r*0.08 + c*0.06, 2.8)*0.25
                    base = lerp_color(C_GREEN, C_GREEN_E, t)
                    edge = C_GREEN_G
                else:
                    base = C_BLACK
                    edge = C_BLACK_E

                pygame.draw.rect(screen, base, rect)
                pygame.draw.rect(screen, edge, rect, 1)

                # glow effects
                if cell in self.blue_cells and not blink_on:
                    dr = max(2, min(self.cell_w, self.cell_h)//5)
                    gs = pygame.Surface((dr*6,dr*6), pygame.SRCALPHA)
                    al = int(65+55*pulse(at+c+r*0.7, 3.0))
                    pygame.draw.circle(gs, (*C_BLUE_E, al), (dr*3,dr*3), dr*2)
                    screen.blit(gs, (rect.centerx-dr*3, rect.centery-dr*3))
                    pygame.draw.circle(screen, C_BLUE_E, rect.center, dr)
                elif cell in self.green_cells and not blink_on:
                    dr = max(1, min(self.cell_w, self.cell_h)//8)
                    pygame.draw.circle(screen, C_GREEN_E, rect.center, dr, 1)

                # cell number
                if self.cell_w >= 28 and self.cell_h >= 20:
                    ns = F10.render(str(r*self.cols+c+1), True, (50,55,80))
                    screen.blit(ns, (x+2, y+2))

        for p in self.particles: p.draw(screen)
        if self.flash_a > 0 and self.flash_col:
            fl = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
            fl.fill((*self.flash_col, self.flash_a))
            screen.blit(fl, (0,0))

        pygame.draw.rect(screen, PANEL_EDGE, (0,0,GRID_W,GRID_H), 2)


# ═════════════════════════════════════════════════════════════════════════════
#  Game Manager
# ═════════════════════════════════════════════════════════════════════════════
class GameManager:
    def __init__(self, rows, cols):
        self.rows=rows; self.cols=cols
        self.cw=GRID_W//cols; self.ch=GRID_H//rows
        self.pat=1; self._build()

    def _build(self):
        self.g1=Pattern1Game(self.rows,self.cols,self.cw,self.ch)
        self.g2=Pattern2Game(self.rows,self.cols,self.cw,self.ch)
        self.current=self.g1

    def restart(self):
        self.pat=1; self._build(); self.current=self.g1

    def force_pattern(self, p):
        self.pat=p; self._build()
        self.current=self.g1 if p==1 else self.g2

    def update(self, dt):
        self.current.update(dt)
        if self.pat==1 and self.current.state==GS.WIN:
            sc=self.current.score; lv=max(1,self.current.lives)
            self.pat=2; self._build()
            self.g2.score=sc; self.g2.lives=lv; self.current=self.g2

    def handle_click(self, px, py): self.current.handle_click(px,py)

    @property
    def state(self):     return self.current.state
    @property
    def score(self):     return self.current.score
    @property
    def lives(self):     return self.current.lives
    @property
    def time_left(self): return self.current.time_left

    def draw(self): self.current.draw()


# ═════════════════════════════════════════════════════════════════════════════
#  Side Panel
# ═════════════════════════════════════════════════════════════════════════════
class Panel:
    PX = GRID_W

    @staticmethod
    def draw(gm, at):
        px=Panel.PX
        pygame.draw.rect(screen,PANEL_BG,(px,0,PANEL_W,SCREEN_H))
        pygame.draw.line(screen,PANEL_EDGE,(px,0),(px,SCREEN_H),2)
        cx=px+PANEL_W//2; y=18

        tc=lerp_color(YELLOW,CYAN,pulse(at,0.8))
        for word in ["GRID","CHALLENGE"]:
            s=F32.render(word,True,tc)
            screen.blit(s,s.get_rect(center=(cx,y))); y+=34
        y+=4

        pname="HOURGLASS" if gm.pat==1 else "GREEN BOUNDARY"
        br=pygame.Rect(px+12,y,PANEL_W-24,28)
        bc=(28,95,195) if gm.pat==1 else (38,118,48)
        rrect(screen,bc,br,8,1,WHITE)
        lb=F14.render(f"P{gm.pat} · {pname}",True,WHITE)
        screen.blit(lb,lb.get_rect(center=br.center)); y+=38

        for txt,col in [("Click BLUE  →  +10 pts",C_BLUE_E),
                        ("Click RED   →  -1 life!",C_RED_E)]:
            s=F14.render(txt,True,col)
            screen.blit(s,s.get_rect(center=(cx,y))); y+=18
        y+=4

        g=gm.current
        if hasattr(g,'target_points') and g.target_points>0:
            ratio=min(1.0,g.points_clicked/g.target_points)
            pw=PANEL_W-28; ph=14
            rrect(screen,(25,28,52),pygame.Rect(px+14,y,pw,ph),5)
            if ratio>0:
                rrect(screen,lerp_color(C_BLUE,C_BLUE_E,ratio),
                      pygame.Rect(px+14,y,int(pw*ratio),ph),5)
            info=F10.render(f"Blue clicks: {g.points_clicked}/{g.target_points}",True,LGRAY)
            screen.blit(info,info.get_rect(center=(cx,y+ph+8))); y+=ph+22

        screen.blit(F14.render("SCORE",True,GRAY),
                    F14.render("SCORE",True,GRAY).get_rect(centerx=cx,y=y)); y+=16
        screen.blit(F32.render(str(gm.score),True,YELLOW),
                    F32.render(str(gm.score),True,YELLOW).get_rect(centerx=cx,y=y)); y+=42

        screen.blit(F14.render("LIVES",True,GRAY),
                    F14.render("LIVES",True,GRAY).get_rect(centerx=cx,y=y)); y+=16
        hx=cx-(5*20)//2
        for li in range(5):
            hc=RED if li<gm.lives else (45,22,22)
            pygame.draw.polygon(screen,hc,[
                (hx+li*20+10,y+16),(hx+li*20,y+7),
                (hx+li*20+10,y+2),(hx+li*20+20,y+7)])
        y+=34

        screen.blit(F14.render("TIME",True,GRAY),
                    F14.render("TIME",True,GRAY).get_rect(centerx=cx,y=y)); y+=16
        bw=PANEL_W-28; bh=16
        tmax=50.0 if gm.pat==1 else 60.0
        rat=max(0,gm.time_left/tmax)
        rrect(screen,(28,32,54),pygame.Rect(px+14,y,bw,bh),5)
        if rat>0:
            rrect(screen,lerp_color((210,40,40),(45,210,95),min(1,rat*1.6)),
                  pygame.Rect(px+14,y,int(bw*rat),bh),5)
        screen.blit(F18.render(f"{max(0,gm.time_left):.1f}s",True,WHITE),
                    F18.render(f"{max(0,gm.time_left):.1f}s",True,WHITE).get_rect(centerx=cx,y=y+18))
        y+=46

        pygame.draw.line(screen,PANEL_EDGE,(px+14,y),(px+PANEL_W-14,y)); y+=10

        screen.blit(F14.render("SWITCH PATTERN",True,GRAY),
                    F14.render("SWITCH PATTERN",True,GRAY).get_rect(centerx=cx,y=y)); y+=18
        half=(PANEL_W-40)//2
        b1=pygame.Rect(px+14,y,half,30); b2=pygame.Rect(px+26+half,y,half,30)
        rrect(screen,(38,115,210) if gm.pat==1 else (26,36,65),b1,6,1,PANEL_EDGE)
        rrect(screen,(55,145,65) if gm.pat==2 else (26,36,65),b2,6,1,PANEL_EDGE)
        for btn,lbl_ in [(b1,"P1"),(b2,"P2")]:
            screen.blit(F18.render(lbl_,True,WHITE),
                        F18.render(lbl_,True,WHITE).get_rect(center=btn.center))
        y+=40

        rb=pygame.Rect(px+18,y,PANEL_W-36,30)
        rrect(screen,(34,145,68),rb,8,1,GREEN)
        screen.blit(F18.render("↺  RESTART",True,WHITE),
                    F18.render("↺  RESTART",True,WHITE).get_rect(center=rb.center)); y+=44

        pygame.draw.line(screen,PANEL_EDGE,(px+14,y),(px+PANEL_W-14,y)); y+=10

        screen.blit(F14.render("LEGEND",True,GRAY),
                    F14.render("LEGEND",True,GRAY).get_rect(centerx=cx,y=y)); y+=16
        for col_,lbl_ in [(C_BLUE,"Blue  = Click! +10 pts"),
                          (C_RED, "Red   = Danger! -1 ♥"),
                          (C_GREEN,"Green = Safe zone"),
                          (C_BLACK,"Black = Empty")]:
            pygame.draw.rect(screen,col_,(px+16,y+2,14,14),border_radius=3)
            pygame.draw.rect(screen,WHITE,(px+16,y+2,14,14),1,border_radius=3)
            screen.blit(F14.render(lbl_,True,LGRAY),(px+34,y+1)); y+=18
        y+=8

        pygame.draw.line(screen,PANEL_EDGE,(px+14,y),(px+PANEL_W-14,y)); y+=8
        if gm.pat==1:
            hints=["Red X scrolls DOWN ↓",
                   "Blue randomly scattered",
                   "inside & outside X arms",
                   "Click fast, they scroll away!"]
        else:
            hints=["Green = safe boundaries",
                   "Red moves every 0.45s",
                   "Blue spawns in GREEN cells",
                   "Click blue fast!"]
        for i,h in enumerate(hints):
            s=F14.render(h,True,C_BLUE_E if i==0 else LGRAY)
            screen.blit(s,s.get_rect(centerx=cx,y=y)); y+=15

        y+=6
        pygame.draw.line(screen,PANEL_EDGE,(px+14,y),(px+PANEL_W-14,y)); y+=8
        for c in ["R = Restart","1 / 2 = Switch pattern"]:
            s=F10.render(c,True,GRAY)
            screen.blit(s,s.get_rect(centerx=cx,y=y)); y+=14

        return b1,b2,rb


# ═════════════════════════════════════════════════════════════════════════════
#  Overlay
# ═════════════════════════════════════════════════════════════════════════════
def draw_overlay(gm, at):
    if gm.state not in(GS.WIN,GS.LOSE): return
    dim=pygame.Surface((GRID_W,GRID_H),pygame.SRCALPHA)
    dim.fill((0,0,0,175)); screen.blit(dim,(0,0))
    cx,cy=GRID_W//2,GRID_H//2
    if gm.state==GS.WIN:
        col=lerp_color(YELLOW,GREEN,pulse(at,1.5))
        label="YOU WIN!"; sub=f"Final Score: {gm.score}"; sub2="Press R to play again"
    else:
        col=lerp_color(RED,(255,120,0),pulse(at,2.0))
        label="GAME OVER"; sub=f"Score: {gm.score}"; sub2="Press R to try again"
    sh=F64.render(label,True,(18,18,18))
    screen.blit(sh,sh.get_rect(center=(cx+3,cy-42+3)))
    screen.blit(F64.render(label,True,col),
                F64.render(label,True,col).get_rect(center=(cx,cy-42)))
    screen.blit(F32.render(sub,True,WHITE),
                F32.render(sub,True,WHITE).get_rect(center=(cx,cy+22)))
    screen.blit(F18.render(sub2,True,LGRAY),
                F18.render(sub2,True,LGRAY).get_rect(center=(cx,cy+62)))


# ═════════════════════════════════════════════════════════════════════════════
#  Setup screen
# ═════════════════════════════════════════════════════════════════════════════
class Setup:
    def __init__(self):
        self.rows=15; self.cols=10
        self.active=None; self.buf=""
        self.done=False; self.anim_t=0.0; self.err=""

    def _rects(self):
        cx=SCREEN_W//2
        return(pygame.Rect(cx-60,320,120,44),
               pygame.Rect(cx-60,400,120,44),
               pygame.Rect(cx-110,500,220,52))

    def handle(self, e):
        if e.type==pygame.MOUSEBUTTONDOWN:
            rr,cr,sr=self._rects()
            if   rr.collidepoint(e.pos): self.active="rows"; self.buf=str(self.rows)
            elif cr.collidepoint(e.pos): self.active="cols"; self.buf=str(self.cols)
            elif sr.collidepoint(e.pos): self._go()
            else: self.active=None
        elif e.type==pygame.KEYDOWN:
            if self.active:
                if   e.key==pygame.K_RETURN:   self._commit()
                elif e.key==pygame.K_TAB:
                    self._commit()
                    self.active="cols" if self.active=="rows" else "rows"
                    self.buf=str(self.cols if self.active=="cols" else self.rows)
                elif e.key==pygame.K_BACKSPACE: self.buf=self.buf[:-1]
                elif e.unicode.isdigit() and len(self.buf)<3: self.buf+=e.unicode
            if e.key==pygame.K_RETURN and not self.active: self._go()

    def _commit(self):
        if not self.buf: return
        v=max(8,min(25,int(self.buf)))
        if self.active=="rows": self.rows=v
        else: self.cols=v
        self.buf=""; self.active=None

    def _go(self):
        if self.active: self._commit()
        if self.rows>=8 and self.cols>=8: self.done=True
        else: self.err="Minimum 8×8"

    def draw(self, dt):
        self.anim_t+=dt
        screen.fill(BG)
        for gx in range(0,SCREEN_W,50):
            pygame.draw.line(screen,(18,20,36),(gx,0),(gx,SCREEN_H))
        for gy in range(0,SCREEN_H,50):
            pygame.draw.line(screen,(18,20,36),(0,gy),(SCREEN_W,gy))
        cx,cy=SCREEN_W//2,SCREEN_H//2
        tc=lerp_color(YELLOW,CYAN,pulse(self.anim_t,0.7))
        for i,w in enumerate(["GRID","CHALLENGE"]):
            s=F64.render(w,True,tc)
            screen.blit(s,s.get_rect(center=(cx,cy-230+i*74)))
        inst=F18.render("MOUSE ONLY · Click BLUE boxes · Avoid RED!",True,C_BLUE_E)
        screen.blit(inst,inst.get_rect(center=(cx,cy-108)))
        rr,cr,sr=self._rects()
        def field(lbl,val,rect,active):
            screen.blit(F18.render(lbl,True,LGRAY),
                        F18.render(lbl,True,LGRAY).get_rect(right=rect.left-12,centery=rect.centery))
            rrect(screen,(20,23,40),rect,8,2,YELLOW if active else PANEL_EDGE)
            d=(self.buf+"▌") if active else str(val)
            screen.blit(F24.render(d,True,WHITE),
                        F24.render(d,True,WHITE).get_rect(center=rect.center))
        field("Rows (8–25)",self.rows,rr,self.active=="rows")
        field("Cols (8–25)",self.cols,cr,self.active=="cols")
        sp=lerp_color((26,152,72),(52,212,112),pulse(self.anim_t,1.5))
        rrect(screen,sp,sr,12,2,WHITE)
        screen.blit(F32.render("START GAME",True,WHITE),
                    F32.render("START GAME",True,WHITE).get_rect(center=sr.center))
        if self.err:
            screen.blit(F18.render(self.err,True,RED),
                        F18.render(self.err,True,RED).get_rect(center=(cx,sr.bottom+22)))
        screen.blit(F14.render("TAB=switch  |  ENTER=start",True,GRAY),
                    F14.render("TAB=switch  |  ENTER=start",True,GRAY).get_rect(center=(cx,SCREEN_H-38)))
        pygame.display.flip()


# ═════════════════════════════════════════════════════════════════════════════
#  Main
# ═════════════════════════════════════════════════════════════════════════════
def main():
    clock=pygame.time.Clock(); setup=Setup(); at=0.0
    while not setup.done:
        dt=clock.tick(60)/1000.0
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            setup.handle(e)
        setup.draw(dt)

    gm=GameManager(setup.rows,setup.cols)
    while True:
        dt=clock.tick(60)/1000.0; at+=dt
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            elif e.type==pygame.MOUSEBUTTONDOWN:
                mx,my=e.pos
                if mx<GRID_W:
                    gm.handle_click(mx,my)
                else:
                    b1,b2,rb=Panel.draw(gm,at)
                    if b1.collidepoint(e.pos): gm.force_pattern(1)
                    if b2.collidepoint(e.pos): gm.force_pattern(2)
                    if rb.collidepoint(e.pos): gm.restart()
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_r: gm.restart()
                if e.key==pygame.K_1: gm.force_pattern(1)
                if e.key==pygame.K_2: gm.force_pattern(2)
        gm.update(dt)
        screen.fill(BG)
        gm.draw()
        Panel.draw(gm,at)
        draw_overlay(gm,at)
        pygame.display.flip()

if __name__=="__main__":
    main()