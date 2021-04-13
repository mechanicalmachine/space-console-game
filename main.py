import os
import random
import curses
import asyncio

from animation.game_over import gameover_frame
from animation.garbage import lamp, duck, hubble, trash_large, trash_small, trash_xl
from animation.rocket import frame_1, frame_2
from curses_tools import draw_frame, read_controls, get_frame_size
from explosion import explode
from obstacles import Obstacle, show_obstacles
from physics import update_speed

TIC_TIMEOUT = 0.1
STARS_AMOUNT = 100
COROUTINES = []
SPACESHIP_FRAME = ''
OBSTACLES = []
OBSTACLES_IN_LAST_COLLISIONS = []


def draw(canvas):
    global COROUTINES

    canvas.nodelay(True)
    canvas_height, canvas_width = canvas.getmaxyx()

    canvas_vertical_center = canvas_height / 2
    canvas_horizontal_center = canvas_width / 2

    # add stars
    for _ in range(1, STARS_AMOUNT):
        row = random.randint(2, canvas_height - 2)
        column = random.randint(2, canvas_width - 2)
        symbol = random.choice('+*.:')
        delay = random.randint(1, 10)
        COROUTINES.append(blink(canvas, row, column, symbol, delay))

    # add spaceship
    spaceship_frames = (frame_1, frame_2)
    COROUTINES.append(
        run_spaceship(canvas, canvas_vertical_center, canvas_horizontal_center - 2, spaceship_frames)
    )

    # change spaceship frame
    COROUTINES.append(animate_spaceship(spaceship_frames))

    # add garbage
    COROUTINES.append(fill_orbit_with_garbage(canvas, canvas_width))

    loop = asyncio.get_event_loop()
    # show obstacles
    loop.create_task(show_obstacles(canvas, OBSTACLES))

    # show all objects except obstacles
    loop.create_task(async_draw(canvas))

    loop.run_forever()


async def async_draw(canvas):
    while True:
        for index, coroutine in enumerate(COROUTINES.copy()):
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.pop(index)
        canvas.refresh()
        canvas.border()
        await asyncio.sleep(TIC_TIMEOUT)


async def fill_orbit_with_garbage(canvas, canvas_width):
    while True:
        rand_garbage_column = random.randint(1, canvas_width - 1)
        garbage_frames = (duck, hubble, lamp, trash_large, trash_small, trash_xl)
        garbage = random.choice(garbage_frames)
        COROUTINES.append(fly_garbage(canvas, rand_garbage_column, garbage))
        await sleep(12)


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def blink(canvas, row, column, symbol, delay):
    await sleep(delay)
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:

        for index, obstacle in enumerate(OBSTACLES.copy()):
            if obstacle.has_collision(row, column):
                OBSTACLES.pop(index)
                OBSTACLES_IN_LAST_COLLISIONS.append(obstacle)

                await explode(canvas, row, column)

                return

        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def run_spaceship(canvas, canvas_vertical_center, canvas_horizontal_center, frames):
    row, column = canvas_vertical_center, canvas_horizontal_center
    frame_rows, frame_columns = get_frame_size(frames[0])
    canvas_rows, canvas_column = canvas.getmaxyx()
    row_speed, column_speed = 0, 0
    while True:
        rows_direction, columns_direction, space_pressed = read_controls(canvas)

        row_speed, column_speed = update_speed(row_speed, column_speed, rows_direction, columns_direction)

        row = max(1, min(row + row_speed, canvas_rows - frame_rows - 1))
        column = max(1, min(column + column_speed, canvas_column - frame_columns - 1))

        previous_spaceship_frame = SPACESHIP_FRAME

        draw_frame(canvas, row, column, SPACESHIP_FRAME, negative=False)

        # add fire coroutine if space pressed
        if space_pressed:
            COROUTINES.append(fire(canvas, row, column+2))

        await asyncio.sleep(0)

        draw_frame(canvas, row, column, previous_spaceship_frame, negative=True)

        for index, obstacle in enumerate(OBSTACLES.copy()):
            # add show_gameover coroutine if spaceship meet garbage
            if obstacle.has_collision(row, column):
                COROUTINES.append(
                    show_gameover(canvas, canvas_vertical_center, canvas_horizontal_center)
                )

                return


async def animate_spaceship(frames):
    global SPACESHIP_FRAME

    while True:
        for frame in frames:
            SPACESHIP_FRAME = frame
            await asyncio.sleep(0)

            SPACESHIP_FRAME = frame


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Column position will stay the same, as specified on start."""

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number)

    row = 0

    rows, columns = get_frame_size(garbage_frame)

    current_obstacle = Obstacle(row, column, rows, columns)

    OBSTACLES.append(current_obstacle)

    while rows_number - garbage_rows_count:
        if current_obstacle in OBSTACLES_IN_LAST_COLLISIONS:
            OBSTACLES_IN_LAST_COLLISIONS.remove(current_obstacle)
            return

        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
        current_obstacle.row += speed


def _get_spaceship_frame(frame_name):
    with open(frame_name) as frame:
        return frame.read()


def _get_frames_paths(*args):
    return [os.path.join(*args, f) for f in os.listdir(os.path.join(*args)) if os.path.isfile(os.path.join(*args, f))]


async def show_gameover(canvas, half_of_canvas_height, half_of_canvas_weight):
    half_of_gameover_frame_length = len(gameover_frame.split('\n'))/2
    half_of_gameover_frame_height = len(gameover_frame.split('\n')[1])/2
    while True:
        draw_frame(
            canvas,
            half_of_canvas_height - half_of_gameover_frame_length,
            half_of_canvas_weight - half_of_gameover_frame_height,
            gameover_frame
        )
        await asyncio.sleep(0)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.initscr()
    curses.start_color()
    curses.curs_set(False)
    curses.wrapper(draw)
