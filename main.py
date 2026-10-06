import asyncio
import random
import sys
import pygame

# ===============================================================
# GAME LOGIC (Phase 2)
# ===============================================================
GRID_SIZE = 10
NUM_WALLS = 18

DIRECTIONS = {
    'UP': (-1, 0),
    'DOWN': (1, 0),
    'LEFT': (0, -1),
    'RIGHT': (0, 1),
}


def is_valid_tile(grid, pos):
  r, c = pos
  if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE):
    return False
  return grid[r][c] != '#'


def generate_map():
  grid = [['.' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
  walls_placed = 0
  forbidden = {(0, 0), (GRID_SIZE - 1, GRID_SIZE - 1), (GRID_SIZE - 1, 0)}

  while walls_placed < NUM_WALLS:
    r = random.randint(0, GRID_SIZE - 1)
    c = random.randint(0, GRID_SIZE - 1)
    if (r, c) not in forbidden and grid[r][c] == '.':
      grid[r][c] = '#'
      walls_placed += 1
  return grid


def make_game_state():
  grid = generate_map()
  return {
      'grid': grid,
      'spy_pos': (0, 0),
      'guard_pos': (GRID_SIZE - 1, GRID_SIZE - 1),
      'doc_pos': (GRID_SIZE - 1, 0),
      'has_document': False,
      'status': 'playing',
      'last_noise_pos': None,
      'turn': 0,
  }


def move_entity(grid, current_pos, direction):
  dr, dc = DIRECTIONS[direction]
  target = (current_pos[0] + dr, current_pos[1] + dc)
  if is_valid_tile(grid, target):
    return target
  return current_pos


def guard_step(game_state):
  grid = game_state['grid']
  guard = game_state['guard_pos']
  target = game_state['spy_pos']
  if not in_spy_vision(
      game_state, guard
  ) and game_state['last_noise_pos'] is not None:
    target = game_state['last_noise_pos']

  best_pos = guard
  best_dist = abs(guard[0] - target[0]) + abs(guard[1] - target[1])

  for direction in DIRECTIONS:
    nxt = move_entity(grid, guard, direction)
    dist = abs(nxt[0] - target[0]) + abs(nxt[1] - target[1])
    if dist < best_dist:
      best_dist = dist
      best_pos = nxt

  game_state['guard_pos'] = best_pos


def play_turn(game_state, direction):
  if game_state['status'] != 'playing':
    return

  game_state['turn'] += 1
  game_state['spy_pos'] = move_entity(
      game_state['grid'], game_state['spy_pos'], direction
  )

  if game_state['spy_pos'] == game_state['doc_pos']:
    game_state['has_document'] = True

  if game_state['spy_pos'] == (0, 0) and game_state['has_document']:
    game_state['status'] = 'won'
    return

  if random.random() < 0.3:
    game_state['last_noise_pos'] = game_state['spy_pos']

  guard_step(game_state)

  if game_state['spy_pos'] == game_state['guard_pos']:
    game_state['status'] = 'lost'


def in_spy_vision(game_state, pos):
  sr, sc = game_state['spy_pos']
  r, c = pos
  return abs(sr - r) <= 1 and abs(sc - c) <= 1


def cell_char(game_state, pos):
  if pos == game_state['spy_pos']:
    return 'S'
  if pos == game_state['guard_pos']:
    return 'G'
  if pos == game_state['doc_pos'] and not game_state['has_document']:
    return 'D'
  if pos == (0, 0) and game_state['has_document']:
    return 'E'
  r, c = pos
  return game_state['grid'][r][c]


# ===============================================================
# GUI & MAIN LOOP (Phase 3)
# ===============================================================
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
TILE_SIZE = 60
GRID_PIXELS = GRID_SIZE * TILE_SIZE
PANEL_X = GRID_PIXELS
PANEL_WIDTH = WINDOW_WIDTH - GRID_PIXELS
FPS = 30

COLOR_FLOOR = (200, 200, 200)
COLOR_GRID_LINE = (150, 150, 150)
COLOR_WALL = (54, 54, 54)
COLOR_SPY = (40, 90, 220)
COLOR_GUARD = (210, 40, 40)
COLOR_DOCUMENT = (240, 200, 30)
COLOR_EXIT = (40, 170, 70)
COLOR_FOG = (0, 0, 0)
COLOR_PANEL_BG = (30, 30, 40)
COLOR_TEXT = (230, 230, 230)
COLOR_WIN_TEXT = (60, 220, 90)
COLOR_LOSE_TEXT = (240, 60, 60)

CHAR_TO_COLOR = {
    'S': COLOR_SPY,
    'G': COLOR_GUARD,
    '#': COLOR_WALL,
    'D': COLOR_DOCUMENT,
    'E': COLOR_EXIT,
    '.': COLOR_FLOOR,
}

KEY_TO_DIRECTION = {
    pygame.K_UP: 'UP',
    pygame.K_DOWN: 'DOWN',
    pygame.K_LEFT: 'LEFT',
    pygame.K_RIGHT: 'RIGHT',
}


def draw_grid(screen, game_state, admin_view):
  for r in range(GRID_SIZE):
    for c in range(GRID_SIZE):
      pos = (r, c)
      rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
      tile_char = cell_char(game_state, pos)
      pygame.draw.rect(screen, CHAR_TO_COLOR[tile_char], rect)
      pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)

      if not admin_view and not in_spy_vision(game_state, pos):
        pygame.draw.rect(screen, COLOR_FOG, rect)


def draw_text_line(screen, font, text, x, y, color=COLOR_TEXT):
  screen.blit(font.render(text, True, color), (x, y))


def draw_panel(screen, game_state, admin_view, font, small_font):
  panel_rect = pygame.Rect(PANEL_X, 0, PANEL_WIDTH, WINDOW_HEIGHT)
  pygame.draw.rect(screen, COLOR_PANEL_BG, panel_rect)

  x = PANEL_X + 12
  y = 15

  doc_text = 'YES' if game_state['has_document'] else 'not yet'
  draw_text_line(screen, font, 'Document Collected:', x, y)
  draw_text_line(screen, font, doc_text, x, y + 24)

  y += 70
  draw_text_line(screen, font, 'Turn Count: %d' % game_state['turn'], x, y)

  y += 45
  noise = game_state['last_noise_pos']
  noise_text = 'none yet' if noise is None else '(%d, %d)' % noise
  draw_text_line(screen, font, 'Last Noise Location:', x, y)
  draw_text_line(screen, font, noise_text, x, y + 24)

  y += 70
  view_text = 'ADMIN (see all)' if admin_view else 'SPY (fog on)'
  draw_text_line(screen, font, 'View: ' + view_text, x, y)

  y += 55
  draw_text_line(screen, font, 'Controls Info:', x, y)
  control_lines = [
      'Arrows = sneak around',
      'TAB = peek at admin map',
      'R = restart, i messed up',
  ]
  for i, line in enumerate(control_lines):
    draw_text_line(screen, small_font, line, x, y + 28 + i * 20)


def draw_game_over(screen, game_state, big_font, small_font):
  if game_state['status'] == 'playing':
    return

  if game_state['status'] == 'won':
    message = 'VICTORY! Escaped with Document'
    color = COLOR_WIN_TEXT
  else:
    message = 'BUSTED! Guard Caught You'
    color = COLOR_LOSE_TEXT

  banner = pygame.Rect(0, GRID_PIXELS // 2 - 60, GRID_PIXELS, 120)
  pygame.draw.rect(screen, (0, 0, 0), banner)
  pygame.draw.rect(screen, color, banner, 3)

  text_surface = big_font.render(message, True, color)
  text_rect = text_surface.get_rect(
      center=(GRID_PIXELS // 2, GRID_PIXELS // 2 - 10)
  )
  screen.blit(text_surface, text_rect)

  hint_surface = small_font.render('press R to try again', True, COLOR_TEXT)
  hint_rect = hint_surface.get_rect(
      center=(GRID_PIXELS // 2, GRID_PIXELS // 2 + 35)
  )
  screen.blit(hint_surface, hint_rect)


def handle_arrow_key(game_state, direction):
  if game_state['status'] != 'playing':
    return

  dr, dc = DIRECTIONS[direction]
  target = (game_state['spy_pos'][0] + dr, game_state['spy_pos'][1] + dc)
  if not is_valid_tile(game_state['grid'], target):
    return

  play_turn(game_state, direction)


async def main():
  pygame.init()
  screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
  pygame.display.set_caption('Spy vs Guard')
  clock = pygame.time.Clock()

  font = pygame.font.Font(None, 26)
  small_font = pygame.font.Font(None, 22)
  big_font = pygame.font.Font(None, 44)

  game_state = make_game_state()
  admin_view = False

  running = True
  while running:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False
      elif event.type == pygame.KEYDOWN:
        if event.key in KEY_TO_DIRECTION:
          handle_arrow_key(game_state, KEY_TO_DIRECTION[event.key])
        elif event.key == pygame.K_TAB:
          admin_view = not admin_view
        elif event.key == pygame.K_r:
          game_state = make_game_state()

    screen.fill(COLOR_PANEL_BG)
    draw_grid(screen, game_state, admin_view)
    draw_panel(screen, game_state, admin_view, font, small_font)
    draw_game_over(screen, game_state, big_font, small_font)

    pygame.display.flip()
    clock.tick(FPS)
    await asyncio.sleep(0)

  pygame.quit()


if __name__ == '__main__':
  asyncio.run(main())