from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.admin_auth import get_current_admin
from app.database import get_db
from app.models import AttendanceEvent, DailyAttendance

router = APIRouter(prefix="/admin", tags=["admin"])

def _get_or_create_daily(db: Session, day: str, name: str) -> DailyAttendance:
    d = (
        db.query(DailyAttendance)
        .filter(DailyAttendance.day == day, DailyAttendance.person_name == name)
        .one_or_none()
    )
    if d is None:
        d = DailyAttendance(day=day, person_name=name)
        db.add(d)
        db.commit()
        db.refresh(d)
    return d

@router.patch("/events/{event_id}")
def correct_event(
    event_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):


    new_name = (payload.get("final_name") or "").strip()
    edit_note = payload.get("edit_note")

    if not new_name:
        raise HTTPException(status_code=400, detail="final_name is required")

    ev = db.query(AttendanceEvent).filter(AttendanceEvent.id == event_id).one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="event not found")

    if ev.status not in ("ok", "duplicate", "reject_out_too_early", "cooldown"):
        raise HTTPException(status_code=400, detail="event cannot be corrected in this status")

    if not ev.day:
        raise HTTPException(status_code=400, detail="event missing day (DB migration issue)")
    if ev.event_type not in ("IN", "OUT"):
        raise HTTPException(status_code=400, detail="only IN/OUT events can be corrected")

    old_name = ev.final_name
    if old_name == new_name:
        return {"ok": True, "event_id": ev.id, "message": "no change"}

    day = ev.day
    ts = ev.ts
    event_type = ev.event_type

    # audit
    ev.edited_by = admin.username
    ev.edited_at = datetime.now(timezone.utc).replace(tzinfo=None)
    ev.edit_note = edit_note

    # update event final_name
    ev.final_name = new_name
    db.add(ev)

    old_daily = _get_or_create_daily(db, day, old_name) if old_name else None
    new_daily = _get_or_create_daily(db, day, new_name)

    # clear old slot if it matches this event timestamp
    if old_daily:
        if event_type == "IN" and old_daily.in_time == ts:
            old_daily.in_time = None
            old_daily.in_is_late = False
        if event_type == "OUT" and old_daily.out_time == ts:
            old_daily.out_time = None
        old_daily.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(old_daily)

    # apply to new slot: earliest IN, latest OUT
    if event_type == "IN":
        if new_daily.in_time is None or ts < new_daily.in_time:
            new_daily.in_time = ts
            new_daily.in_is_late = bool(ev.is_late)
    else:  # OUT
        if new_daily.out_time is None or ts > new_daily.out_time:
            new_daily.out_time = ts

    new_daily.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(new_daily)

    db.commit()

    return {
        "ok": True,
        "event_id": ev.id,
        "day": day,
        "event_type": event_type,
        "old_final_name": old_name,
        "new_final_name": new_name,
        "edited_by": ev.edited_by,
        "edited_at": ev.edited_at.isoformat() if ev.edited_at else None,
    }
