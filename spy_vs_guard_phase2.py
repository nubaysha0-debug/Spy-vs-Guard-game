import random
import numpy as np

# ---------------------------------------------------------------
# Spy vs Guard, Phase 2: now with fog of war and creaky floorboards
# no classes anywhere, just dicts and functions. keeping it scrappy.
# ---------------------------------------------------------------

GRID_SIZE = 10

# my little direction lookup, (row change, col change) for each move
DIRECTIONS = {
    'UP': (-1, 0),
    'DOWN': (1, 0),
    'LEFT': (0, -1),
    'RIGHT': (0, 1),
}

# i honestly forgot where the spy started in phase 1, so top-left it is.
# change this if your phase 1 had it somewhere else!
SPY_START = (0, 0)
GUARD_START = (9, 0)
DOCUMENT_POS = (8, 8)
EXIT_POS = (0, 9)

# a few walls i scattered around until the map felt kinda annoying
WALLS = [(3, 3), (3, 4), (3, 5), (5, 6), (6, 6), (6, 2), (7, 2), (4, 8)]

NOISE_CHANCE = 0.20         # 20% chance the spy's boots creak on any step
GUARD_TRACK_CHANCE = 0.60   # 60% of the time the guard actually follows the noise
VISION_RADIUS = 1           # 1 step each way = a 3x3 peephole


def make_game_state():
    # build the grid first, 0 = empty floor, 1 = wall
    grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=int)
    for r, c in WALLS:
        grid[r, c] = 1

    # everything lives in one dict, no classes, no drama
    return {
        'grid': grid,
        'spy_pos': SPY_START,
        'guard_pos': GUARD_START,
        'has_document': False,
        'last_noise_pos': None,   # nobody has heard anything yet
        'turn': 0,
        'status': 'playing',      # playing / won / caught
    }


# ---------------------------------------------------------------
# movement stuff
# ---------------------------------------------------------------

def is_valid_tile(grid, pos):
    # is this tile on the board AND not a wall? that's all i care about
    r, c = pos
    if r < 0 or r >= GRID_SIZE or c < 0 or c >= GRID_SIZE:
        return False
    return grid[r, c] == 0


def get_valid_moves(grid, pos):
    # look at all 4 neighbors, keep the ones i can actually stand on
    moves = []
    for dr, dc in DIRECTIONS.values():
        new_pos = (pos[0] + dr, pos[1] + dc)
        if is_valid_tile(grid, new_pos):
            moves.append(new_pos)
    return moves


def manhattan_distance(a, b):
    # taxicab distance, good enough for a guard with no map skills
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ---------------------------------------------------------------
# noise pings (the spy is NOT a ninja, apparently)
# ---------------------------------------------------------------

def maybe_make_noise(game_state):
    # roll the dice, 20% of the time the floor goes CREAK
    if random.random() < NOISE_CHANCE:
        game_state['last_noise_pos'] = game_state['spy_pos']
        print("CREAK! Noise detected near %s. ugh, that was loud." % (game_state['spy_pos'],))


# ---------------------------------------------------------------
# spy turn
# ---------------------------------------------------------------

def move_spy(game_state, direction):
    if direction not in DIRECTIONS:
        print("what is '%s' even supposed to mean? not moving." % direction)
        return False

    dr, dc = DIRECTIONS[direction]
    new_pos = (game_state['spy_pos'][0] + dr, game_state['spy_pos'][1] + dc)

    if not is_valid_tile(game_state['grid'], new_pos):
        print("oof, bumped into a wall or the edge of the world. no move.")
        return False

    game_state['spy_pos'] = new_pos

    # grabbing the document if i'm standing on it
    if new_pos == DOCUMENT_POS and not game_state['has_document']:
        game_state['has_document'] = True
        print("got the document!! now to sneak out of here.")

    # every successful step = a chance to make noise
    maybe_make_noise(game_state)
    return True


# ---------------------------------------------------------------
# guard AI (random walk, but with ears now)
# ---------------------------------------------------------------

def step_toward(valid_moves, target):
    # of the tiles i can reach, pick the one closest to the target.
    # ties get settled by a coin flip so it's not too predictable
    best_dist = min(manhattan_distance(m, target) for m in valid_moves)
    best_moves = [m for m in valid_moves if manhattan_distance(m, target) == best_dist]
    return random.choice(best_moves)


