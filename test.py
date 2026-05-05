import time
from datetime import datetime
from pathlib import Path
import subprocess
import sys

# Kill any stuck Excel processes before starting
print("Cleaning up previous Excel processes...")
subprocess.run(['taskkill', '/f', '/im', 'excel.exe'], capture_output=True)
time.sleep(2)

# Create file path in Documents folder
documents_path = Path.home() / "Documents"
documents_path.mkdir(parents=True, exist_ok=True)
filename = documents_path / f"excel_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
filename = str(filename)

print(f"File will be saved to: {filename}")
print("Starting Excel")
print("Press Ctrl+C to stop logging\n")

try:
    import win32com.client as win32
    
    # Create Excel instance with all alerts disabled from the start
    excel = win32.Dispatch("Excel.Application")
    excel.DisplayAlerts = False
    excel.AskToUpdateLinks = False
    excel.Visible = True
    
    # Add new workbook
    wb = excel.Workbooks.Add()
    ws = wb.ActiveSheet
    
    # Set headers
    ws.Cells(1, 1).Value = "Timestamp"  # Column A
    ws.Cells(1, 2).Value = "Text"       # Column B
    
    # Format headers as bold
    ws.Range("A1:B1").Font.Bold = True
    
    # Save the file
    wb.SaveAs(filename)
    print("Excel file created successfully!")
    print("Writing data...\n")
    
    row = 2  # Start from row 2
    
    while True:
        try:
            # Write timestamp in column A
            current_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            ws.Cells(row, 1).Value = current_time
            
            # Write "abcd" in column B
            ws.Cells(row, 2).Value = "abcd"
            
            # Save every 20 rows
            if (row - 1) % 20 == 0:
                wb.Save()
                print(f"Saved at row {row-1} (Total: {row-1} rows)")
            
            row += 1
            time.sleep(0.2)
            
        except Exception as e:
            print(f"Error at row {row}: {e}")
            break
            
except KeyboardInterrupt:
    print("\n\n Stopping")
    
except Exception as e:
    print(f"\nError: {e}")
    
finally:
    try:
        # Save final data
        if 'wb' in locals():
            wb.Save()
            print(f"\n Final save completed!")
            print(f"Total rows written: {row-2}")
            print(f"File location: {filename}")
        
        # Close Excel
        if 'excel' in locals():
            excel.Quit()
            print("Excel closed successfully")
            
    except:
        pass
    
    print("\n Script finished!")
