
from fastapi import APIRouter

from database.db import get_connection

router = APIRouter(
    prefix="/api/analytics",
    tags=["Campus Analytics"],
)


@router.get("/blocks")
def get_block_analytics():
    """
    Return issue statistics for every block that has reported issues.
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                block_name,
                COUNT(*) AS total_issues,
                SUM(
                    CASE WHEN status = 'open'
                    THEN 1 ELSE 0 END
                ) AS open_issues,
                SUM(
                    CASE WHEN status = 'in_progress'
                    THEN 1 ELSE 0 END
                ) AS in_progress_issues,
                SUM(
                    CASE WHEN status = 'resolved'
                    THEN 1 ELSE 0 END
                ) AS resolved_issues,
                SUM(
                    CASE
                        WHEN severity = 'critical'
                        AND status != 'resolved'
                        THEN 1 ELSE 0
                    END
                ) AS critical_issues,
                SUM(
                    CASE
                        WHEN severity = 'high'
                        AND status != 'resolved'
                        THEN 1 ELSE 0
                    END
                ) AS high_issues
            FROM issues
            GROUP BY block_name
            ORDER BY total_issues DESC, block_name ASC
            """
        ).fetchall()

    blocks = [dict(row) for row in rows]

    return {
        "total_blocks_with_issues": len(blocks),
        "blocks": blocks,
    }


@router.get("/summary")
def get_campus_summary():
    """
    Return overall campus issue statistics.
    """

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_issues,
                SUM(
                    CASE WHEN status = 'open'
                    THEN 1 ELSE 0 END
                ) AS open_issues,
                SUM(
                    CASE WHEN status = 'in_progress'
                    THEN 1 ELSE 0 END
                ) AS in_progress_issues,
                SUM(
                    CASE WHEN status = 'resolved'
                    THEN 1 ELSE 0 END
                ) AS resolved_issues,
                SUM(
                    CASE
                        WHEN severity IN ('high', 'critical')
                        AND status != 'resolved'
                        THEN 1 ELSE 0
                    END
                ) AS high_priority_issues
            FROM issues
            """
        ).fetchone()

    summary = dict(row)

    # SQLite returns NULL for SUM when the table is empty.
    for key, value in summary.items():
        if value is None:
            summary[key] = 0

    return summary
