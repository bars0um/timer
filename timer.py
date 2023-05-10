import time
import csv
import math
import curses
import subprocess
import hashlib
import os
import logging

# Set up logging
logging.basicConfig(filename="timer.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def check_git_pull():
    """Performs a git pull and checks if any changes were made."""
    result = subprocess.run(["git", "pull"], capture_output=True, text=True)
    logging.info(f"git check results: {result}")
    return "Already up to date." not in result.stdout

def parse_properties(filename):
    properties = {}
    with open(filename, "r") as f:
        for line in f:
            key, value = line.strip().split("=", 1)
            properties[key] = value
    return properties

def download_timesheet(properties):
    if not properties['remote_save'] == "true":
        return
    """Downloads timesheet.csv from the remote system using SCP."""
    logging.info(f"Downloading latest version of timesheet...")
    remote_path = f"{properties['host']}:{properties['path']}/timesheet.csv"
    subprocess.run(["scp", remote_path, "timesheet.csv"])

def upload_timesheet(properties):
    if not properties['remote_save'] == "true":
        return
    """Uploads timesheet.csv to the remote system using SCP."""
    logging.info(f"Uploading latest version of timesheet...")
    remote_path = f"{properties['host']}:{properties['path']}/timesheet.csv"
    subprocess.run(["scp", "timesheet.csv", remote_path])

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

def select_description(stdscr, descriptions):
    """Select a description from the last 3 tasks or enter a new one"""
    selected_index = -1
    custom_description = ""
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Select a description or enter a new one:")
        for i, desc in enumerate(descriptions):
            if i == selected_index:
                stdscr.addstr(i+1, 0, "> {}".format(desc))
            else:
                stdscr.addstr(i+1, 0, "  {}".format(desc))
        stdscr.addstr(len(descriptions)+1, 0, "Custom: {}".format(custom_description))
        stdscr.refresh()
        c = stdscr.getch()
        if c == curses.KEY_UP:
            selected_index = max(-1, selected_index - 1)
        elif c == curses.KEY_DOWN:
            selected_index = min(len(descriptions) - 1, selected_index + 1)
        elif c == ord('\n'):
            return descriptions[selected_index] if selected_index >= 0 else custom_description
        elif c == curses.KEY_BACKSPACE:
            custom_description = custom_description[:-1]
        else:
            custom_description += chr(c)

def last_descriptions_from_csv(n=3):
    """Retrieve the last n descriptions from the CSV file"""
    descriptions = []
    with open("timesheet.csv", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 2:
                descriptions.append(row[2])
    return descriptions[-n:]

def main(stdscr):
    """Main function"""
     # Read properties from the timer.properties file
    properties = parse_properties("timer.properties")

    # Perform a git pull to ensure the latest version of the code
    if check_git_pull():
        stdscr.clear()
        stdscr.addstr(0, 0, "A new version of the script has been downloaded.")
        stdscr.addstr(1, 0, "Please restart the script.")
        stdscr.refresh()
        while True:
            c = stdscr.getch()
            if c == ord('q'):
                return

    # Download timesheet.csv from the remote system
    download_timesheet(properties)


    global start_time
    curses.curs_set(1)
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    stdscr.bkgd(curses.color_pair(2))
#    stdscr.timeout(1000)  # Set timeout to 1000 ms (1 second)

    # Select or enter a description
    last_descriptions = last_descriptions_from_csv(3)
    if last_descriptions:
        stdscr.addstr(0, 0, "Select a description:")
        stdscr.refresh()
        description = select_description(stdscr, last_descriptions)
    else:
        stdscr.addstr(0, 0, "Enter a description:")
        stdscr.refresh()
        description = ""
        while True:
            c = stdscr.getch()
            if c == curses.KEY_ENTER or c == 10 or c == 13:
                break
            elif c == curses.KEY_BACKSPACE:
                description = description[:-1]
            else:
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
    stdscr.timeout(500) # Set timeout to 1000 ms (1 second)
    
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
            
            # Download again in case another system has updated this file since we last checked
            download_timesheet(properties)
            
            save_time(description, project, elapsed_time)
            
            # Upload timesheet.csv to the remote system
            upload_timesheet(properties)
            
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
