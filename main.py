import random
import time
import curses
import asyncio
from os import path

from curses_tools import draw_frame, read_controls, get_frame_size

TIC_TIMEOUT = 0.1


def draw(canvas):
    canvas.nodelay(True)
    canvas.border()
    canvas_height, canvas_width = canvas.getmaxyx()
    coroutines = []

    # add stars
    for _ in range(1, 100):
        row = random.randint(2, canvas_height-2)
        column = random.randint(2, canvas_width-2)
        symbol = random.choice('+*.:')
        coroutines.append(blink(canvas, row, column, symbol))

    # add spaceship
    frames_filenames = ['rocket_frame_1.txt', 'rocket_frame_2.txt']
    animation_dir = 'animation'
    spaceship_frames = []
    for filename in frames_filenames:
        frame_path = _get_related_filepath(animation_dir, filename)
        spaceship_frame = _get_spaceship_frame(frame_path)
        spaceship_frames.append(spaceship_frame)
    coroutines.append(animate_spaceship(canvas, canvas_height / 2, canvas_width / 2 - 2, spaceship_frames))

    # add fire
    coroutines.append(fire(canvas, canvas_height / 2, canvas_width / 2))

    while True:
        try:
            for coroutine in coroutines:
                coroutine.send(None)
                canvas.refresh()
            time.sleep(TIC_TIMEOUT)
        except StopIteration:
            coroutines.pop()


async def blink(canvas, row, column, symbol='*'):
    for _ in range(random.randint(1, 10)):
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


def _get_related_filepath(dirname, filename):
    return path.join(dirname, filename)


def _get_spaceship_frame(frame_name):
    with open(frame_name) as frame:
        return frame.read()


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.initscr()
    curses.start_color()
    curses.curs_set(False)
    curses.wrapper(draw)
