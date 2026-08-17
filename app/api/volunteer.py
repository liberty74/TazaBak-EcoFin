"""Volunteer task registration and completion rewards."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserTask, VolunteerTask, utcnow
from app.schemas import (
    VolunteerCompleteRequest,
    VolunteerCompleteResponse,
    VolunteerRegisterRequest,
    VolunteerRegisterResponse,
    VolunteerTaskResponse,
)
from app.security import require_dispatcher_key
from app.services.points import credit_points
from app.services.users import find_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/volunteer", tags=["volunteer"])


@router.get("/tasks", response_model=list[VolunteerTaskResponse])
def get_volunteer_tasks(
    include_completed: bool = False,
    db: Session = Depends(get_db),
) -> list[VolunteerTask]:
    statement = select(VolunteerTask)
    if not include_completed:
        statement = statement.where(VolunteerTask.status == "open")
    return list(
        db.scalars(
            statement.order_by(VolunteerTask.date.asc(), VolunteerTask.time.asc())
        ).all()
    )


@router.post(
    "/tasks/{task_id}/register",
    response_model=VolunteerRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_for_task(
    task_id: int,
    payload: VolunteerRegisterRequest,
    db: Session = Depends(get_db),
) -> VolunteerRegisterResponse:
    user = find_user(db, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "volunteer":
        raise HTTPException(status_code=403, detail="Volunteer role required")
    task = db.get(VolunteerTask, task_id)
    if task is None or task.status != "open":
        raise HTTPException(status_code=404, detail="Open volunteer task not found")

    user_task = UserTask(
        user_id=user.id,
        task_id=task.id,
        reward_points_snapshot=task.reward_points,
        reward_points_awarded=0,
    )
    try:
        db.add(user_task)
        db.commit()
        db.refresh(user_task)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="User is already registered for this task"
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Volunteer registration failed user=%s task=%s", user.id, task.id)
        raise HTTPException(status_code=500, detail="Volunteer registration failed") from exc

    logger.info("Volunteer registered user=%s task=%s", user.id, task.id)
    return VolunteerRegisterResponse(
        user_task_id=user_task.id,
        registration_id=user_task.id,
        task_id=task.id,
        user_id=user.id,
        reward_points_pending=user_task.reward_points_snapshot,
        points_balance=user.points,
    )


@router.post(
    "/tasks/{task_id}/complete",
    response_model=VolunteerCompleteResponse,
    dependencies=[Depends(require_dispatcher_key)],
)
def complete_task(
    task_id: int,
    payload: VolunteerCompleteRequest,
    db: Session = Depends(get_db),
) -> VolunteerCompleteResponse:
    """Complete one registration and award its snapshotted reward exactly once."""

    user = find_user(db, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != "volunteer":
        raise HTTPException(status_code=403, detail="Volunteer role required")
    dispatcher = find_user(db, payload.dispatcher_id)
    if dispatcher is None:
        raise HTTPException(status_code=404, detail="Dispatcher not found")
    if dispatcher.role != "dispatcher":
        raise HTTPException(status_code=403, detail="Dispatcher role required")
    task = db.get(VolunteerTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Volunteer task not found")
    user_task = db.scalar(
        select(UserTask).where(
            UserTask.user_id == user.id,
            UserTask.task_id == task.id,
        )
    )
    if user_task is None:
        raise HTTPException(status_code=404, detail="Task registration not found")

    completed_at = utcnow()
    try:
        transition = db.execute(
            update(UserTask)
            .where(UserTask.id == user_task.id, UserTask.status == "registered")
            .values(status="completed", completed_at=completed_at)
            .execution_options(synchronize_session=False)
        )
        if transition.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="Task is already completed")

        reward = user_task.reward_points_snapshot or task.reward_points
        points_result = credit_points(
            db,
            user,
            reward,
            "VOLUNTEER_REWARD",
            f"Награда за задачу: {task.title}",
            f"user-task:{user_task.id}",
        )
        db.execute(
            update(UserTask)
            .where(UserTask.id == user_task.id)
            .values(reward_points_awarded=reward)
            .execution_options(synchronize_session=False)
        )
        task.status = "completed"
        db.commit()
    except HTTPException:
        raise
    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        db.rollback()
        logger.exception("Volunteer completion failed user=%s task=%s", user.id, task.id)
        raise HTTPException(status_code=500, detail="Task completion failed") from exc

    logger.info("Volunteer task completed user=%s task=%s reward=%s", user.id, task.id, reward)
    return VolunteerCompleteResponse(
        user_task_id=user_task.id,
        task_id=task.id,
        user_id=user.id,
        points_awarded=reward,
        current_balance=points_result.balance,
        completed_at=completed_at,
    )
