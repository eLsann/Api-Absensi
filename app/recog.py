import cv2
from facenet_pytorch import MTCNN, InceptionResnetV1
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session
import torch

from app.config import settings
from app.logging_config import get_logger
from app.models import Person

logger = get_logger(__name__)

_DEVICE = "cpu"
_MODEL = InceptionResnetV1(pretrained="vggface2").eval().to(_DEVICE)
logger.info(f"Face recognition model loaded on device: {_DEVICE}")

# MTCNN detector with landmark detection for alignment
# MTCNN detection thresholds: [P-Net, R-Net, O-Net]
# Ekstrak ke konstanta agar konsisten (tidak duplikat di defensive reset L117)
_MTCNN_THRESHOLDS = [0.6, 0.7, 0.8]
# Minimum face detection confidence (filter post-MTCNN)
_MIN_DETECTION_PROB = 0.9

_MTCNN = MTCNN(
    image_size=160,
    margin=20,
    keep_all=True,
    device=_DEVICE,
    post_process=False,
    min_face_size=80,
    thresholds=_MTCNN_THRESHOLDS,
)
logger.info("MTCNN face detector initialized")


def _align_face(img_rgb: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
    """
    Align face using eye landmarks.
    landmarks: [left_eye_x, left_eye_y, right_eye_x, right_eye_y, nose_x, nose_y, ...]
    """
    try:
        # Extract eye positions (MTCNN returns 5 landmarks: left_eye, right_eye, nose, left_mouth, right_mouth)
        left_eye = landmarks[0]   # (x, y)
        right_eye = landmarks[1]  # (x, y)

        # Calculate angle between eyes
        dy = right_eye[1] - left_eye[1]
        dx = right_eye[0] - left_eye[0]
        angle = np.degrees(np.arctan2(dy, dx))

        # Get center point between eyes
        eye_center = ((left_eye[0] + right_eye[0]) / 2, (left_eye[1] + right_eye[1]) / 2)

        # Get rotation matrix
        h, w = img_rgb.shape[:2]
        M = cv2.getRotationMatrix2D(eye_center, angle, 1.0)

        # Apply affine transformation
        aligned = cv2.warpAffine(img_rgb, M, (w, h), flags=cv2.INTER_CUBIC)

        return aligned
    except Exception as e:
        logger.warning(f"Alignment failed, using original: {e}")
        return img_rgb

_CACHE = {"names": None, "vectors": None}

def _csv_to_vec(s: str) -> np.ndarray:
    from io import StringIO
    return np.loadtxt(StringIO(s), delimiter=',', dtype=np.float32)

def rebuild_cache(db: Session):
    logger.info("Rebuilding face recognition cache...")
    persons = db.query(Person).all()
    names, vecs = [], []
    for p in persons:
        if not p.embeddings:
            continue
        mats = [_csv_to_vec(e.vec_csv) for e in p.embeddings]
        mean = np.vstack(mats).mean(axis=0)
        names.append(p.name)
        vecs.append(mean)
    _CACHE["names"] = names
    _CACHE["vectors"] = np.vstack(vecs).astype(np.float32) if vecs else np.zeros((0, 512), dtype=np.float32)
    logger.info(f"Cache rebuilt with {len(names)} persons")

def _bytes_to_bgr(img_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("invalid_image")
    return bgr

def _preprocess(face_bgr: np.ndarray) -> torch.Tensor:
    rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb).resize((160, 160))
    x = np.asarray(pil).astype(np.float32)
    x = (x - 127.5) / 128.0
    return torch.from_numpy(x).permute(2, 0, 1).unsqueeze(0).to(_DEVICE)

@torch.inference_mode()
def embed_face(face_bgr: np.ndarray) -> np.ndarray:
    t = _preprocess(face_bgr)
    return _MODEL(t).cpu().numpy().astype(np.float32)[0]


def _detect_faces_internal(bgr: np.ndarray, max_faces: int = 5, sort_left_to_right: bool = False, include_queue_id: bool = False) -> list:
    """
    Internal helper for face detection. Used by both detect_faces and detect_faces_from_bgr.

    Args:
        bgr: BGR image array
        max_faces: Maximum number of faces to detect
        sort_left_to_right: Sort faces by x position
        include_queue_id: Include queue_id in results
    """
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # Defensive Fix: Validate thresholds to prevent IndexError
    if isinstance(_MTCNN.thresholds, list) and len(_MTCNN.thresholds) < 3:
        logger.warning(f"MTCNN thresholds corrupted (len={len(_MTCNN.thresholds)}). Resetting to defaults.")
        _MTCNN.thresholds = list(_MTCNN_THRESHOLDS)  # pakai konstanta, bukan literal duplikat

    # Use MTCNN to detect faces and landmarks
    boxes, probs, landmarks = _MTCNN.detect(rgb, landmarks=True)

    if boxes is None or len(boxes) == 0:
        return []

    valid_faces = []

    # Filter by probability and collect valid faces
    # _ menggantikan i karena index tidak dipakai di dalam loop (B007)
    for _, (box, prob, lm) in enumerate(zip(boxes, probs, landmarks, strict=False)):
        if prob < settings.detection_confidence:  # dikonfigurasi via DETECTION_CONFIDENCE env var
            continue
        valid_faces.append((box, prob, lm))

    if not valid_faces:
        return []

    # Sort by x position (left to right) if requested
    if sort_left_to_right:
        valid_faces = sorted(valid_faces, key=lambda f: f[0][0])

    # Limit to max_faces
    valid_faces = valid_faces[:max_faces]

    results = []
    h, w = bgr.shape[:2]

    for i, (box, prob, lm) in enumerate(valid_faces):
        x1, y1, x2, y2 = [int(v) for v in box]

        # Clamp to image bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        # Add padding
        pad_w = int(0.15 * (x2 - x1))
        pad_h = int(0.15 * (y2 - y1))
        x1_pad = max(0, x1 - pad_w)
        y1_pad = max(0, y1 - pad_h)
        x2_pad = min(w, x2 + pad_w)
        y2_pad = min(h, y2 + pad_h)

        # Align face using landmarks before cropping
        aligned_rgb = _align_face(rgb, lm)
        aligned_bgr = cv2.cvtColor(aligned_rgb, cv2.COLOR_RGB2BGR)

        # Crop from aligned image
        crop = aligned_bgr[y1_pad:y2_pad, x1_pad:x2_pad]

        result = {
            "crop": crop,
            "confidence": float(prob),
            "bbox": [x1, y1, x2, y2]
        }

        if include_queue_id:
            result["queue_id"] = i + 1

        results.append(result)

    return results


def detect_faces_from_bgr(bgr: np.ndarray, max_faces: int = 1) -> list:
    """
    Detect faces from BGR numpy array (for enroll process).
    Returns list of face crops with alignment applied.
    """
    return _detect_faces_internal(bgr, max_faces=max_faces, sort_left_to_right=False, include_queue_id=False)


def detect_faces(img_bytes: bytes, max_faces: int = 5) -> list:
    """Detect multiple faces using MTCNN, with alignment. Returns list sorted left-to-right."""
    bgr = _bytes_to_bgr(img_bytes)
    results = _detect_faces_internal(bgr, max_faces=max_faces, sort_left_to_right=True, include_queue_id=True)
    logger.info(f"MTCNN detected {len(results)} faces (aligned)")
    return results


def identify_single(face_crop: np.ndarray, db: Session) -> dict:
    """Identify a single face crop against the cache"""
    if _CACHE["names"] is None:
        rebuild_cache(db)

    names = _CACHE["names"] or []
    vectors = _CACHE["vectors"]

    if vectors is None or vectors.shape[0] == 0:
        return {"status": "error", "name": None, "distance": None}

    h, w = face_crop.shape[:2]
    if min(h, w) < settings.min_face_px:
        return {"status": "reject", "name": None, "distance": None}

    try:
        emb = embed_face(face_crop)
        dists = np.linalg.norm(vectors - emb[None, :], axis=1)
        best_idx = int(np.argmin(dists))
        dist = float(dists[best_idx])
        name = names[best_idx]

        if dist > settings.max_distance:
            return {"status": "unknown", "name": None, "distance": dist}

        return {"status": "ok", "name": name, "distance": dist}
    except Exception as e:
        logger.error(f"identify_single error: {e}")
        return {"status": "error", "name": None, "distance": None}


def identify_multiple(img_bytes: bytes, db: Session, max_faces: int = 5) -> dict:
    """Detect and identify multiple faces in a single image"""
    try:
        faces_data = detect_faces(img_bytes, max_faces)

        if not faces_data:
            return {
                "status": "no_face",
                "faces": [],
                "recognized_names": []
            }

        results = []
        recognized_names = []

        for face in faces_data:
            result = identify_single(face["crop"], db)

            face_result = {
                "queue_id": face["queue_id"],
                "bbox": face["bbox"],
                "status": result["status"],
                "name": result["name"],
                "distance": result["distance"]
            }
            results.append(face_result)

            if result["status"] == "ok" and result["name"]:
                recognized_names.append(result["name"])

        logger.info(f"Multi-face: {len(results)} detected, {len(recognized_names)} recognized")

        return {
            "status": "ok",
            "faces": results,
            "recognized_names": recognized_names
        }

    except Exception as e:
        logger.error(f"identify_multiple error: {e}", exc_info=True)
        return {
            "status": "error",
            "faces": [],
            "recognized_names": [],
            "error": str(e)
        }
