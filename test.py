import time
from datetime import datetime
from pathlib import Path
import subprocess
import win32com.client as win32
import pyautogui
import threading

# Kill existing Excel processes
subprocess.run(['taskkill', '/f', '/im', 'excel.exe'], capture_output=True)
time.sleep(2)

# Function to automatically click "No" on the Genpact popup
def auto_click_no():
    time.sleep(3)  # Wait for Excel to start
    while True:
        try:
            # Look for the Genpact popup window
            popup = pyautogui.locateOnScreen(pyautogui.size(), confidence=0.7)
            # Check if popup exists by looking for "Genpact" or "Classification" text
            screenshot = pyautogui.screenshot()
            if "Classification" in str(pyautogui.locateAll):
                # Press 'N' key for "No" or click the No button
                pyautogui.press('n')  # Alt+N or just N
                time.sleep(0.5)
                pyautogui.press('enter')
                print("✓ Auto-clicked 'No' on classification popup")
        except:
            pass
        time.sleep(1)

# Start auto-clicker in background
clicker_thread = threading.Thread(target=auto_click_no, daemon=True)
clicker_thread.start()

# Create file path
documents_path = Path.home() / "Documents"
documents_path.mkdir(parents=True, exist_ok=True)
filename = documents_path / f"excel_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
filename = str(filename)

print(f"Saving to: {filename}")
print("Starting Excel...")
print("Press Ctrl+C to stop logging\n")

try:
    # Start Excel
    excel = win32.Dispatch("Excel.Application")
    excel.DisplayAlerts = False
    excel.Visible = True
    
    wb = excel.Workbooks.Add()
    ws = wb.ActiveSheet
    
    ws.Cells(1, 1).Value = "Timestamp"
    ws.Cells(1, 2).Value = "Text"
    ws.Range("A1:B1").Font.Bold = True
    
    wb.SaveAs(filename)
    print("Excel ready!\n")
    
    row = 2
    
    while True:
        ws.Cells(row, 1).Value = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        ws.Cells(row, 2).Value = "abcd"
        
        if (row - 1) % 20 == 0:
            wb.Save()
            print(f"Saved at row {row-1}")
        
        row += 1
        time.sleep(0.2)
        
except KeyboardInterrupt:
    print("\n\nStopping.")
    
finally:
    wb.Save()
    excel.Quit()
    print(f"\nDone! Total rows: {row-2}")
    print(f"File: {filename}")
