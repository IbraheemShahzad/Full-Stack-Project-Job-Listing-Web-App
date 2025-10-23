from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.exc import IntegrityError

from db import SessionLocal
from models.job import Job

bp = Blueprint("jobs", __name__)

ALLOWED_SORTS = {"date_desc", "date_asc", "title_asc", "company_asc"}

def _to_dict(j: Job) -> Dict[str, Any]:
    return {
        "id": j.id,
        "title": j.title,
        "company": j.company,
        "city": j.city or "",
        "country": j.country or "",
        "location": j.location or "",
        "posting_date": j.posting_date.isoformat() if j.posting_date else None,
        "job_type": j.job_type or "",
        "tags": j.tags or [],
        "job_url": j.job_url,
    }

def _bad_request(message: str, details: Optional[Dict[str, Any]] = None):
    payload: Dict[str, Any] = {"error": "validation_error", "message": message}
    if details:
        payload["details"] = details
    return jsonify(payload), 400

def _parse_iso_date(value: Any, field: str) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"{field} must be YYYY-MM-DD")
    raise ValueError(f"{field} must be YYYY-MM-DD")

def _normalize_tags(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(t).strip() for t in value if str(t).strip()]
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    return []

@bp.get("/health")
def health():
    """
    Health Check
    ---
    tags: [Meta]
    responses:
      200:
        description: API and DB health
        schema:
          type: object
          properties:
            ok: { type: boolean }
            db_rows: { type: integer }
    """
    with SessionLocal() as s:
        total = s.scalar(select(func.count()).select_from(Job))
    return jsonify({"ok": True, "db_rows": int(total or 0)})

@bp.get("/jobs")
def list_jobs():
    """
    List Jobs
    ---
    tags: [Jobs]
    parameters:
      - name: q
        in: query
        type: string
        required: false
        description: Keyword in title or company
      - name: job_type
        in: query
        type: string
      - name: city
        in: query
        type: string
      - name: country
        in: query
        type: string
      - name: location
        in: query
        type: string
      - name: tag
        in: query
        type: array
        collectionFormat: multi
        items: { type: string }
        description: Repeat ?tag=Life&tag=Pricing
      - name: tag_mode
        in: query
        type: string
        enum: [any, all]
        default: any
        description: Match any tag (default) or require all tags
      - name: sort
        in: query
        type: string
        enum: [date_desc, date_asc, title_asc, company_asc]
        default: date_desc
      - name: page
        in: query
        type: integer
        default: 1
      - name: page_size
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Paginated jobs
        schema:
          type: object
          properties:
            page: { type: integer }
            page_size: { type: integer }
            total: { type: integer }
            items:
              type: array
              items:
                $ref: '#/definitions/Job'
    definitions:
      Job:
        type: object
        properties:
          id: { type: integer }
          title: { type: string }
          company: { type: string }
          city: { type: string }
          country: { type: string }
          location: { type: string }
          posting_date: { type: string, format: date }
          job_type: { type: string }
          tags:
            type: array
            items: { type: string }
          job_url: { type: string }
    """
    q = request.args.get("q", type=str)
    job_type = request.args.get("job_type", type=str)
    city = request.args.get("city", type=str)
    country = request.args.get("country", type=str)
    location = request.args.get("location", type=str)
    tags = request.args.getlist("tag")
    tag_mode = (request.args.get("tag_mode", "any") or "any").lower()
    sort = request.args.get("sort", default="date_desc", type=str)
    page = max(request.args.get("page", default=1, type=int), 1)
    page_size = min(max(request.args.get("page_size", default=20, type=int), 1), 100)

    if sort not in ALLOWED_SORTS:
        return _bad_request(f"Unsupported sort '{sort}'. Allowed: {', '.join(sorted(ALLOWED_SORTS))}")

    with SessionLocal() as s:
        stmt = select(Job)

        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(or_(Job.title.ilike(like), Job.company.ilike(like)))
        if job_type:
            stmt = stmt.where(Job.job_type.ilike(job_type.strip()))
        if city:
            stmt = stmt.where(Job.city.ilike(city.strip()))
        if country:
            stmt = stmt.where(Job.country.ilike(country.strip()))
        if location:
            stmt = stmt.where(Job.location.ilike(location.strip()))

        if tags:
            if tag_mode == "all":
                # require ALL tags (jsonb @> operator)
                stmt = stmt.where(Job.tags.contains(tags))
            else:
                # default: ANY overlap
                stmt = stmt.where(func.jsonb_exists_any(Job.tags, tags))

        if sort == "date_asc":
            stmt = stmt.order_by(asc(Job.posting_date), asc(Job.id))
        elif sort == "title_asc":
            stmt = stmt.order_by(asc(Job.title), asc(Job.id))
        elif sort == "company_asc":
            stmt = stmt.order_by(asc(Job.company), asc(Job.id))
        else:
            stmt = stmt.order_by(desc(Job.posting_date), desc(Job.id))

        total = s.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = s.scalars(stmt).all()

    return jsonify({
        "page": page,
        "page_size": page_size,
        "total": int(total or 0),
        "items": [_to_dict(r) for r in rows],
    })

