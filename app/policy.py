from dataclasses import dataclass
import time

from sqlalchemy.orm import Session

from app.models import AttendancePolicy


@dataclass
class PolicyData:
    """Simple data class to hold policy values (avoids SQLAlchemy DetachedInstanceError)"""
    timezone: str = "Asia/Jakarta"
    in_start_time: str = "05:00"
    late_after_time: str = "08:00"
    out_start_time: str = "15:00"
    out_end_time: str = "17:00"  # NEW: OUT window end
    retention_days: int = 60

_CACHE = {"policy": None, "built_at": 0.0}
_TTL = 5.0

def get_policy(db: Session) -> PolicyData:
    now = time.time()
    if _CACHE["policy"] is not None and (now - _CACHE["built_at"]) < _TTL:
        return _CACHE["policy"]

    policy_row = db.query(AttendancePolicy).filter(AttendancePolicy.id == 1).one_or_none()
    if policy_row is None:
        policy_row = AttendancePolicy(id=1)
        db.add(policy_row)
        db.commit()
        db.refresh(policy_row)

    # Cache plain data values, not the SQLAlchemy object
    policy_data = PolicyData(
        timezone=policy_row.timezone,
        in_start_time=policy_row.in_start_time,
        late_after_time=policy_row.late_after_time,
        out_start_time=policy_row.out_start_time,
        out_end_time=getattr(policy_row, 'out_end_time', '17:00'),  # Handle old DB without column
        retention_days=policy_row.retention_days,
    )

    _CACHE["policy"] = policy_data
    _CACHE["built_at"] = now
    return policy_data

def invalidate_policy_cache():
    _CACHE["policy"] = None
    _CACHE["built_at"] = 0.0
