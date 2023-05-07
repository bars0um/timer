import time
import csv
import curses

def format_time(duration):
    """Format duration as hours, minutes, and seconds"""
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02d}:{:02d}:{:02d}".format(int(hours), int(minutes), int(seconds))

def save_time(description, project, elapsed_time_seconds):
    """Save elapsed time to CSV file"""
    elapsed_time_hours = int(elapsed_time_seconds / 3600)
    elapsed_time_minutes = int((elapsed_time_seconds % 3600) / 60)
    elapsed_time_seconds = int(elapsed_time_seconds % 60)
    elapsed_time_str = "{:02d}:{:02d}:{:02d}".format(elapsed_time_hours, elapsed_time_minutes, elapsed_time_seconds)
    start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
    with open("timesheet.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([start_time_str, elapsed_time_str, description, project])

def get_project_list():
    """Get list of projects from CSV file"""
    project_set = set()
    try:
        with open("timesheet.csv", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 3:
                    project_set.add(row[3])
    except FileNotFoundError:
        pass

    return sorted(list(project_set))

def select_project(stdscr, project_list):
    """Select project from list"""
    project_list.append("Enter a new project")
    selected_index = 0
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Select a project:")
        for i, project in enumerate(project_list):
            if i == selected_index:
                stdscr.addstr(i+2, 0, "> {}".format(project))
            else:
                stdscr.addstr(i+2, 0, "  {}".format(project))
        stdscr.refresh()
        c = stdscr.getch()
        if c == curses.KEY_UP:
            selected_index = max(0, selected_index-1)
        elif c == curses.KEY_DOWN:
            selected_index = min(len(project_list)-1, selected_index+1)
        elif c == ord('\n'):
            if selected_index == len(project_list) - 1:  # "Enter a new project" is selected
                return None
            else:
                return project_list[selected_index]

def input_project(stdscr):
    stdscr.addstr(1, 0, "Enter a project:")
    stdscr.refresh()
    project = ""
    while True:
        c = stdscr.getch()
        if c == ord('\n'):
            break
        elif c == curses.KEY_BACKSPACE or c == 127:
            project = project[:-1]
        elif c != -1:  # Ignore timeout (-1)
            project += chr(c)
        stdscr.clear()
        stdscr.addstr(1, 0, "Enter a project: {}".format(project))
        stdscr.refresh()
    return project

def main(stdscr):
    """Main function"""
    global start_time
    curses.curs_set(1)
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    stdscr.bkgd(curses.color_pair(2))
    stdscr.timeout(100)  # Set timeout to 1000 ms (1 second)

    # Enter a description
    stdscr.addstr(0, 0, "Enter a description:", curses.color_pair(1))
    stdscr.refresh()
    description = ""
    while True:
        c = stdscr.getch()
        if c == ord('\n'):
            break
        elif c == curses.KEY_BACKSPACE or c == 127:
            description = description[:-1]
        elif c != -1:  # Ignore timeout (-1)
            description += chr(c)
        stdscr.clear()
        stdscr.addstr(0, 0, "Enter a description: {}".format(description))
        stdscr.refresh()

    # Select or enter a project
    project_list = get_project_list()
    if project_list:
        stdscr.addstr(1, 0, "Select a project:")
        stdscr.refresh()
        project = select_project(stdscr, project_list)
        if project is None:  # "Enter a new project" was selected
            project = input_project(stdscr)
    else:
        project = input_project(stdscr)

    # Start the timer
    stdscr.clear()
    stdscr.addstr(0, 0, "Press 's' to start the timer...")
    stdscr.refresh()

    while True:
        c = stdscr.getch()
        if c == ord('s'):
            stdscr.clear()
            start_time = time.time()
            start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
            stdscr.addstr(0, 0, "Timer started at {}".format(start_time_str))
            stdscr.addstr(1, 0, "Description: {}".format(description))
            stdscr.addstr(2, 0, "Project: {}".format(project))
            elapsed_time = time.time() - start_time
            stdscr.addstr(3, 0, "Elapsed time: {}".format(format_time(elapsed_time)), curses.color_pair(1))
            stdscr.refresh()
            break

    # Monitor and display the elapsed time
    while True:
        c = stdscr.getch()
        if c == ord('q'):
            break
        elif c == ord('p'):
            stdscr.clear()
            stdscr.addstr(0, 0, "Timer stopped at {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
            stdscr.refresh()
            elapsed_time = time.time() - start_time
            save_time(description, project, elapsed_time)
            break
        current_time = time.time()
        elapsed_time = current_time - start_time
        stdscr.clear()
        start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        stdscr.addstr(0, 0, "Timer started at {}".format(start_time_str))
        stdscr.addstr(1, 0, "Description: {}".format(description))
        stdscr.addstr(2, 0, "Project: {}".format(project))
        stdscr.addstr(3, 0, "Elapsed time: {}".format(format_time(elapsed_time)), curses.color_pair(1))
        stdscr.addstr(4, 0, "Press 'p' to stop the timer or 'q' to quit.")
        stdscr.refresh()
        time.sleep(1)

# Start curses
curses.wrapper(main)
