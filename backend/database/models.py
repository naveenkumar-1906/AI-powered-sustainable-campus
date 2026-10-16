
def issue_to_dict(row):
    if row is None:
        return None

    issue = dict(row)

    if issue.get("confidence") is not None:
        issue["confidence"] = round(
            float(issue["confidence"]), 3
        )

    return issue
