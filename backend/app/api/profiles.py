from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..services.aggregator import aggregate_step, find_context_events
from ..services.profile_manager import ProfileManager, ProfileNotFoundError

router = APIRouter(prefix="/api")


def get_manager(request: Request) -> ProfileManager:
    return request.app.state.manager


@router.get("/health")
def health(request: Request):
    manager: ProfileManager = get_manager(request)
    return {
        "status": "ok",
        "monitor": manager.monitor_status(),
        "mappingRules": len(manager.mapper.rules),
    }


@router.get("/categories")
def categories(request: Request):
    """Return the semantic category taxonomy (for UI color/legend)."""
    from ..models.taxonomy import CATEGORY_TAXONOMY

    return {"categories": CATEGORY_TAXONOMY}


@router.get("/profiles")
def list_profiles(request: Request):
    manager: ProfileManager = get_manager(request)
    return {"profiles": [p.to_summary() for p in manager.list_profiles()]}


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: str, request: Request):
    manager: ProfileManager = get_manager(request)
    rec = manager.get(profile_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    summary = rec.to_summary()
    stage_summary: dict[str, int] = {}
    if rec.trace is not None:
        for step in rec.trace.steps:
            stage_summary[step.stage] = stage_summary.get(step.stage, 0) + 1
    summary["stageSummary"] = stage_summary
    summary["compatibility"] = (
        "ok" if manager.mapper.rules else "semantic_mapping_unavailable"
    )
    return summary


@router.get("/profiles/{profile_id}/steps")
def get_steps(
    profile_id: str,
    request: Request,
    stage: Optional[str] = Query(default=None),
):
    manager: ProfileManager = get_manager(request)
    rec = manager.get(profile_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    try:
        trace = manager.ensure_loaded(rec)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    steps = trace.steps
    if stage:
        stage = stage.upper()
        steps = [s for s in steps if s.stage == stage]
    return {"steps": [s.to_dict() for s in steps]}


@router.get("/profiles/{profile_id}/steps/{step_id}")
def get_step_detail(
    profile_id: str,
    step_id: str,
    request: Request,
    include_python: bool = Query(default=False),
):
    manager: ProfileManager = get_manager(request)
    rec = manager.get(profile_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    try:
        trace = manager.ensure_loaded(rec)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    step = trace.step(step_id)
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found")

    events = [trace.events[i] for i in step.event_ids]
    if not include_python:
        events = [e for e in events if e.category != "python_function"]
    events.sort(key=lambda e: e.timestamp_us)
    total = len(events)
    capped = events[: manager.settings.max_events_per_response]

    all_events = [trace.events[i] for i in step.event_ids]
    metrics = aggregate_step(step, all_events)
    context = find_context_events(trace, step, limit=10)

    return {
        "step": step.to_dict(),
        "metrics": metrics,
        "contextEvents": [e.to_compact(step.start_us) for e in context],
        "events": [e.to_compact(step.start_us) for e in capped],
        "totalEventCount": total,
        "truncated": total > len(capped),
    }


@router.get("/profiles/{profile_id}/events/{event_id}")
def get_event_detail(profile_id: str, event_id: str, request: Request):
    manager: ProfileManager = get_manager(request)
    rec = manager.get(profile_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    try:
        trace = manager.ensure_loaded(rec)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    try:
        eid = int(event_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid event id")
    ev = trace.event(eid)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")

    source = manager.source_mapper.for_rule_id(ev.rule_id)
    step = trace.step(ev.step_id) if ev.step_id else None
    flows = trace.flow_events_for(ev, limit=20)

    return {
        "id": str(eid),
        "raw": ev.to_raw(),
        "normalized": ev.to_dict(),
        "semantic": {
            "category": ev.semantic_category,
            "name": ev.semantic_name,
            "confidence": ev.confidence,
            "framework": ev.framework,
            "ruleId": ev.rule_id,
        },
        "source": source,
        "step": step.to_dict() if step else None,
        "flows": [f.to_compact() for f in flows],
    }
