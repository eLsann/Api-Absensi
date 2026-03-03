import os

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
import numpy as np
from sqlalchemy.orm import Session

from app.admin_auth import get_current_admin  # JWT dependency
from app.database import get_db
from app.models import Embedding, Person
from app.recog import detect_faces_from_bgr, embed_face, rebuild_cache

router = APIRouter(prefix="/admin", tags=["admin"])

# ── Module-level constants ──────────────────────────────────────────
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
_MAX_FILE_SIZE = 10 * 1024 * 1024   # 10 MB
_ENROLL_MAX_IMAGE_PX = 1000         # resize jika dimensi image > ini


def _vec_to_csv(v: np.ndarray) -> str:
    return ",".join(f"{x:.6f}" for x in v.tolist())


@router.get("/persons")
def list_persons(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    persons = db.query(Person).order_by(Person.name.asc()).all()
    return [{"id": p.id, "name": p.name} for p in persons]


@router.post("/persons")
def create_person(
    payload: dict,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    exists = db.query(Person).filter(Person.name == name).one_or_none()
    if exists:
        return {"id": exists.id, "name": exists.name, "created": False}

    p = Person(name=name)
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name, "created": True}


def augment_image(bgr: np.ndarray) -> list:
    """Generate augmented versions of an image for stronger embeddings"""
    augmented = [bgr]  # Original

    # 1. Horizontal flip
    flipped = cv2.flip(bgr, 1)
    augmented.append(flipped)

    # 2. Brightness variations (+20%, -20%)
    bright = cv2.convertScaleAbs(bgr, alpha=1.2, beta=10)
    dark = cv2.convertScaleAbs(bgr, alpha=0.8, beta=-10)
    augmented.append(bright)
    augmented.append(dark)

    # 3. Slight rotation (+5°, -5°)
    h, w = bgr.shape[:2]
    center = (w // 2, h // 2)
    for angle in [5, -5]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        augmented.append(rotated)

    return augmented  # Returns 6 images total


@router.post("/persons/{person_id}/enroll")
async def enroll_person(
    person_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    person = db.query(Person).filter(Person.id == person_id).one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")

    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")

    added = 0
    skipped = 0
    augmented_count = 0

    for f in files:
        if f.filename:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in _ALLOWED_EXTENSIONS:
                skipped += 1
                continue

        img_bytes = await f.read()

        if not img_bytes or len(img_bytes) > _MAX_FILE_SIZE:
            skipped += 1
            continue

        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            skipped += 1
            continue

        h, w = bgr.shape[:2]
        if max(h, w) > _ENROLL_MAX_IMAGE_PX:
            scale = _ENROLL_MAX_IMAGE_PX / max(h, w)
            bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)))

        # FIXED: Detect face FIRST, then augment and embed the face crop
        # This matches the recognition flow for consistent embeddings
        faces = detect_faces_from_bgr(bgr, max_faces=1)

        if not faces:
            # No face detected in this image
            skipped += 1
            continue

        # Get the face crop (already aligned by detect_faces_from_bgr)
        face_crop = faces[0]["crop"]

        # Generate augmented versions of the FACE CROP (not full image)
        aug_faces = augment_image(face_crop)

        for aug_face in aug_faces:
            try:
                emb = embed_face(aug_face)
                db.add(Embedding(person_id=person.id, vec_csv=_vec_to_csv(emb)))
                augmented_count += 1
            except Exception:
                continue

        added += 1

    db.commit()
    rebuild_cache(db)

    return {
        "ok": True,
        "person_id": person.id,
        "name": person.name,
        "images_processed": added,
        "embeddings_added": augmented_count,
        "skipped": skipped,
    }



@router.delete("/persons/{person_id}")
def delete_person(
    person_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    person = db.query(Person).filter(Person.id == person_id).one_or_none()
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")

    db.query(Embedding).filter(Embedding.person_id == person_id).delete()
    db.delete(person)
    db.commit()

    rebuild_cache(db)
    return {"ok": True, "deleted_person_id": person_id}

@router.post("/rebuild_cache")
def rebuild_cache_endpoint(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    rebuild_cache(db)
    return {"ok": True}
