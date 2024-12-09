import pyautogui
import keyboard
import numpy as np
from PIL import ImageGrab
import pytesseract
import time
import os
import sys
from datetime import datetime, timedelta
import logging
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass
class StepMetrics:
    step_name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "🔄"  # Can be "✓", "❌", or "🔄"
    duration: Optional[float] = None
    commands_executed: int = 0
    messages_sent: int = 0

class ProjectMetrics:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.steps: Dict[str, StepMetrics] = {}
        self.current_step: Optional[str] = None
        self.metrics_file = f"logs/project_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    def start_step(self, step_name: str):
        """Start tracking a new step"""
        if self.current_step:
            self.end_step()
        
        self.current_step = step_name
        self.steps[step_name] = StepMetrics(
            step_name=step_name,
            start_time=time.time()
        )
        
    def end_step(self, status: str = "✓"):
        """End current step with given status"""
        if self.current_step and self.current_step in self.steps:
            step = self.steps[self.current_step]
            step.end_time = time.time()
            step.status = status
            step.duration = step.end_time - step.start_time
            self.save_metrics()
            
    def update_step_metrics(self, commands: int, messages: int):
        """Update metrics for current step"""
        if self.current_step and self.current_step in self.steps:
            step = self.steps[self.current_step]
            step.commands_executed = commands
            step.messages_sent = messages
            self.save_metrics()
            
    def save_metrics(self):
        """Save metrics to file"""
        os.makedirs('logs', exist_ok=True)
        metrics_data = {
            'project_name': self.project_name,
            'total_duration': self.get_total_duration(),
            'steps': {name: asdict(step) for name, step in self.steps.items()}
        }
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
            
    def get_total_duration(self) -> float:
        """Calculate total project duration"""
        total = 0.0
        for step in self.steps.values():
            if step.duration:
                total += step.duration
        return total
    
    def generate_report(self) -> str:
        """Generate a formatted report of project metrics"""
        report = [
            "╔════════════════════════════════════════════════════════╗",
            f"║ Project: {self.project_name:<45} ║",
            "╠════════════════════════════════════════════════════════╣",
            "║ Step Metrics:                                          ║"
        ]
        
        for step in self.steps.values():
            duration_str = f"{step.duration:.1f}s" if step.duration else "In Progress"
            status_line = f"║ {step.status} {step.step_name[:30]:<30} {duration_str:<10} ║"
            report.append(status_line)
            
        total_duration = self.get_total_duration()
        report.extend([
            "╠════════════════════════════════════════════════════════╣",
            f"║ Total Duration: {total_duration:.1f} seconds                        ║",
            "╚════════════════════════════════════════════════════════╝"
        ])
        
        return "\n".join(report)

