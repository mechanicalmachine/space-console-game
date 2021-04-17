import random
import curses
import asyncio

from animation.game_over import gameover_frame
from animation.garbage import lamp, duck, hubble, trash_large, trash_small, trash_xl
from animation.rocket import frame_1, frame_2
from curses_tools import draw_frame, read_controls, get_frame_size
from explosion import explode
from obstacles import Obstacle
from physics import update_speed

TIC_TIMEOUT = 0.1
STARS_AMOUNT = 100

coroutines = []
spaceship_frame = ''
obstacles = []
obstacles_in_last_collisions = []
year = 1957


def draw(canvas):
    global coroutines

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
        coroutines.append(blink(canvas, row, column, symbol, delay))

    # add spaceship
    spaceship_frames = (frame_1, frame_2)
    coroutines.append(
        run_spaceship(canvas, canvas_vertical_center, canvas_horizontal_center - 2, spaceship_frames)
    )

    # change spaceship frame
    coroutines.append(animate_spaceship(spaceship_frames))

    # add garbage
    coroutines.append(fill_orbit_with_garbage(canvas, canvas_width))

    loop = asyncio.get_event_loop()

    # show all objects except obstacles
    loop.create_task(async_draw(canvas))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


async def async_draw(canvas):
    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        canvas.border()
        await asyncio.sleep(TIC_TIMEOUT)


def get_garbage_delay_tics():
    if year < 1961:
        return None
    elif year < 1969:
        return 20
    elif year < 1981:
        return 14
    elif year < 1995:
        return 10
    elif year < 2010:
        return 8
    elif year < 2020:
        return 6
    else:
        return 2


async def fill_orbit_with_garbage(canvas, canvas_width):
    while True:
        garbage_delay_tics = get_garbage_delay_tics()
        if garbage_delay_tics:
            rand_garbage_column = random.randint(1, canvas_width - 1)
            garbage_frames = (duck, hubble, lamp, trash_large, trash_small, trash_xl)
            garbage = random.choice(garbage_frames)
            coroutines.append(fly_garbage(canvas, rand_garbage_column, garbage))
            await sleep(garbage_delay_tics)
        else:
            await asyncio.sleep(0)


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

    fire_row, fire_column = start_row, start_column

    canvas.addstr(round(fire_row), round(fire_column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(fire_row), round(fire_column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(fire_row), round(fire_column), ' ')

    fire_row += rows_speed
    fire_column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()

    curses.beep()

    while 0 < fire_row < rows:
        for index, obstacle in enumerate(obstacles.copy()):
            if obstacle.has_collision(fire_row, fire_column):
                obstacles_in_last_collisions.append(obstacle)

                await explode(canvas, fire_row, fire_column)

                return

        canvas.addstr(round(fire_row), round(fire_column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(fire_row), round(fire_column), ' ')
        fire_row += rows_speed
        fire_column += columns_speed


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

        previous_spaceship_frame = spaceship_frame

        draw_frame(canvas, row, column, spaceship_frame, negative=False)

        plasma_gun_activation_year = 2020

        if year > plasma_gun_activation_year and space_pressed:
            coroutines.append(fire(canvas, row, column + 2))

        await asyncio.sleep(0)

        draw_frame(canvas, row, column, previous_spaceship_frame, negative=True)

        for index, obstacle in enumerate(obstacles.copy()):
            # add show_gameover coroutine if spaceship meet garbage
            if obstacle.has_collision(row, column):
                coroutines.append(
                    show_gameover(canvas, canvas_vertical_center, canvas_horizontal_center)
                )

                return


async def animate_spaceship(frames):
    global spaceship_frame

    while True:
        for frame in frames:
            spaceship_frame = frame
            await asyncio.sleep(0)

            spaceship_frame = frame


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Column position will stay the same, as specified on start."""

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number)

    row = 0

    garbage_rows_takes, garbage_columns_takes = get_frame_size(garbage_frame)

    current_obstacle = Obstacle(row, column, garbage_rows_takes, garbage_columns_takes)

    obstacles.append(current_obstacle)

    try:
        while row < rows_number:
            if current_obstacle in obstacles_in_last_collisions:
                obstacles_in_last_collisions.remove(current_obstacle)
                return

            draw_frame(canvas, row, column, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
            current_obstacle.row += speed
    finally:
        obstacles.remove(current_obstacle)


async def show_gameover(canvas, half_of_canvas_height, half_of_canvas_width):
    half_of_gameover_frame_length = len(gameover_frame.split('\n'))/2
    half_of_gameover_frame_height = len(gameover_frame.split('\n')[1])/2
    while True:
        draw_frame(
            canvas,
            half_of_canvas_height - half_of_gameover_frame_length,
            half_of_canvas_width - half_of_gameover_frame_height,
            gameover_frame
        )
        await asyncio.sleep(0)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.initscr()
    curses.start_color()
    curses.curs_set(False)
    curses.wrapper(draw)
