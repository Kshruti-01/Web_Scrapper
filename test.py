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