@bp.get("/jobs/<int:job_id>")
def get_job(job_id: int):
    """
    Get Job by ID
    ---
    tags: [Jobs]
    parameters:
      - name: job_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Job
        schema:
          $ref: '#/definitions/Job'
      404:
        description: Not Found
    """
    with SessionLocal() as s:
        j = s.get(Job, job_id)
        if not j:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_to_dict(j))

@bp.post("/jobs")
def create_job():
    """
    Create Job
    ---
    tags: [Jobs]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [title, company, posting_date, job_url]
          properties:
            title: { type: string }
            company: { type: string }
            city: { type: string }
            country: { type: string }
            location: { type: string }
            posting_date: { type: string, format: date }
            job_type: { type: string, default: Full-time }
            tags:
              type: array
              items: { type: string }
            job_url: { type: string }
    responses:
      201:
        description: Created
        schema:
          $ref: '#/definitions/Job'
      400:
        description: Validation error
      409:
        description: Conflict (duplicate job_url)
    """
    data = request.get_json(force=True) or {}

    # basic required fields
    missing = [f for f in ["title", "company", "job_url", "posting_date"] if not str(data.get(f, "")).strip()]
    if missing:
        return _bad_request("Missing required fields", {"missing": missing})

    # coerce/validate date & tags
    try:
        data["posting_date"] = _parse_iso_date(data.get("posting_date"), "posting_date")
    except ValueError as e:
        return _bad_request(str(e))

    data["tags"] = _normalize_tags(data.get("tags"))

    # defaults
    data.setdefault("job_type", "Full-time")
    data.setdefault("city", "")
    data.setdefault("country", "")
    data.setdefault("location", f"{data.get('city','')}, {data.get('country','')}".strip(", "))

    j = Job(**data)
    with SessionLocal() as s:
        s.add(j)
        try:
            s.commit()
        except IntegrityError:
            s.rollback()
            return jsonify({"error": "conflict", "message": "job_url must be unique"}), 409
        s.refresh(j)
        return jsonify(_to_dict(j)), 201

@bp.put("/jobs/<int:job_id>")
@bp.patch("/jobs/<int:job_id>")
def update_job(job_id: int):
    """
    Update Job
    ---
    tags: [Jobs]
    parameters:
      - name: job_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            title: { type: string }
            company: { type: string }
            city: { type: string }
            country: { type: string }
            location: { type: string }
            posting_date: { type: string, format: date }
            job_type: { type: string }
            tags:
              type: array
              items: { type: string }
            job_url: { type: string }
    responses:
      200:
        description: Updated
        schema:
          $ref: '#/definitions/Job'
      404:
        description: Not Found
      409:
        description: Conflict (duplicate job_url)
    """
    patch = request.get_json(force=True) or {}

    # coerce inputs
    if "posting_date" in patch:
        try:
            patch["posting_date"] = _parse_iso_date(patch["posting_date"], "posting_date")
        except ValueError as e:
            return _bad_request(str(e))
    if "tags" in patch:
        patch["tags"] = _normalize_tags(patch["tags"])

    with SessionLocal() as s:
        j = s.get(Job, job_id)
        if not j:
            return jsonify({"error": "not_found"}), 404

        for k, v in patch.items():
            setattr(j, k, v)

        try:
            s.commit()
        except IntegrityError:
            s.rollback()
            return jsonify({"error": "conflict", "message": "job_url must be unique"}), 409

        s.refresh(j)
        return jsonify(_to_dict(j))

@bp.delete("/jobs/<int:job_id>")
def delete_job(job_id: int):
    """
    Delete Job
    ---
    tags: [Jobs]
    parameters:
      - name: job_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Deleted
      404:
        description: Not Found
    """
    with SessionLocal() as s:
        j = s.get(Job, job_id)
        if not j:
            return jsonify({"error": "not_found"}), 404
        s.delete(j)
        s.commit()
        return jsonify({"ok": True})
