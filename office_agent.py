"""Windows Office COM adapter. Operates on owned documents, never global input."""
from contextlib import contextmanager
from decimal import Decimal
import sys
from runtime import artifact
from scenario import report_text


def normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


@contextmanager
def office_session(prog_id, collection_name, control):
    if sys.platform != "win32":
        raise RuntimeError("Live Office automation requires Windows and installed Word/Excel")
    import pythoncom
    from win32com.client import DispatchEx
    pythoncom.CoInitialize()
    app = None
    owned = []
    cleanup_errors = []
    preserved = False
    previous_settings = {}
    try:
        control.check()
        app = DispatchEx(prog_id)
        app.Visible = True
        for name in ("DisplayAlerts", "AutomationSecurity"):
            previous_settings[name] = getattr(app, name)
        app.DisplayAlerts = 0
        app.AutomationSecurity = 3  # Force-disable macros in programmatically opened files.
        control.audit.emit("office_session_opened", backend="office_com", application=prog_id)
        yield app, owned
    finally:
        # Cancellation never prevents cleanup. Never close arbitrary collection members.
        for document in reversed(owned):
            try:
                document.Close(SaveChanges=False)
            except Exception as error:
                cleanup_errors.append(type(error).__name__)
        if app is not None:
            for name, value in previous_settings.items():
                try:
                    setattr(app, name, value)
                except Exception as error:
                    cleanup_errors.append(type(error).__name__)
            try:
                if getattr(app, collection_name).Count == 0:
                    app.Quit()
                else:
                    preserved = True  # Someone may have opened another document in this instance.
            except Exception as error:
                cleanup_errors.append(type(error).__name__)
        app = None
        pythoncom.CoUninitialize()
        control.audit.emit("office_cleanup", backend="office_com", application=prog_id,
                           errors=cleanup_errors, instance_preserved=preserved)
        if cleanup_errors and sys.exc_info()[0] is None:
            raise RuntimeError("Office cleanup failed: " + ", ".join(cleanup_errors))


def observe_office_process(app, application, control):
    """Record the observed window's PID; never assume a launcher or parent PID."""
    import win32process
    hwnd = app.Hwnd if application == "Excel" else app.ActiveWindow.Hwnd
    _, pid = win32process.GetWindowThreadProcessId(int(hwnd))
    control.audit.emit("office_process_observed", backend="office_com",
                       application=application, observed_pid=pid, window_handle=int(hwnd))


def close_owned(document, owned):
    document.Close(SaveChanges=False)
    owned.remove(document)


def create_budget(data, workspace, control):
    path = (workspace / "budget.xlsx").resolve()
    if path.exists():
        raise FileExistsError(path)
    with office_session("Excel.Application", "Workbooks", control) as (app, owned):
        workbook = app.Workbooks.Add()
        owned.append(workbook)
        observe_office_process(app, "Excel", control)
        sheet = workbook.Worksheets(1)
        sheet.Name = "Budget"
        headers = ("Item", "Quantity", "Unit price", "Line total")
        for column, value in enumerate(headers, 1):
            sheet.Cells(1, column).Value = value
        for row, item in enumerate(data["items"], 2):
            control.check()
            sheet.Cells(row, 1).NumberFormat = "@"
            sheet.Cells(row, 1).Value = item["name"]
            sheet.Cells(row, 2).Value = item["quantity"]
            sheet.Cells(row, 3).Value = float(item["unit_price"])
            sheet.Cells(row, 4).Formula = f"=B{row}*C{row}"
            control.pause()
        total_row = len(data["items"]) + 2
        sheet.Cells(total_row, 1).Value = "Total " + data["currency"]
        formula = f"=SUM(D2:D{total_row - 1})"
        sheet.Cells(total_row, 4).Formula = formula
        sheet.Range(f"C2:D{total_row}").NumberFormat = "0.00"
        sheet.Range("A1:D1").Font.Bold = True
        sheet.Columns("A:D").AutoFit()
        app.Calculate()
        control.check()
        workbook.SaveAs(Filename=str(path), FileFormat=51)  # .xlsx
        close_owned(workbook, owned)
        control.check()
        reopened = app.Workbooks.Open(Filename=str(path), UpdateLinks=0, ReadOnly=True)
        owned.append(reopened)
        saved = reopened.Worksheets("Budget")
        for row, item in enumerate(data["items"], 2):
            control.check()
            if (saved.Cells(row, 1).Value != item["name"]
                    or saved.Cells(row, 2).Value != item["quantity"]
                    or Decimal(str(saved.Cells(row, 3).Value)).quantize(Decimal(".01")) != Decimal(item["unit_price"])
                    or Decimal(str(saved.Cells(row, 4).Value)).quantize(Decimal(".01")) != Decimal(item["line_total"])
                    or saved.Cells(row, 4).Formula != f"=B{row}*C{row}"):
                raise RuntimeError(f"Saved budget row {row} did not match")
        observed = Decimal(str(saved.Cells(total_row, 4).Value)).quantize(Decimal(".01"))
        if observed != Decimal(data["total"]) or saved.Cells(total_row, 4).Formula != formula:
            raise RuntimeError("Saved budget total/formula did not match")
        result = artifact(path)
        result["total"] = format(observed, ".2f")
        control.audit.emit("artifact_verified", backend="office_com", kind="budget", **result)
    control.check()
    return result


def create_report(data, budget, workspace, control):
    if budget["total"] != data["total"]:
        raise RuntimeError("Report requires the verified budget total")
    path = (workspace / "report.docx").resolve()
    if path.exists():
        raise FileExistsError(path)
    text = report_text(data, control.audit.run_id)
    with office_session("Word.Application", "Documents", control) as (app, owned):
        document = app.Documents.Add()
        owned.append(document)
        observe_office_process(app, "Word", control)
        for line in text.splitlines():
            control.check()
            document.Content.InsertAfter(line + "\r")
            control.pause()
        control.check()
        document.SaveAs2(FileName=str(path), FileFormat=12, AddToRecentFiles=False)
        close_owned(document, owned)
        control.check()
        reopened = app.Documents.Open(FileName=str(path), ReadOnly=True, AddToRecentFiles=False)
        owned.append(reopened)
        if normalized(reopened.Content.Text) != normalized(text):
            raise RuntimeError("Saved report content did not match")
        result = artifact(path)
        control.audit.emit("artifact_verified", backend="office_com", kind="report", **result)
    control.check()
    return result
