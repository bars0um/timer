from datetime import datetime, timedelta
import sys
import os
import time
import csv
import subprocess
import logging
from tkinter import Tk, Label, Button, Entry, Listbox, StringVar, Toplevel, Text, BOTH, YES, NONE, DISABLED, Scrollbar, RIGHT, Frame, Canvas, Y
import argparse

from tkinter import ttk
from tkinter.ttk import Combobox
from datetime import datetime
from collections import defaultdict

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours} hours {minutes} minutes {seconds} seconds"


def check_git_pull():
    """Performs a git pull and checks if any changes were made."""
    result = subprocess.run(["git", "pull"], capture_output=True, text=True)
    logging.info(f"git check results: {result}")
    return "Already up to date." not in result.stdout

def save_time(description, project, elapsed_time_seconds,start_time_str):
        """Save elapsed time to CSV file"""
        elapsed_time_hours = int(elapsed_time_seconds / 3600)
        elapsed_time_minutes = int((elapsed_time_seconds % 3600) / 60)
        elapsed_time_seconds = int(elapsed_time_seconds % 60)
        elapsed_time_str = "{:02d}:{:02d}:{:02d}".format(elapsed_time_hours, elapsed_time_minutes, elapsed_time_seconds)
        
        with open(properties['timesheet_path'], "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([start_time_str, elapsed_time_str, description, project])

def download_timesheet(properties):
    if not properties['remote_save'] == "true":
        return
    """Downloads timesheet.csv from the remote system using SCP."""
    remote_path = f"{properties['host']}:{properties['path']}/timesheet.csv"
    subprocess.run(["scp", remote_path, properties['timesheet_path']])
    logging.info(f"Downloading latest version of timesheet...scp {remote_path} {properties['timesheet_path']}")



def upload_timesheet(properties):
    if not properties['remote_save'] == "true":
        return
    """Uploads timesheet.csv to the remote system using SCP."""
    logging.info(f"Uploading latest version of timesheet...")
    remote_path = f"{properties['host']}:{properties['path']}/timesheet.csv"
    subprocess.run(["scp", properties['timesheet_path'], remote_path])
    
def parse_properties(filename):
    properties = {}
    with open(filename, "r") as f:
        for line in f:
            key, value = line.strip().split("=", 1)
            properties[key] = value
    return properties

# Set up logging


class TimesheetApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Timesheet App")
        
        self.start_time = None
        self.project_var = StringVar()
        self.already_started = False
        self.paused = False 
        # Initialize labels for description and project titles
        self.description_label = Label(master, text="")
        self.project_label = Label(master, text="")
        self.timer_label = Label(master, text="", font=("Helvetica", 35))
        
        # Get unique descriptions and projects and the last description and project from timesheet.csv
        self.unique_descriptions, self.unique_projects, last_description, last_project = self.get_unique_data()
        
        self.description_combobox = Combobox(master, values=self.unique_descriptions)
        self.description_combobox.pack()
        if last_description:
            self.description_combobox.set(last_description)
        else:
            self.description_combobox.set("Select or type a description")
        
        self.project_combobox = Combobox(master, values=self.unique_projects)
        self.project_combobox.pack()
        if last_project:
            self.project_combobox.set(last_project)
        else:
            self.project_combobox.set("Select or type a project")
        
        self.start_button = Button(master, text="Start Timer", command=self.start_timer)
        self.stop_button = Button(master, text="Stop Timer", command=self.stop_timer)
        self.save_button = Button(master, text="Save Entry", command=self.save_entry)
        self.start_button.pack()
        
        self.details_button = Button(master, text="Summary", command=self.show_details_window)
        self.details_button.pack()
        # Add a button to resume the timer
        self.resume_button = Button(master, text="Resume Timer", command=self.resume_timer)
        
        self.update_clock()

    def get_descriptions_with_durations(self):
        data = []
        monthly_data = defaultdict(lambda: {'entries': [], 'total_duration': timedelta(), 'project_durations': defaultdict(timedelta)})

        try:
            with open(properties['timesheet_path'], 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        start_date_time, elapsed_time, description, project = row
                        start_dt = datetime.strptime(start_date_time, '%Y-%m-%d %H:%M:%S')
                        elapsed_h, elapsed_m, elapsed_s = map(int, elapsed_time.split(':'))
                        elapsed_td = timedelta(hours=elapsed_h, minutes=elapsed_m, seconds=elapsed_s)

                        month_key = start_dt.strftime('%Y-%m')
                        monthly_data[month_key]['entries'].append({
                            'Date': start_dt.strftime('%Y-%m-%d'), 
                            'Description': description, 
                            'Duration': elapsed_td,
                            'Project': project
                        })
                        monthly_data[month_key]['total_duration'] += elapsed_td
                        monthly_data[month_key]['project_durations'][project] += elapsed_td

            for month_key, month_data in monthly_data.items():
                month_name = datetime.strptime(month_key, '%Y-%m').strftime('%B %Y')
                data.append({'Date': f'Month: {month_name}', 'Description': '', 'Duration': '', 'Project': 'All'})
                data.extend(month_data['entries'])
                for project, duration in month_data['project_durations'].items():
                    # Append monthly total for each project
                    data.append({
                        'Date': 'Monthly Total', 
                        'Description': '', 
                        'Duration': format_timedelta(duration),
                        'Project': project
                    })

        except FileNotFoundError:
            pass

        return data

    def update_summary_view(self, scrollable_frame, project_filter):
        bg_color1 = "#703224"  # A light gray color

        # Clear previous content
        for widget in scrollable_frame.winfo_children():
            widget.destroy()

        # Filtered data based on project
        descriptions_with_durations = self.get_descriptions_with_durations()
        
        if project_filter:
            descriptions_with_durations = [item for item in descriptions_with_durations if item.get('Project') == project_filter or (item.get('Date') == 'Monthly Total' and item.get('Project') == project_filter)]

        logging.info(f"showing {project_filter}")

         # Display filtered data
        for index, row_data in enumerate(descriptions_with_durations):
            if "Month:" in row_data['Date']:
                Label(scrollable_frame, text=row_data['Date'], width=70, bg=bg_color1, anchor='w').grid(row=index, column=0, columnspan=4)
            elif "Monthly Total" in row_data['Date']:
                #Label(scrollable_frame, text=row_data['Date'], width=10, anchor='w').grid(row=index, column=0)
                #Label(scrollable_frame, text=row_data['Description'], width=50, anchor='w').grid(row=index, column=1)
                Label(scrollable_frame, text=row_data['Duration'], width=70,bg=bg_color1, anchor='center').grid(row=index, column=0, columnspan=4)  # Center align the duration
            else:
                Label(scrollable_frame, text=row_data['Date'], width=10).grid(row=index, column=0)
                Label(scrollable_frame, text=row_data['Description'], width=50).grid(row=index, column=1)
                Label(scrollable_frame, text=row_data['Duration'], width=10).grid(row=index, column=2)
     
        return descriptions_with_durations

    def show_details_window(self):
        bg_color1 = "#703224"  # A light gray color

        new_window = Toplevel(self.master)
        new_window.title("Details Window")


        # Retrieve the currently selected project
        selected_project = self.project_combobox.get()

        # Project selection for filtering
        project_filter_var = StringVar(value=selected_project)
        project_filter_combobox = Combobox(new_window, textvariable=project_filter_var, values=self.unique_projects)
        project_filter_combobox.pack()

        # Button to apply filter
        filter_button = Button(new_window, text="Filter", command=lambda: self.update_summary_view(scrollable_frame, project_filter_var.get()))
        filter_button.pack()
 
        # Set initial size
        new_window.geometry("800x600")  # Adjust width (800) and height (600) as per your requirement
    

        canvas = Canvas(new_window)
        scrollbar = Scrollbar(new_window, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind the mouse wheel event to the canvas scroll
        #canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-1*(event.delta//120), "units"))
        new_window.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-1*(event.delta//120), "units"))

        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        

        descriptions_with_durations = self.update_summary_view(scrollable_frame, None)

        for index, row_data in enumerate(descriptions_with_durations):
            if "Month:" in row_data['Date']:
                Label(scrollable_frame, text=row_data['Date'], width=70, bg=bg_color1, anchor='w').grid(row=index, column=0, columnspan=4)
            elif "Monthly Total" in row_data['Date']:
                #Label(scrollable_frame, text=row_data['Date'], width=10, anchor='w').grid(row=index, column=0)
                #Label(scrollable_frame, text=row_data['Description'], width=50, anchor='w').grid(row=index, column=1)
                Label(scrollable_frame, text=row_data['Duration'], width=70,bg=bg_color1, anchor='center').grid(row=index, column=0, columnspan=4)  # Center align the duration
            else:
                Label(scrollable_frame, text=row_data['Date'], width=10).grid(row=index, column=0)
                Label(scrollable_frame, text=row_data['Description'], width=50).grid(row=index, column=1)
                Label(scrollable_frame, text=row_data['Duration'], width=10).grid(row=index, column=2)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def get_unique_data(self):
        descriptions = set()
        projects = set()
        last_description = None
        last_project = None

        try:
            with open(properties['timesheet_path'], 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                       # print(row)
                        descriptions.add(row[2])  # Assuming description is in the first column
                        projects.add(row[3])  # Assuming project is in the second column
                        last_description = row[2]
                        last_project = row[3]
        except FileNotFoundError:
            pass  # File not found, return empty sets and None values

        return list(descriptions), list(projects), last_description, last_project

        
    def start_timer(self):
        # Get the selected description and project
        self.description = self.description_combobox.get()
        self.project = self.project_combobox.get()

        # Hide the input fields and display the timer and titles
        self.description_combobox.pack_forget()
        self.project_combobox.pack_forget()
        self.start_button.pack_forget()
        
        self.project_label.config(text=f"{self.project}")
        self.project_label.pack()

        self.description_label.config(text=f"{self.description}")
        self.description_label.pack()

        if not self.already_started:
            self.start_time = time.time()
            self.already_started = True

        self.timer_label.pack()
        # Display the stop button when the timer starts
        self.stop_button.pack()
        self.update_clock()
    
    def stop_timer(self):
        self.pause_start_time = time.time()
        self.paused = True
        self.start_time_str  = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time))
        self.elapsed_time = time.time() - self.start_time

        # Hide the timer label and stop button, and show the input fields again
        self.resume_button.pack()
        self.save_button.pack()
        self.stop_button.pack_forget()
        
        
        # Reset the start time to stop the timer
        #self.start_time = None

    def resume_timer(self):
        self.paused = False
        pause_duration = time.time() - self.pause_start_time
        self.start_time += pause_duration
        self.resume_button.pack_forget()  # Hide the resume button
        self.save_button.pack_forget()  # Hide the save button when resuming
        self.start_button.invoke()  # Invoke the start button's action to start the timer again


        
    def save_entry(self):
        self.save_button.pack_forget()
        # Download again in case another system has updated this file since we last checked
        download_timesheet(properties)
        save_time(self.description,self.project, self.elapsed_time,self.start_time_str)
        # Upload timesheet.csv to the remote system
        upload_timesheet(properties)
        logging.info('done uploading new time entry, shutting down timer')
        self.master.destroy()

    def update_clock(self):
        if self.start_time and not self.paused:
            elapsed_time = time.time() - self.start_time 
            mins, sec = divmod(elapsed_time, 60)
            hours, mins = divmod(mins, 60)
            self.timer_label.config(text="Elapsed time:\n{:02d}:{:02d}:{:02d}".format(int(hours), int(mins), int(sec)))
            
            # Update the timer label every second
            self.master.after(1000, self.update_clock)
        

    def format_time(self, duration):
        """Format duration as hours, minutes, and seconds"""
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "{:02d}:{:02d}:{:02d}".format(int(hours), int(minutes), int(seconds))

# Run the Tkinter app
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Track Time')
    parser.add_argument('-log', dest='loglevel', type=str, default='info', required=False, help='log level')
    parser.add_argument('-work', dest='workdir', type=str, default='.')
    parser.add_argument('-host', dest='host', type=str, default='timer')
    parser.add_argument('-hostpath', dest='hostpath', type=str, default='~/timer')
    parser.add_argument('-remote', dest='remote', type=str, default='true')

    args = parser.parse_args()
    args.workdir = os.path.expanduser(args.workdir)  # Add this line to expand '~' to the user's home directory

    properties = {
        "host": args.host,
        "path": args.hostpath,
        "workdir": args.workdir,
        "remote_save": args.remote,
        "timesheet_path" : f"{args.workdir}{os.sep}timesheet.csv"
    }
    log_path = f"{properties['workdir']}{os.sep}timer.log"
    
    logging.basicConfig(filemode="w",force=True,filename=f"{log_path}", level=args.loglevel.upper(), format="%(asctime)s - %(levelname)s - %(message)s")
    
    logging.info("started timer app")
    #sys.exit()

    root = Tk()
    # Read properties from the timer.properties file
    
    # Download timesheet.csv from the remote system
    download_timesheet(properties)
    app = TimesheetApp(root)
    root.mainloop()

