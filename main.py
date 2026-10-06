import sys
import pygame
import asyncio

# ---------------------------------------------------------------
# Spy vs Guard, Phase 3: the pretty graphical version
# all the actual game rules live in the phase 2 file, this script
# only draws stuff and listens for key presses. no classes, still.
# (keep spy_vs_guard_phase2.py in the same folder or the import dies)
# ---------------------------------------------------------------
import spy_vs_guard_phase2 as logic

# ---------- window layout ----------
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
TILE_SIZE = 60                                # 10 tiles * 60px = 600px, a perfect square
GRID_PIXELS = logic.GRID_SIZE * TILE_SIZE     # grid takes the left 600px
PANEL_X = GRID_PIXELS                         # info panel starts where the grid ends
PANEL_WIDTH = WINDOW_WIDTH - GRID_PIXELS      # leftover 200px for the panel
FPS = 30

# ---------- colors (R, G, B) ----------
COLOR_FLOOR = (200, 200, 200)       # light gray floor
COLOR_GRID_LINE = (150, 150, 150)   # slightly darker gray for the lines
COLOR_WALL = (54, 54, 54)           # dark charcoal
COLOR_SPY = (40, 90, 220)           # blue
COLOR_GUARD = (210, 40, 40)         # red
COLOR_DOCUMENT = (240, 200, 30)     # gold
COLOR_EXIT = (40, 170, 70)          # green
COLOR_FOG = (0, 0, 0)               # pitch black
COLOR_PANEL_BG = (30, 30, 40)
COLOR_TEXT = (230, 230, 230)
COLOR_WIN_TEXT = (60, 220, 90)
COLOR_LOSE_TEXT = (240, 60, 60)

# reusing the phase 2 cell_char() letters, so the GUI and the terminal
# version always agree about what is on each tile. letter -> color
CHAR_TO_COLOR = {
    'S': COLOR_SPY,
    'G': COLOR_GUARD,
    '#': COLOR_WALL,
    'D': COLOR_DOCUMENT,
    'E': COLOR_EXIT,
    '.': COLOR_FLOOR,
}

# same dictionary trick as the game logic: key -> direction name
KEY_TO_DIRECTION = {
    pygame.K_UP: 'UP',
    pygame.K_DOWN: 'DOWN',
    pygame.K_LEFT: 'LEFT',
    pygame.K_RIGHT: 'RIGHT',
}


# ---------------------------------------------------------------
# drawing functions
# ---------------------------------------------------------------

def draw_grid(screen, game_state, admin_view):
    # go through every tile, paint it, then (maybe) cover it with fog
    for r in range(logic.GRID_SIZE):
        for c in range(logic.GRID_SIZE):
            pos = (r, c)
            rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)

            # ask the phase 2 logic what is on this tile, then look up its color
            tile_char = logic.cell_char(game_state, pos)
            pygame.draw.rect(screen, CHAR_TO_COLOR[tile_char], rect)
            pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)  # thin outline = grid line

            # fog of war: in spy view, anything outside the 3x3 box goes black.
            # this also hides the guard automatically, which is kinda neat
            if not admin_view and not logic.in_spy_vision(game_state, pos):
                pygame.draw.rect(screen, COLOR_FOG, rect)


def draw_text_line(screen, font, text, x, y, color=COLOR_TEXT):
    # tiny helper so i don't repeat render + blit everywhere
    screen.blit(font.render(text, True, color), (x, y))


