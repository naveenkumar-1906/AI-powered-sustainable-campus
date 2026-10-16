
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal, Optional

from database.db import get_connection
from database.models import issue_to_dict
from services.alerts import alert_manager

router = APIRouter(prefix="/api/issues", tags=["Issues"])

Category = Literal[
    "waste", "water", "energy", "safety", "other"
]
Severity = Literal["low", "medium", "high", "critical"]
Status = Literal["open", "in_progress", "resolved"]


class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(default="", max_length=2000)
    category: Category
    block_name: str = Field(min_length=1, max_length=80)
    severity: Severity = "medium"
    source: Literal["manual", "vision", "sensor"] = "manual"
    confidence: Optional[float] = Field(default=None, ge=0, le=1)


class IssueUpdate(BaseModel):
    status: Optional[Status] = None
    severity: Optional[Severity] = None


def calculate_priority(severity: str) -> int:
    scores = {
        "low": 20,
        "medium": 50,
        "high": 75,
        "critical": 100,
    }
    return scores[severity]


@router.post("", status_code=201)

async def create_issue(payload: IssueCreate):

    priority = calculate_priority(payload.severity)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO issues (
                title, description, category, block_name,
                severity, priority_score, source, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.title,
                payload.description,
                payload.category,
                payload.block_name,
                payload.severity,
                priority,
                payload.source,
                payload.confidence,
            ),
        )

        row = connection.execute(
            "SELECT * FROM issues WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    issue = issue_to_dict(row)

    print("DEBUG: Broadcasting issue_created", issue["id"])


    await alert_manager.broadcast({
        "type": "issue_created",
        "issue": issue,
    })

    return issue


@router.get("")
def list_issues(
    status: Optional[Status] = None,
    block_name: Optional[str] = Query(default=None, max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
):
    query = "SELECT * FROM issues WHERE 1=1"
    parameters = []

    if status:
        query += " AND status = ?"
        parameters.append(status)

    if block_name:
        query += " AND block_name = ?"
        parameters.append(block_name)

    query += " ORDER BY priority_score DESC, created_at DESC LIMIT ?"
    parameters.append(limit)

    with get_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [issue_to_dict(row) for row in rows]


@router.get("/{issue_id}")
def get_issue(issue_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM issues WHERE id = ?",
            (issue_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Issue not found")

    return issue_to_dict(row)


@router.patch("/{issue_id}")
async def update_issue(issue_id: int, payload: IssueUpdate):
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide status or severity to update",
        )

    with get_connection() as connection:
        existing = connection.execute(
            "SELECT * FROM issues WHERE id = ?",
            (issue_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Issue not found",
            )

        fields = []
        values = []

        if "status" in updates:
            fields.append("status = ?")
            values.append(updates["status"])

        if "severity" in updates:
            fields.append("severity = ?")
            values.append(updates["severity"])
            fields.append("priority_score = ?")
            values.append(calculate_priority(updates["severity"]))

        fields.append("updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')")
        values.append(issue_id)

        connection.execute(
            f"UPDATE issues SET {', '.join(fields)} WHERE id = ?",
            values,
        )

        row = connection.execute(
            "SELECT * FROM issues WHERE id = ?",
            (issue_id,),
        ).fetchone()

    return issue_to_dict(row)
