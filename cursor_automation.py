import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
import keyboard
import numpy as np
from PIL import ImageGrab, ImageEnhance
import pytesseract
import time
import os
import logging
from datetime import datetime
import sys
import threading

class CursorAutomation:
    def __init__(self):
        self.region = None
        self.last_text = None
        self.delay = 0.5
        self.running = True
        self.is_paused = False
        self.selection_timeout = 30  # 30 seconds timeout for selection
        self.check_dependencies()
        self.setup_logging()
        self.setup_gui()

    def check_dependencies(self):
        """Check if required dependencies are installed"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except Exception as e:
            messagebox.showerror("Error", 
                "Tesseract OCR is not installed or not in PATH.\n"
                "Please install Tesseract OCR and try again.")
            sys.exit(1)

    def setup_logging(self):
        """Setup logging to file with rotation"""
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        log_filename = f'logs/automation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('CursorAutomation')

    def setup_gui(self):
        """Setup the GUI window"""
        self.root = tk.Tk()
        self.root.title("Cursor Automation")
        self.root.geometry("400x350")
        
        # Make window appear on top
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.update()
        
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TLabel', padding=5)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status label with better visibility
        self.status_var = tk.StringVar(value="Ready to start")
        status_label = ttk.Label(
            main_frame, 
            textvariable=self.status_var,
            wraplength=380,
            background='white',
            relief='solid',
            padding=5
        )
        status_label.grid(row=0, column=0, columnspan=2, pady=10, sticky='ew')
        
        # Region info
        self.region_var = tk.StringVar(value="No region selected")
        region_label = ttk.Label(
            main_frame,
            textvariable=self.region_var,
            background='white',
            relief='solid',
            padding=5
        )
        region_label.grid(row=1, column=0, columnspan=2, pady=5, sticky='ew')
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        select_btn = ttk.Button(
            btn_frame,
            text="Select Region",
            command=self.start_region_selection,
            width=20
        )
        select_btn.grid(row=0, column=0, padx=5)
        
        self.toggle_btn = ttk.Button(
            btn_frame,
            text="Start",
            command=self.toggle_automation,
            width=20
        )
        self.toggle_btn.grid(row=0, column=1, padx=5)
        
        # Cancel button for region selection
        self.cancel_btn = ttk.Button(
            main_frame,
            text="Cancel Selection",
            command=self.cancel_selection,
            state='disabled'
        )
        self.cancel_btn.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Instructions with better formatting
        instructions = """
