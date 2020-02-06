import os
import random
import time
import curses
import asyncio

from curses_tools import draw_frame, read_controls, get_frame_size

TIC_TIMEOUT = 0.1
STARS_AMOUNT = 100
COROUTINES = []


def draw(canvas):
    global COROUTINES

    canvas.nodelay(True)
    canvas.border()
    canvas_height, canvas_width = canvas.getmaxyx()

    # add stars
    for _ in range(1, STARS_AMOUNT):
        row = random.randint(2, canvas_height-2)
        column = random.randint(2, canvas_width-2)
        symbol = random.choice('+*.:')
        delay = random.randint(1, 10)
        COROUTINES.append(blink(canvas, row, column, symbol, delay))

    # add spaceship
    spaceship_frames = []
    spaceship_frames_filenames = _get_frames_paths('animation', 'rocket')
    for filename in spaceship_frames_filenames:
        spaceship_frame = _get_spaceship_frame(filename)
        spaceship_frames.append(spaceship_frame)
    COROUTINES.append(animate_spaceship(canvas, canvas_height / 2, canvas_width / 2 - 2, spaceship_frames))

    # add fire
    COROUTINES.append(fire(canvas, canvas_height / 2, canvas_width / 2))

    loop = asyncio.get_event_loop()
    loop.create_task(async_draw(canvas, canvas_width))
    loop.run_forever()


async def async_draw(canvas, canvas_width):
    while True:
        # add garbage
        garbage_frames_filenames1 = _get_frames_paths('animation', 'garbage')
        garbage_frame1 = _get_spaceship_frame(garbage_frames_filenames1[0])
        await fill_orbit_with_garbage(canvas, garbage_frame1, canvas_width)

        for index, coroutine in enumerate(COROUTINES.copy()):
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.pop(index)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


async def fill_orbit_with_garbage(canvas, garbage_frame, canvas_width):
    rand_garbage_column = random.randint(1, canvas_width - 1)
    COROUTINES.append(fly_garbage(canvas, rand_garbage_column, garbage_frame))
    await asyncio.sleep(0.1)


async def blink(canvas, row, column, symbol, delay):
    for _ in range(delay):
        await asyncio.sleep(0)
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(20):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)


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
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(canvas, start_row, start_column, frames):
    row, column = start_row, start_column
    frame_rows, frame_columns = get_frame_size(frames[0])
    canvas_rows, canvas_column = canvas.getmaxyx()
    while True:
        rows_direction, columns_direction, space_pressed = read_controls(canvas)

        row = max(1, min(row + rows_direction, canvas_rows - frame_rows - 1))
        column = max(1, min(column + columns_direction, canvas_column - frame_columns - 1))

        for frame in frames:
            draw_frame(canvas, row, column, frame, negative=False)
            await asyncio.sleep(0)

            draw_frame(canvas, row, column, frame, negative=True)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay the same, as specified on start."""

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed


def _get_spaceship_frame(frame_name):
    with open(frame_name) as frame:
        return frame.read()


def _get_frames_paths(*args):
    return [os.path.join(*args, f) for f in os.listdir(os.path.join(*args)) if os.path.isfile(os.path.join(*args, f))]


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.initscr()
    curses.start_color()
    curses.curs_set(False)
    curses.wrapper(draw)
