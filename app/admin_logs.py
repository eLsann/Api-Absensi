from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin_auth import get_current_admin
from app.database import get_db
from app.models import AttendanceEvent, DailyAttendance

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/events")
def list_events(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    name: str | None = Query(default=None),
    day: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
):


    q = db.query(AttendanceEvent)
    if status:
        q = q.filter(AttendanceEvent.status == status)
    if name:
        q = q.filter(AttendanceEvent.final_name == name)
    if day:
        q = q.filter(AttendanceEvent.day == day)
    if device_id:
        q = q.filter(AttendanceEvent.device_id == device_id)

    rows = q.order_by(AttendanceEvent.ts.desc()).offset(offset).limit(limit).all()

    return [
        {
            "id": r.id,
            "day": r.day,
            "ts": r.ts.isoformat(),
            "device_id": r.device_id,
            "predicted_name": r.predicted_name,
            "final_name": r.final_name,
            "event_type": r.event_type,
            "is_late": r.is_late,
            "status": r.status,
            "distance": r.distance,
            "snapshot_path": r.snapshot_path,
            "edited_by": r.edited_by,
            "edited_at": r.edited_at.isoformat() if r.edited_at else None,
            "edit_note": r.edit_note,
        }
        for r in rows
    ]

@router.get("/daily")
def list_daily(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
    day: str | None = Query(default=None),
    month: str | None = Query(default=None, description="YYYY-MM"),
    name: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
):


    q = db.query(DailyAttendance)
    if day:
        q = q.filter(DailyAttendance.day == day)
    if month:
        q = q.filter(DailyAttendance.day.startswith(month))
    if name:
        q = q.filter(DailyAttendance.person_name == name)

    rows = q.order_by(DailyAttendance.day.desc(), DailyAttendance.person_name.asc()).offset(offset).limit(limit).all()

    return [
        {
            "id": r.id,
            "day": r.day,
            "person_name": r.person_name,
            "in_time": r.in_time.isoformat() if r.in_time else None,
            "in_is_late": r.in_is_late,
            "out_time": r.out_time.isoformat() if r.out_time else None,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]
