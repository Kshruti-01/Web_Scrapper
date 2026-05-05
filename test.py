import xlwings as xw
import time
from datetime import datetime
import os
from pathlib import Path

# Get user's Documents folder automatically
documents_path = Path.home() / "Documents"
filename = documents_path / f"excel_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
filename = str(filename)

# Create Excel app
app = xw.App(visible=True)

# Set properties IMMEDIATELY after creating app (before adding workbook)
app.display_alerts = False
app.screen_updating = False

# Now add workbook - popup should be suppressed
wb = app.books.add()
ws = wb.sheets[0]

ws.range("A1").value = "Timestamp"
ws.range("B1").value = "Text"
row = 2 

# Save - popup should also be suppressed here
wb.save(filename)

try:
    while True:
        ws.range(f"A{row}").value = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        ws.range(f"B{row}").value = "abcd"
        row += 1

        if row % 20 == 0:
            wb.save()
            print(f"Saved at row {row-1}")

        time.sleep(0.2)

except KeyboardInterrupt:
    wb.save()
    print(f"\nStopped and saved. Total rows written: {row-1}")
    app.quit()



PS C:\Users\850085869\OneDrive - Genpact\Desktop\Project\testing> pip install xlwings
Defaulting to user installation because normal site-packages is not writeable
Collecting xlwings
  Downloading xlwings-0.35.2-cp312-cp312-win_amd64.whl.metadata (6.4 kB)
Collecting pywin32>=224 (from xlwings)
  Using cached pywin32-311-cp312-cp312-win_amd64.whl.metadata (10 kB)
Downloading xlwings-0.35.2-cp312-cp312-win_amd64.whl (1.6 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.6/1.6 MB 1.8 MB/s eta 0:00:00
Using cached pywin32-311-cp312-cp312-win_amd64.whl (9.5 MB)
Installing collected packages: pywin32, xlwings
  WARNING: The scripts pywin32_postinstall.exe and pywin32_testall.exe are installed in 'C:\Users\850085869\AppData\Roaming\Python\Python312\Scripts' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script xlwings.exe is installed in 'C:\Users\850085869\AppData\Roaming\Python\Python312\Scripts' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed pywin32-311 xlwings-0.35.2