def draw_panel(screen, game_state, admin_view, font, small_font):
    # right-hand side status panel
    panel_rect = pygame.Rect(PANEL_X, 0, PANEL_WIDTH, WINDOW_HEIGHT)
    pygame.draw.rect(screen, COLOR_PANEL_BG, panel_rect)

    x = PANEL_X + 12
    y = 15

    doc_text = "YES" if game_state['has_document'] else "not yet"
    draw_text_line(screen, font, "Document Collected:", x, y)
    draw_text_line(screen, font, doc_text, x, y + 24)

    y += 70
    draw_text_line(screen, font, "Turn Count: %d" % game_state['turn'], x, y)

    y += 45
    noise = game_state['last_noise_pos']
    noise_text = "none yet" if noise is None else "(%d, %d)" % noise
    draw_text_line(screen, font, "Last Noise Location:", x, y)
    draw_text_line(screen, font, noise_text, x, y + 24)

    y += 70
    view_text = "ADMIN (see all)" if admin_view else "SPY (fog on)"
    draw_text_line(screen, font, "View: " + view_text, x, y)

    # controls cheat sheet, written the way i'd scribble it on a sticky note
    y += 55
    draw_text_line(screen, font, "Controls Info:", x, y)
    control_lines = [
        "Arrows = sneak around",
        "TAB = peek at admin map",
        "R = restart, i messed up",
    ]
    for i, line in enumerate(control_lines):
        draw_text_line(screen, small_font, line, x, y + 28 + i * 20)


def draw_game_over(screen, game_state, big_font, small_font):
    # nothing to draw while the game is still going
    if game_state['status'] == 'playing':
        return

    if game_state['status'] == 'won':
        message = "VICTORY! Escaped with Document"
        color = COLOR_WIN_TEXT
    else:
        message = "BUSTED! Guard Caught You"
        color = COLOR_LOSE_TEXT

    # dark banner across the middle of the grid so the text is readable
    banner = pygame.Rect(0, GRID_PIXELS // 2 - 60, GRID_PIXELS, 120)
    pygame.draw.rect(screen, (0, 0, 0), banner)
    pygame.draw.rect(screen, color, banner, 3)

    # center the big message and the restart hint inside the banner
    text_surface = big_font.render(message, True, color)
    text_rect = text_surface.get_rect(center=(GRID_PIXELS // 2, GRID_PIXELS // 2 - 10))
    screen.blit(text_surface, text_rect)

    hint_surface = small_font.render("press R to try again", True, COLOR_TEXT)
    hint_rect = hint_surface.get_rect(center=(GRID_PIXELS // 2, GRID_PIXELS // 2 + 35))
    screen.blit(hint_surface, hint_rect)


# ---------------------------------------------------------------
# input handling
# ---------------------------------------------------------------

def handle_arrow_key(game_state, direction):
    # one full turn: spy moves, noise roll, guard moves, win/loss check.
    # play_turn() from phase 2 does all of that for us.
    if game_state['status'] != 'playing':
        return  # game is over, arrows do nothing until R is pressed

    # bumping into a wall shouldn't cost a turn (otherwise the guard gets
    # a free step for nothing, which feels unfair), so i check first
    dr, dc = logic.DIRECTIONS[direction]
    target = (game_state['spy_pos'][0] + dr, game_state['spy_pos'][1] + dc)
    if not logic.is_valid_tile(game_state['grid'], target):
        return

    logic.play_turn(game_state, direction)


# ---------------------------------------------------------------
# main loop
# ---------------------------------------------------------------

async def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Spy vs Guard - Phase 3")
    clock = pygame.time.Clock()

    # None = pygame's built-in default font, no font files needed
    font = pygame.font.Font(None, 26)
    small_font = pygame.font.Font(None, 22)
    big_font = pygame.font.Font(None, 44)

    game_state = logic.make_game_state()
    admin_view = False   # start in spy view (fog on)

    running = True
    while running:
        # --- listen for events ---
        await asyncio.sleep(0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in KEY_TO_DIRECTION:
                    handle_arrow_key(game_state, KEY_TO_DIRECTION[event.key])
                elif event.key == pygame.K_TAB:
                    admin_view = not admin_view          # flip the view
                elif event.key == pygame.K_r:
                    game_state = logic.make_game_state()  # fresh game, fresh start

        # --- draw everything ---
        screen.fill(COLOR_PANEL_BG)
        draw_grid(screen, game_state, admin_view)
        draw_panel(screen, game_state, admin_view, font, small_font)
        draw_game_over(screen, game_state, big_font, small_font)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()