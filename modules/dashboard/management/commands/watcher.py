import os
import time
import sqlite3
import xmltodict

class RunfolderWatcher:
    def __init__(self, db_path, watch_dirs):
        self.db_path = db_path
        self.watch_dirs = watch_dirs
        self.init_db()
    
    def init_db(self):
        # Create SQLite table for runfolder data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS runfolders (
                id INTEGER PRIMARY KEY,
                runfolder_name TEXT UNIQUE,
                runfolder_path TEXT UNIQUE,
                instrument_id TEXT,
                flowcell_id TEXT,
                run_date TEXT,
                run_start_time TEXT,
                run_end_time TEXT,
                status TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def scan_runfolders(self):
        # Scan directories for runfolders and update database
        for dir in self.watch_dirs:
            for root, dirs, files in os.walk(dir):
                for dir in dirs:
                    if dir.startswith('.'):
                        continue
                    else:
                        runfolder_path = os.path.join(root, dir)
                        self.extract_run_info(runfolder_path)
    

    def extract_run_info(self, runfolder_path):
        # Parse RunInfo.xml, RunParameters.xml, RunCompletionStatus.xml
        run_info = self.parse_run_info(runfolder_path)
        run_parameters = self.parse_run_parameters(runfolder_path)
        run_completion_status = self.parse_completion_status(runfolder_path)
        state = self.determine_runfolder_state(runfolder_path)
        self.update_database(run_info, run_parameters, run_completion_status)

    def parse_run_info(self, runfolder_path):
        xml_path = os.path.join(runfolder_path, "RunInfo.xml")
        if not os.path.exists(xml_path):
            return None
        
        tree = xmltodict.parse(xml_path)
        root = tree.getroot()
        
        run = root.find("Run")
        return {
            "run_id": run.get("Id"),
            "run_number": run.get("Number"), 
            "flowcell": run.find("Flowcell").text,
            "instrument": run.find("Instrument").text,
            "date": run.find("Date").text
        }

    def parse_run_parameters(self, runfolder_path):
        xml_path = os.path.join(runfolder_path, "RunParameters.xml")
        if not os.path.exists(xml_path):
            return None
        
        tree = xmltodict.parse(xml_path)
        root = tree.getroot()
        
        return {
            "run_start_time": root.find("RunStartTime").text,
            "run_end_time": root.find("RunEndTime").text if root.find("RunEndTime") else None
        }      

    def determine_runfolder_state(self, runfolder_path):
        """Determine state based on file presence"""

        run_completion_status_path = os.path.join(runfolder_path, "RunCompletionStatus.xml") if os.path.exists(os.path.join(runfolder_path, "RunCompletionStatus.xml")) else None
        copy_complete_path = os.path.join(runfolder_path, "CopyComplete.txt") if os.path.exists(os.path.join(runfolder_path, "CopyComplete.txt")) else None
        rta_complete_path = os.path.join(runfolder_path, "RTAComplete.txt") if os.path.exists(os.path.join(runfolder_path, "RTAComplete.txt")) else None
        run_parameters_path = os.path.join(runfolder_path, "RunParameters.xml") if os.path.exists(os.path.join(runfolder_path, "RunParameters.xml")) else None

        # how to avoid race conditions here?
        if (run_parameters_path and copy_complete_path and rta_complete_path) and not run_completion_status_path:
            state = "sequencing"
        elif run_parameters_path and copy_complete_path and rta_complete_path and run_completion_status_path:
            state = "finished"
        else:
            state = "initializing"
        
        completion_status = self.parse_completion_status(run_completion_status_path)
        return {
            "state": state,
            "completion_status": completion_status
        }

    def parse_completion_status(self, run_completion_status_path):
        if not run_completion_status_path:
            return None
        # Parse completion details
        tree = xmltodict.parse(run_completion_status_path)
        root = tree.getroot()
        completion_status = root.find("CompletionStatus").text
        completion_time = root.find("CompletionTime").text
        return {
            "completion_status": completion_status,
            "completion_time": completion_time
        }

    def update_database(self, run_info, run_parameters, run_completion_status):
        # Update database with run information
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO runfolders (runfolder_name, runfolder_path, instrument_id, flowcell_id, run_date, run_start_time, run_end_time, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (run_info["run_id"], run_info["run_number"], run_info["flowcell"], run_info["instrument"], run_info["date"], run_parameters["run_start_time"], run_parameters["run_end_time"], run_completion_status["completion_status"], run_completion_status["completion_time"], time.time()))
        conn.commit()
        conn.close()

def main():
    # Simple config
    WATCH_DIRS = ["/data/runs"]
    DB_PATH = "runfolders.db"
    
    watcher = RunfolderWatcher(DB_PATH, WATCH_DIRS)
    
    while True:
        watcher.scan_runfolders()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()