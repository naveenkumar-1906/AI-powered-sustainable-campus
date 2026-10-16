function setBlockIssueCount(blockName, count = 0) {
    const marker = document.querySelector(
      `#campus-map .campus-marker[data-block="${blockName}"]`
    );
  
    if (!marker) return;
  
    const countElement = marker.querySelector(
      ".block-issues, [data-issue-count]"
    );
  
    if (countElement) {
      countElement.textContent =
        count === 1 ? "1 open issue" : `${count} issues`;
    }
  }