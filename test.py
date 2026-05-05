import xlwings as xw
import time
from datetime import datetime
from pathlib import Path
import signal
import sys

def signal_handler(sig, frame):
    print("\nForced stop requested. Closing...")
    try:
        wb.save()
        app.quit()
    except:
        pass
    sys.exit(0)

# Register signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

try:
    # Get Documents folder
    documents_path = Path.home() / "Documents"
    documents_path.mkdir(parents=True, exist_ok=True)
    filename = documents_path / f"excel_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filename = str(filename)
    
    print(f"Will save to: {filename}")
    print("Starting Excel (this may take 5-10 seconds)...")
    
    # Create Excel app with minimal visibility
    app = xw.App(visible=True, add_book=False)  # Don't add default workbook
    app.display_alerts = False
    app.screen_updating = False
    
    # Add workbook explicitly
    wb = app.books.add()
    ws = wb.sheets[0]
    
    ws.range("A1").value = "Timestamp"
    ws.range("B1").value = "Text"
    row = 2
    
    print("Saving initial file...")
    wb.save(filename)
    print("Ready! Writing data... Press Ctrl+C to stop")
    
    while True:
        try:
            ws.range(f"A{row}").value = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            ws.range(f"B{row}").value = "abcd"
            print(f"Row {row} written", end="\r")  # Print on same line
            row += 1

            if row % 20 == 0:
                wb.save()
                print(f"\n✓ Saved at row {row-1}")

            time.sleep(0.2)
            
        except Exception as e:
            print(f"\nError writing row {row}: {e}")
            break

except KeyboardInterrupt:
    print("\n\nStopping...")
    
except Exception as e:
    print(f"\nError: {e}")
    
finally:
    try:
        print("Saving final data...")
        wb.save()
        print("Closing Excel...")
        app.quit()
        print("Done!")
    except:
        pass
