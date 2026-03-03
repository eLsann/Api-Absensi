import csv
from datetime import timedelta
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.admin_auth import get_current_admin
from app.database import get_db
from app.models import AttendanceEvent, DailyAttendance

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/reports/monthly")
def report_monthly(
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Get monthly attendance summary"""
    rows = db.query(DailyAttendance).filter(DailyAttendance.day.startswith(month)).all()

    summary: dict[str, dict] = {}
    for r in rows:
        s = summary.setdefault(
            r.person_name,
            {"person_name": r.person_name, "days_present": 0, "late_count": 0, "missing_out": 0},
        )
        if r.in_time is not None:
            s["days_present"] += 1
            if r.in_is_late:
                s["late_count"] += 1
        if r.in_time is not None and r.out_time is None:
            s["missing_out"] += 1

    return {"month": month, "total_records": len(rows), "summary": [summary[k] for k in sorted(summary.keys())]}


@router.get("/reports/export/csv")
def export_csv(
    month: str = Query(None, description="Optional: YYYY-MM filter"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Export attendance data as CSV file"""

    # Query daily attendance records
    query = db.query(DailyAttendance)
    if month:
        query = query.filter(DailyAttendance.day.startswith(month))

    rows = query.order_by(DailyAttendance.day.desc(), DailyAttendance.person_name).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Tanggal",
        "Nama",
        "Jam Masuk (WIB)",
        "Jam Pulang (WIB)",
        "Status Terlambat"
    ])

    # Data rows
    for r in rows:
        # Convert UTC to WIB (UTC+7)
        in_time_str = ""
        out_time_str = ""

        if r.in_time:
            in_wib = r.in_time + timedelta(hours=7)
            in_time_str = in_wib.strftime("%H:%M:%S")

        if r.out_time:
            out_wib = r.out_time + timedelta(hours=7)
            out_time_str = out_wib.strftime("%H:%M:%S")

        writer.writerow([
            r.day,
            r.person_name,
            in_time_str,
            out_time_str,
            "Terlambat" if r.in_is_late else "Tepat Waktu"
        ])

    # Prepare response
    output.seek(0)
    filename = f"absensi_{month or 'all'}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/reports/export/events/csv")
def export_events_csv(
    day: str = Query(None, description="Optional: YYYY-MM-DD filter"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Export all attendance events as CSV"""

    query = db.query(AttendanceEvent).filter(AttendanceEvent.status == "ok")
    if day:
        query = query.filter(AttendanceEvent.day == day)

    rows = query.order_by(AttendanceEvent.ts.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID",
        "Tanggal",
        "Jam (WIB)",
        "Device",
        "Nama",
        "Tipe",
        "Status",
        "Terlambat"
    ])

    for r in rows:
        ts_str = ""
        if r.ts:
            ts_wib = r.ts + timedelta(hours=7)
            ts_str = ts_wib.strftime("%H:%M:%S")

        writer.writerow([
            r.id,
            r.day,
            ts_str,
            r.device_id,
            r.final_name or r.predicted_name or "-",
            r.event_type or "-",
            r.status,
            "Ya" if r.is_late else "Tidak"
        ])

    output.seek(0)
    filename = f"events_{day or 'all'}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