Instructions:
1. Click 'Select Region' to choose the button area
2. Move mouse to top-left corner and press 'S'
3. Move mouse to bottom-right corner and press 'S'
4. Click 'Start' to begin automation
5. Press 'ESC' at any time to cancel selection
        """
        instr_label = ttk.Label(
            main_frame,
            text=instructions,
            justify=tk.LEFT,
            background='white',
            relief='solid',
            padding=10
        )
        instr_label.grid(row=4, column=0, columnspan=2, pady=10, sticky='ew')
        
        # Error display
        self.error_var = tk.StringVar()
        self.error_label = ttk.Label(
            main_frame,
            textvariable=self.error_var,
            foreground='red',
            wraplength=380
        )
        self.error_label.grid(row=5, column=0, columnspan=2, pady=5)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(100, self.update_gui)
        
        # Bind escape key
        self.root.bind('<Escape>', lambda e: self.cancel_selection())

    def update_gui(self):
        """Update GUI elements"""
        if self.running and not self.is_paused:
            try:
                text = self.get_button_text()
                if text:
                    self.handle_button(text)
                self.error_var.set("")  # Clear any error message
            except Exception as e:
                self.error_var.set(f"Error: {str(e)}")
                self.logger.error(f"Error in update_gui: {e}")
        
        if self.running:
            self.root.after(100, self.update_gui)

    def start_region_selection(self):
        """Start the region selection process"""
        self.selection_cancelled = False
        self.cancel_btn.configure(state='normal')
        self.status_var.set("Move to top-left corner and press 'S'")
        
        # Use a thread for selection to keep GUI responsive
        self.selection_thread = threading.Thread(target=self._select_region_thread)
        self.selection_thread.daemon = True
        self.selection_thread.start()

    def _select_region_thread(self):
        """Thread function for region selection"""
        try:
            # First point
            start_time = time.time()
            while not self.selection_cancelled and time.time() - start_time < self.selection_timeout:
                if keyboard.is_pressed('s'):
                    x1, y1 = pyautogui.position()
                    break
                time.sleep(0.1)
            else:
                if not self.selection_cancelled:
                    self.root.after(0, lambda: self.status_var.set("Selection timed out"))
                return

            time.sleep(0.5)  # Debounce
            
            # Second point
            self.root.after(0, lambda: self.status_var.set("Move to bottom-right corner and press 'S'"))
            start_time = time.time()
            while not self.selection_cancelled and time.time() - start_time < self.selection_timeout:
                if keyboard.is_pressed('s'):
                    x2, y2 = pyautogui.position()
                    break
                time.sleep(0.1)
            else:
                if not self.selection_cancelled:
                    self.root.after(0, lambda: self.status_var.set("Selection timed out"))
                return

            if self.selection_cancelled:
                return

            # Process selection
            left = min(x1, x2)
            top = min(y1, y2)
            right = max(x1, x2)
            bottom = max(y1, y2)
            
            if right - left < 10 or bottom - top < 10:
                self.root.after(0, lambda: self.status_var.set("Selected region too small"))
                return
                
            self.region = (left, top, right, bottom)
            self.root.after(0, lambda: self.region_var.set(f"Region: {right-left}x{bottom-top} pixels"))
            self.root.after(0, lambda: self.status_var.set("Region selected. Click Start to begin automation."))
            self.logger.info(f"Region selected: {self.region}")
            
        except Exception as e:
            self.logger.error(f"Error in region selection: {e}")
            self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.cancel_btn.configure(state='disabled'))

    def cancel_selection(self):
        """Cancel the region selection process"""
        self.selection_cancelled = True
        self.status_var.set("Selection cancelled")
        self.cancel_btn.configure(state='disabled')

    def toggle_automation(self):
        """Toggle automation on/off"""
        if not self.region:
            self.status_var.set("Please select a region first")
            return
            
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.toggle_btn.configure(text="Start")
            self.status_var.set("Automation paused")
        else:
            self.toggle_btn.configure(text="Pause")
            self.status_var.set("Automation running")

    def on_closing(self):
        """Handle window closing"""
        self.running = False
        self.selection_cancelled = True
        self.root.destroy()

    def handle_button(self, text):
        """Handle different button states"""
        if not text or text == self.last_text:
            return

        accept_phrases = [
            'run command',
            'run this command',
            'run the command',
            'accept',
            'accept all',
            'command',
            'command ⌘'
        ]
        
        if any(phrase in text.lower() for phrase in accept_phrases):
            self.logger.info(f"Found button: '{text}'")
            self.status_var.set(f"Found button: '{text}'")
            time.sleep(self.delay)
            
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
                
                self.logger.info("Pressed Ctrl+Enter")
                self.status_var.set("Pressed Ctrl+Enter")
                
            except Exception as e:
                self.logger.error(f"Error pressing Ctrl+Enter: {e}")
                self.status_var.set(f"Error: {str(e)}")
                
        self.last_text = text

    def get_button_text(self):
        """Get text from the button area"""
        try:
            screenshot = self.take_screenshot()
            if screenshot:
                # Enhance image for better OCR
                enhancer = ImageEnhance.Contrast(screenshot)
                screenshot = enhancer.enhance(2.0)  # Increase contrast
                
                configs = [
                    '--psm 7 --oem 3',  # Single line
                    '--psm 6 --oem 3',  # Uniform block of text
                    '--psm 3 --oem 3'   # Fully automatic
                ]
                
                for config in configs:
                    text = pytesseract.image_to_string(screenshot, config=config).lower().strip()
                    if text:
                        return text
        except Exception as e:
            self.logger.error(f"Error reading text: {e}")
            self.status_var.set(f"Error: {str(e)}")
        return ""

    def take_screenshot(self):
        """Take a screenshot of the selected region"""
        try:
            if not self.region:
                return None
                
            screenshot = ImageGrab.grab(bbox=self.region)
            width, height = screenshot.size
            if width == 0 or height == 0:
                raise ValueError("Invalid screenshot dimensions")
                
            screenshot = screenshot.resize((width * 3, height * 3))
            return screenshot
        except Exception as e:
            self.logger.error(f"Screenshot error: {e}")
            return None

    def run(self):
        """Start the GUI application"""
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            messagebox.showerror("Error", f"Application error: {str(e)}")

def main():
    try:
        automation = CursorAutomation()
        automation.run()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start application: {str(e)}")
        logging.error(f"Application failed to start: {e}")

if __name__ == "__main__":
    main()