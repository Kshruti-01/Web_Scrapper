import xlwings as xw
import time
from datetime import datetime
 
filename = fr"C:UsersYOURNAMEDocumentsexcel_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
 
app = xw.App(visible=True)
wb = app.books.add()
ws = wb.sheets[0]
 
ws.range("A1").value = "Text"
row = 2 
wb.save(filename)
 
try:
    while True:
        ws.range(f"A{row}").value = "abcd"
        row += 1
 
        if row % 20 == 0:
            wb.save()
 
        time.sleep(0.2)
 
except KeyboardInterrupt:
    wb.save()
    print("Stopped and saved.")