class CursorAutomation:
    def __init__(self, steps_file_path=None):
        self.region = None
        self.last_text = None
        self.delay = 0.5
        self.waiting_for_completion = False
        self.messages_sent = 0
        self.commands_executed = 0
        self.is_paused = False
        self.last_status = ""
        self.running = True
        self.start_time = None
        self.seen_texts = set()
        self.current_step = None
        self.steps_file = steps_file_path or "project_steps.md"
        self.last_file_check = 0
        self.check_interval = 1  # Check file every second for Cursor updates
        self.last_file_content = None
        
        if not os.path.exists(self.steps_file):
            print(f"Warning: Steps file not found at {self.steps_file}")
            print("Please provide the correct path when starting the automation.")
            print("Example: python cursor_automation.py path/to/your/steps.md")
        
        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup logging to both file and console"""
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Find next available log number
        log_number = 1
        while os.path.exists(f'logs/log_{log_number}.txt'):
            log_number += 1
            
        # Create log filename with simple numbering
        log_filename = f'logs/log_{log_number}.txt'
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('CursorAutomation')
        self.logger.info('Starting Cursor Automation')
        self.log_filename = log_filename

    def log_action(self, message, level='info'):
        """Log an action with timestamp"""
        if level == 'error':
            self.logger.error(message)
        else:
            self.logger.info(message)

    def parse_current_step(self):
        """Parse the project steps file to find current step"""
        try:
            if not os.path.exists(self.steps_file):
                return None
                
            current_time = time.time()
            if current_time - self.last_file_check < self.check_interval:
                return self.current_step
                
            self.last_file_check = current_time
            
            # Read current file content
            with open(self.steps_file, 'r', encoding='utf-8') as f:
                current_content = f.read()
                
            # Check if file has changed
            if current_content == self.last_file_content:
                return self.current_step
                
            self.last_file_content = current_content
            lines = current_content.splitlines()
            
            # Track section hierarchy and collect all steps
            current_main_section = ""
            current_subsection = ""
            steps = []  # Store (line_number, status, full_path) tuples
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Update section tracking
                if line.startswith('## '):
                    current_main_section = line[3:].strip()
                    current_subsection = ""
                elif line.startswith('### '):
                    current_subsection = line[4:].strip()
                
                # Look for any step markers
                if any(marker in line for marker in ['🔄', '❌', '✓']):
                    # Remove all markers and clean up
                    clean_step = line.replace('🔄', '').replace('❌', '').replace('✓', '').strip('- ').strip()
                    
                    # Determine status
                    status = 'in_progress' if '🔄' in line else 'incomplete' if '❌' in line else 'complete'
                    
                    # Build full step path
                    if current_subsection:
                        full_path = [current_main_section, current_subsection, clean_step]
                    else:
                        full_path = [current_main_section, clean_step]
                    
                    steps.append((i, status, full_path))
            
            # First look for in-progress steps
            in_progress = [s for s in steps if s[1] == 'in_progress']
            if in_progress:
                # Get the earliest in-progress step
                earliest = min(in_progress, key=lambda x: x[0])
                return ' > '.join(earliest[2])
            
            # If no in-progress steps, look for earliest incomplete step
            incomplete = [s for s in steps if s[1] == 'incomplete']
            if incomplete:
                earliest = min(incomplete, key=lambda x: x[0])
                return ' > '.join(earliest[2])
                        
        except Exception as e:
            self.log_action(f"Error parsing steps file: {e}", 'error')
        return None

    def update_status(self, status=""):
        """Update the status display"""
        self.clear_console()
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Check current step from file
        new_step = self.parse_current_step()
        if new_step != self.current_step:
            self.current_step = new_step
            if new_step:
                self.log_action(f"Current step: {new_step}")
        
        print("╔════════════════════════════════════════════════════════╗")
        print("║             CURSOR AUTOMATION CONTROL PANEL             ║")
        print("╠════════════════════════════════════════════════════════╣")
        print(f"║ Runtime: {self.get_runtime()}                                    ║")
        
        if self.current_step:
            # Split long steps across multiple lines if needed
            step_parts = self.current_step.split(' > ')
            print("║ Current Step:                                          ║")
            for i, part in enumerate(step_parts):
                indent = "  " * i
                part_display = f"{indent}{part}"[:45].ljust(45)
                print(f"║   {part_display} ║")
        else:
            print("║ No current step found                                 ║")
            
        print(f"║ Messages Sent: {self.messages_sent:<3}                                    ║")
        print(f"║ Commands Executed: {self.commands_executed:<3}                               ║")
        print("╠════════════════════════════════════════════════════════╣")
        if status:
            self.last_status = status
        if self.last_status:
            truncated_status = self.last_status[:48] + "..." if len(self.last_status) > 51 else self.last_status
            print(f"║ Last Action: {truncated_status:<45} ║")
        print("╚════════════════════════════════════════════════════════╝")

    def handle_command(self, cmd):
        """Handle terminal commands"""
        cmd = cmd.lower().strip()
        if cmd.startswith('step '):
            step_name = cmd[5:].strip()
            self.set_current_step(step_name)
            self.update_status(f"Started step: {step_name}")
        elif cmd == 'complete':
            self.complete_current_step("✓")
            self.update_status("Completed current step")
        elif cmd == 'fail':
            self.complete_current_step("❌")
            self.update_status("Marked current step as failed")
        elif cmd == 'metrics':
            self.show_metrics()
        elif cmd == 'stop' or cmd == 'exit' or cmd == 'quit':
            if self.current_step:
                self.complete_current_step()
            self.running = False
            self.log_action("Stopping automation...")
            self.update_status("Stopping automation...")
        else:
            # Handle other existing commands...
            super().handle_command(cmd)

    def show_log_location(self):
        """Show the location of the log file"""
        self.clear_console()
        print("+------------------------------------------------+")
        print("|                    LOG LOCATION                 |")
        print("+------------------------------------------------+")
        print(f"| Log file: {self.log_filename}")
        print("+------------------------------------------------+")
        input("Press Enter to continue...")

    def show_help(self):
        """Show available commands"""
        self.clear_console()
        print("+------------------------------------------------+")
        print("|                 AVAILABLE COMMANDS              |")
        print("+------------------------------------------------+")
        print("| stop/exit/quit : Stop automation               |")
        print("| pause          : Pause automation              |")
        print("| resume         : Resume automation             |")
        print("| reselect       : Reselect region              |")
        print("| next           : Force next step               |")
        print("| complete       : Force complete step           |")
        print("| help           : Show this help                |")
        print("| log            : Show log location             |")
        print("+------------------------------------------------+")
        input("Press Enter to continue...")

    def handle_button(self, text):
        """Handle different button states"""
        if not text:
            return

        # More comprehensive button text detection
        accept_phrases = [
            'run command',
            'run this command',
            'run the command',
            'accept',
            'accept all',
            'command',
            'command ⌘'
        ]
        
        completed_phrases = [
            'completed',
            'done',
            'success',
            'finished'
        ]
        
        # Check for accept/run command button
        is_accept_button = any(phrase in text.lower() for phrase in accept_phrases)
        is_completed = any(phrase in text.lower() for phrase in completed_phrases)
        
        if is_accept_button and text != self.last_text:
            self.log_action(f"Found button: '{text}'")
            self.update_status(f"Found button: '{text}'")
            time.sleep(self.delay)
            
            # Try multiple methods to ensure the keypress works
            try:
                # Method 1: Direct keyboard press
                keyboard.press('ctrl')
                time.sleep(0.15)
                keyboard.press('enter')
                time.sleep(0.15)
                keyboard.release('enter')
                keyboard.release('ctrl')
                time.sleep(0.15)
                
                # Method 2: PyAutoGUI backup
                pyautogui.hotkey('ctrl', 'enter')
                
                self.commands_executed += 1
                self.log_action("Pressed Ctrl+Enter")
                self.update_status("Pressed Ctrl+Enter")
                self.waiting_for_completion = True
                
            except Exception as e:
                self.log_action(f"Error pressing Ctrl+Enter: {e}", 'error')
                self.update_status(f"Error pressing Ctrl+Enter: {e}")
                
        elif is_completed and self.waiting_for_completion:
            self.log_action("Task completed, continuing implementation")
            self.update_status("Task completed, continuing implementation")
            time.sleep(0.5)
            self.type_continue_implementation()
            self.waiting_for_completion = False
                
        elif 'generating' in text.lower() or 'loading' in text.lower():
            if text != self.last_text:
                self.log_action("Waiting for generation...")
                self.update_status("Waiting for generation...")
            
        elif 'cancel' in text.lower() or 'skip' in text.lower():
            if text != self.last_text:
                self.log_action("Cancel/Skip button detected, waiting...")
                self.update_status("Cancel/Skip button detected, waiting...")
            
        self.last_text = text

    def run(self):
        """Main automation loop"""
        self.update_status("Starting automation... Type 'help' for commands")
        
        import threading
        def command_thread():
            while self.running:
                try:
                    cmd = input().strip()
                    if cmd:
                        self.handle_command(cmd)
                        print("\nEnter command > ", end='', flush=True)
                except EOFError:
                    break

        # Start command thread
        threading.Thread(target=command_thread, daemon=True).start()
        
        while self.running:
            if not self.is_paused:
                text = self.get_button_text()
                if text:  # Only process if text is found
                    self.handle_button(text)
            time.sleep(0.5)  # Slightly increased to reduce CPU usage

    def clear_console(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_button_text(self):
        """Get text from the button area"""
        try:
            screenshot = self.take_screenshot()
            if screenshot:
                # Try multiple OCR configurations for better detection
                configs = [
                    '--psm 7 --oem 3',  # Single line
                    '--psm 6 --oem 3',  # Uniform block of text
                    '--psm 3 --oem 3'   # Fully automatic
                ]
                
                for config in configs:
                    text = pytesseract.image_to_string(screenshot, config=config).lower().strip()
                    if text:
                        if text not in self.seen_texts:
                            self.seen_texts.add(text)
                            self.log_action(f"New text detected: '{text}'")
                            self.update_status(f"New text detected: '{text}'")
                        return text
        except Exception as e:
            self.log_action(f"Error reading text: {e}", 'error')
            self.update_status(f"Error reading text: {e}")
        return ""

    def type_continue_implementation(self):
        """Send message to continue with implementation"""
        keyboard.press_and_release('ctrl+/')
        time.sleep(0.5)
        message = "continue with the steps and update the project steps with what we have completed and whats in progress and the implementation unless there is something critical you need to add or unless the test scripts dont show 100% functionality"
        pyautogui.write(message)
        time.sleep(0.5)
        pyautogui.press('enter')
        self.messages_sent += 1
        self.log_action("Sent continue message")
        self.update_status("Sent continue message")

    def type_complete_current_step(self):
        """Send message to complete current step"""
        keyboard.press_and_release('ctrl+/')
        time.sleep(0.5)
        message = "complete the current steps functionality"
        pyautogui.write(message)
        time.sleep(0.5)
        pyautogui.press('enter')
        self.messages_sent += 1
        self.update_status("Sent: Complete current step")

    def type_next_step(self):
        """Send message to move to next step"""
        keyboard.press_and_release('ctrl+/')
        time.sleep(0.5)
        message = "move on to the next step"
        pyautogui.write(message)
        time.sleep(0.5)
        pyautogui.press('enter')
        self.messages_sent += 1
        self.update_status("Sent: Move to next step")

    def take_screenshot(self):
        """Take a screenshot of the selected region"""
        try:
            screenshot = ImageGrab.grab(bbox=self.region)
            # Increase size and contrast for better OCR
            width, height = screenshot.size
            screenshot = screenshot.resize((width * 3, height * 3))  # Bigger resize
            return screenshot
        except Exception as e:
            self.update_status(f"Screenshot error: {e}")
            return None

    def select_region(self):
        """Let user select the region to monitor"""
        self.clear_console()
        print("╔════════════════════════════════════════════════════════╗")
        print("║               REGION SELECTION MODE                     ║")
        print("╠════════════════════════════════════════════════════════╣")
        print("║ 1. Move mouse to top-left corner of the button area    ║")
        print("║ 2. Press 'S' to start                                  ║")
        print("╚════════════════════════════════════════════════════════╝")
        
        while not keyboard.is_pressed('s'):
            time.sleep(0.1)
        x1, y1 = pyautogui.position()
        time.sleep(0.5)
        
        self.clear_console()
        print("╔════════════════════════════════════════════════════════╗")
        print("║               REGION SELECTION MODE                     ║")
        print("╠════════════════════════════════════════════════════════╣")
        print("║ Now move to bottom-right corner and press 'S' again    ║")
        print("╚════════════════════════════════════════════════════════╝")
        
        while not keyboard.is_pressed('s'):
            time.sleep(0.1)
        x2, y2 = pyautogui.position()
        
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        
        self.region = (left, top, right, bottom)
        
        # Add 3-second countdown
        for i in range(3, 0, -1):
            self.clear_console()
            print("╔═══════════════════════════════════════════════════════╗")
            print("║               STARTING AUTOMATION                       ║")
            print("╠════════════════════════════════════════════════════════╣")
            print(f"║ Region selected: {right-left}x{bottom-top} pixels           ║")
            print(f"║ Starting in {i} seconds...                               ║")
            print("╚════════════════════════════════════════════════════════╝")
            time.sleep(1)
        
        self.start_time = time.time()
        self.update_status(f"Region selected: ({right-left}x{bottom-top})")

    def get_runtime(self):
        """Get formatted runtime string"""
        if not self.start_time:
            return "00:00:00"
        seconds = int(time.time() - self.start_time)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def validate_file_format(self):
        """Validate file format and return diagnostic info"""
        try:
            with open(self.steps_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            lines = content.splitlines()
            diagnostics = {
                'has_sections': False,
                'has_subsections': False,
                'has_progress_markers': False,
                'has_incomplete_markers': False,
                'total_steps': 0,
                'in_progress': 0,
                'completed': 0,
                'incomplete': 0,
                'issues': [],
                'warnings': []
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith('## '):
                    diagnostics['has_sections'] = True
                elif line.startswith('### '):
                    diagnostics['has_subsections'] = True
                elif '✓' in line:
                    diagnostics['completed'] += 1
                    diagnostics['total_steps'] += 1
                elif '❌' in line:
                    diagnostics['has_incomplete_markers'] = True
                    diagnostics['incomplete'] += 1
                    diagnostics['total_steps'] += 1
                elif '🔄' in line:
                    diagnostics['has_progress_markers'] = True
                    diagnostics['in_progress'] += 1
                    diagnostics['total_steps'] += 1
                    
            # Check for critical issues
            if not diagnostics['has_sections']:
                diagnostics['issues'].append("No sections (##) found. File should have sections marked with ##")
            if not diagnostics['has_progress_markers'] and not diagnostics['has_incomplete_markers']:
                diagnostics['issues'].append("No progress (🔄) or incomplete (❌) markers found")
                
            # Add warnings for non-critical issues
            if diagnostics['in_progress'] > 1:
                diagnostics['warnings'].append(f"Multiple in-progress (🔄) steps found: {diagnostics['in_progress']}")
                
            return diagnostics
            
        except Exception as e:
            return {'error': str(e), 'issues': [f"Error reading file: {e}"]}

    def show_startup_check(self):
        """Show startup diagnostic information"""
        self.clear_console()
        print("+------------------------------------------------+")
        print("|             CURSOR AUTOMATION FILE CHECK        |")
        print("+------------------------------------------------+")
        print(f"| File: {self.steps_file}")
        
        diagnostics = self.validate_file_format()
        
        if 'error' in diagnostics:
            print("+------------------------------------------------+")
            print("| ERROR READING FILE:                             |")
            print(f"| {diagnostics['error']:<52} |")
            print("+------------------------------------------------+")
            input("\nPress Enter to exit...")
            sys.exit(1)
            
        print("+------------------------------------------------+")
        print("| File Statistics:                                |")
        print(f"| • Total Steps: {diagnostics['total_steps']:<42} |")
        print(f"| • Completed: {diagnostics['completed']:<44} |")
        print(f"| • In Progress: {diagnostics['in_progress']:<41} |")
        print(f"| • Incomplete: {diagnostics['incomplete']:<42} |")
        
        if diagnostics['issues']:
            print("+------------------------------------------------+")
            print("| Critical Issues Found:                          |")
            for issue in diagnostics['issues']:
                print(f"| • {issue:<52} |")
            print("|                                                |")
            print("| File should have:                              |")
            print("| 1. Sections marked with ##                     |")
            print("| 2. Steps marked with ✓ (complete)              |")
            print("|    🔄 (in progress) or ❌ (incomplete)         |")
            input("\nPress Enter to exit...")
            sys.exit(1)
            
        if diagnostics['warnings']:
            print("+------------------------------------------------+")
            print("| Warnings:                                       |")
            for warning in diagnostics['warnings']:
                print(f"| • {warning:<52} |")
            print("|                                                |")
            print("| Note: Will proceed with earliest in-progress step |")
        
        current_step = self.parse_current_step()
        if current_step:
            print("+------------------------------------------------+")
            print("| Current Step:                                   |")
            step_parts = current_step.split(' > ')
            for i, part in enumerate(step_parts):
                indent = "  " * i
                part_display = f"{indent}{part}"[:45].ljust(45)
                print(f"|   {part_display} |")
        else:
            print("+------------------------------------------------+")
            print("| No current step found - Add 🔄 to your current step |")
            
        print("+------------------------------------------------+")
        print("| File format looks good! Ready to start automation. |")
        print("+------------------------------------------------+")
        
        input("\nPress Enter to continue or Ctrl+C to exit...")

def main():
    print("+------------------------------------------------+")
    print("|              CURSOR AUTOMATION SETUP            |")
    print("+------------------------------------------------+")
    print("| Paste your steps file path (or press Enter for default)|")
    print("+------------------------------------------------+")
    
    steps_file = input("File path > ").strip()
    if not steps_file:
        steps_file = "project_steps.md"
        print("Using default: project_steps.md")
    
    if not os.path.exists(steps_file):
        print(f"Error: File not found at {steps_file}")
        print("Please check the path and try again.")
        return
        
    automation = CursorAutomation(steps_file)
    
    # Run startup checks
    automation.show_startup_check()
    
    print("Starting automation in 3 seconds...")
    time.sleep(3)
    
    automation.select_region()
    automation.run()

if __name__ == "__main__":
    main()