def move_guard(game_state):
    valid_moves = get_valid_moves(game_state['grid'], game_state['guard_pos'])
    if not valid_moves:
        return  # boxed in, guard just stands there being sad

    noise_pos = game_state['last_noise_pos']

    # heard something? 60% of the time go check it out, otherwise wander
    if noise_pos is not None and random.random() < GUARD_TRACK_CHANCE:
        game_state['guard_pos'] = step_toward(valid_moves, noise_pos)
        print("[admin] guard is heading toward the noise at %s" % (noise_pos,))
    else:
        game_state['guard_pos'] = random.choice(valid_moves)

    # if the guard got to the noise spot, nothing's there, so forget about it
    if game_state['guard_pos'] == noise_pos:
        game_state['last_noise_pos'] = None


# ---------------------------------------------------------------
# win / loss
# ---------------------------------------------------------------

def check_game_over(game_state):
    if game_state['spy_pos'] == game_state['guard_pos']:
        game_state['status'] = 'caught'
        print("busted. the guard got me. well, that went badly.")
    elif game_state['spy_pos'] == EXIT_POS and game_state['has_document']:
        game_state['status'] = 'won'
        print("made it out with the document. i'm basically james bond.")
    return game_state['status']


def play_turn(game_state, direction):
    game_state['turn'] += 1
    print("--- turn %d: spy tries to go %s ---" % (game_state['turn'], direction))

    move_spy(game_state, direction)
    if check_game_over(game_state) != 'playing':
        return

    move_guard(game_state)
    check_game_over(game_state)


# ---------------------------------------------------------------
# rendering (plain ASCII only, windows consoles hate fancy stuff)
# ---------------------------------------------------------------

def cell_char(game_state, pos):
    # what's *really* on this tile? full truth, no fog
    if pos == game_state['spy_pos']:
        return 'S'
    if pos == game_state['guard_pos']:
        return 'G'
    if game_state['grid'][pos[0], pos[1]] == 1:
        return '#'
    if pos == DOCUMENT_POS and not game_state['has_document']:
        return 'D'
    if pos == EXIT_POS:
        return 'E'
    return '.'


def render_full_map(game_state):
    # admin / god-mode view, i can see everything
    print("== ADMIN MAP (everything visible) ==")
    for r in range(GRID_SIZE):
        print(' '.join(cell_char(game_state, (r, c)) for c in range(GRID_SIZE)))


def in_spy_vision(game_state, pos):
    # inside the 3x3 box around the spy? (chebyshev distance <= 1)
    sr, sc = game_state['spy_pos']
    return abs(pos[0] - sr) <= VISION_RADIUS and abs(pos[1] - sc) <= VISION_RADIUS


def render_spy_view(game_state):
    # what the spy can see: a tiny 3x3 flashlight, fog everywhere else.
    # the guard only shows up as G if he's inside that little box.
    print("== SPY VIEW (fog of war) ==")
    for r in range(GRID_SIZE):
        row_chars = []
        for c in range(GRID_SIZE):
            if in_spy_vision(game_state, (r, c)):
                row_chars.append(cell_char(game_state, (r, c)))
            else:
                row_chars.append('?')
        print(' '.join(row_chars))


# ---------------------------------------------------------------
# test section: 5 scripted turns, both maps every turn
# ---------------------------------------------------------------

def run_test_sequence():
    # uncomment for the same dice rolls every run (handy for debugging):
    # random.seed(42)

    game_state = make_game_state()
    test_moves = ['DOWN', 'DOWN', 'RIGHT', 'RIGHT', 'DOWN']

    print("starting state, before anybody does anything:")
    render_full_map(game_state)
    render_spy_view(game_state)
    print()

    for direction in test_moves:
        play_turn(game_state, direction)
        render_full_map(game_state)
        render_spy_view(game_state)
        print("last noise pos: %s | has doc: %s | status: %s"
              % (game_state['last_noise_pos'], game_state['has_document'], game_state['status']))
        print()

        if game_state['status'] != 'playing':
            print("game ended early, stopping the test here.")
            break

    print("test done. fingers crossed nothing exploded.")


if __name__ == '__main__':
    run_test_sequence()