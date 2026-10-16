
"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const pageNames = {
    overview: "Campus overview",
    "campus-blocks": "Campus blocks",
    "issue-management": "Issue management",
    cctv: "CCTV footage analysis",
    "live-alerts": "Live alerts"
  };

  let selectedBlock = "Block A";
  let previewUrl = null;
  let currentIssues = [];

  function showPage(pageId) {
    if (!pageNames[pageId]) pageId = "overview";

    $$(".page-section").forEach(section => {
      const active = section.id === pageId;
      section.classList.toggle("hidden", !active);
      section.setAttribute("aria-hidden", String(!active));
    });

    $$(".nav-link").forEach(button => {
      button.classList.toggle("active", button.dataset.pageTarget === pageId);
    });

    $("#page-title").textContent = pageNames[pageId];
    $("#page-subtitle").textContent =
      pageId === "cctv"
        ? `Analyse authorized footage for ${selectedBlock}.`
        : "Dayananda Sagar University · Smarter sustainability.";

    if (pageId === "issue-management") loadIssues();
    if (pageId === "overview" || pageId === "campus-blocks") loadIssues();
    if (pageId === "live-alerts") loadAlerts();

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  document.addEventListener("click", event => {
    const navButton = event.target.closest("[data-page-target]");
    if (navButton) {
      event.preventDefault();
      showPage(navButton.dataset.pageTarget);
      return;
    }

    const blockButton = event.target.closest("[data-block]");
    if (blockButton) {
      selectedBlock = blockButton.dataset.block;
      $("#selected-cctv-block").textContent = selectedBlock;

      $$("[data-block]").forEach(button => {
        button.classList.toggle("is-selected", button.dataset.block === selectedBlock);
      });

      showPage("cctv");
    }
  });

  // Theme toggle
  $("#theme-toggle")?.addEventListener("click", () => {
    const dark = document.body.classList.toggle("dark-mode");
    $("#theme-toggle").textContent = dark ? "☀" : "☾";
    $("#theme-toggle").setAttribute("aria-pressed", String(dark));
  });

  async function apiFetch(url, options = {}) {
    const response = await fetch(url, options);
    const text = await response.text();
    let data = {};

    try { data = text ? JSON.parse(text) : {}; }
    catch { data = { detail: text }; }

    if (!response.ok) {
      const message = data.detail || data.message || `Request failed (${response.status})`;
      throw new Error(message);
    }

    return data;
  }

  async function checkBackend() {
    const status = $("#backend-status");
    const dot = $("#backend-dot");

    try {
      await apiFetch("/health");
      status.textContent = "Connected";
      dot.classList.add("connected");
      dot.classList.remove("error");
    } catch {
      status.textContent = "Disconnected";
      dot.classList.add("error");
      dot.classList.remove("connected");
    }
  }

  function issueArray(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.issues)) return data.issues;
    if (Array.isArray(data.items)) return data.items;
    return [];
  }

  function priorityOf(issue) {
    return String(issue.priority || issue.severity || "low").toLowerCase();
  }

  function statusOf(issue) {
    return String(issue.status || "open").toLowerCase();
  }

  function blockOf(issue) {
    return String(issue.block || issue.block_name || issue.location || "");
  }

  function isResolved(issue) {
    return ["resolved", "closed", "completed", "fixed"].includes(statusOf(issue));
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
  }

  function renderIssue(issue) {
    const priority = priorityOf(issue);
    const title = issue.title || issue.issue_type || issue.type || "Campus issue";
    const block = blockOf(issue) || "Unspecified block";
    const description = issue.description || issue.recommendation || "";
    const resolved = isResolved(issue);

    return `
      <article class="issue-item">
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(block)} · ${escapeHtml(statusOf(issue))}</p>
        <p class="priority-label ${escapeHtml(priority)}">
          ${escapeHtml(priority.toUpperCase())} priority
        </p>
        ${description ? `<p>${escapeHtml(description)}</p>` : ""}
        ${resolved ? '<p class="priority-label resolved">Resolved</p>' : ""}
      </article>`;
  }

  function renderIssues(issues) {
    currentIssues = issues;

    const openIssues = issues.filter(issue => !isResolved(issue));
    const highIssues = openIssues.filter(issue =>
      ["high", "critical"].includes(priorityOf(issue))
    );
    const resolvedIssues = issues.filter(isResolved);

    $("#total-issues").textContent = issues.length;
    $("#open-issues").textContent = openIssues.length;
    $("#high-priority-issues").textContent = highIssues.length;
    $("#resolved-issues").textContent = resolvedIssues.length;

    // All four map blocks begin with zero and update only from real records.
    $$(".campus-marker").forEach(marker => {
      const block = marker.dataset.block;
      const blockOpen = openIssues.filter(issue => blockOf(issue) === block);
      const count = blockOpen.length;
      const high = blockOpen.some(issue =>
        ["high", "critical"].includes(priorityOf(issue))
      );
      const medium = blockOpen.some(issue => priorityOf(issue) === "medium");

      const countLabel = $("[data-issue-count]", marker);
      if (countLabel) {
        countLabel.textContent = `${count} open ${count === 1 ? "issue" : "issues"}`;
      }

      marker.classList.remove("priority-high", "priority-low", "priority-none");
      marker.classList.add(count === 0 ? "priority-none" : high ? "priority-high" : "priority-low");
      if (medium && !high) marker.classList.add("priority-low");
    });

    const issueHtml = issues.length
      ? issues.map(renderIssue).join("")
      : "<p>No issues have been recorded.</p>";

    $("#issues-list").innerHTML = issueHtml;
    $("#recent-reports-list").innerHTML = issues.length
      ? issues.slice(-4).reverse().map(renderIssue).join("")
      : "<p>No reports have been recorded yet.</p>";
  }

  async function loadIssues() {
    try {
      // This is the expected existing issue API endpoint.
      const data = await apiFetch("/api/issues");
      renderIssues(issueArray(data));
    } catch (error) {
      $("#issues-list").innerHTML = `<p>Could not load issues: ${escapeHtml(error.message)}</p>`;
      $("#recent-reports-list").innerHTML = "<p>Issue records could not be loaded.</p>";
      console.error("Issue loading failed:", error);
    }
  }

  $("#refresh-issues")?.addEventListener("click", loadIssues);

  async function loadAlerts() {
    try {
      const data = await apiFetch("/api/alerts");
      const alerts = Array.isArray(data) ? data : (data.alerts || []);
      $("#live-alert-count").textContent = alerts.length;
      $("#live-alerts-list").innerHTML = alerts.length
        ? alerts.map(renderIssue).join("")
        : "<p>No alerts at this time.</p>";
    } catch {
      $("#live-alerts-list").innerHTML =
        "<p>Live alerts are unavailable. Check the backend alert route.</p>";
    }
  }

  // Video preview
  $("#video-file")?.addEventListener("change", event => {
    const file = event.target.files?.[0];
    const video = $("#video-preview");
    const info = $("#video-file-info");
    const status = $("#video-analysis-status");
    const button = $("#analyse-video-button");

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    video.hidden = true;
    video.removeAttribute("src");

    if (!file) {
      info.textContent = "No video selected.";
      status.textContent = "Select a video to begin.";
      button.disabled = true;
      return;
    }

    const allowed = /\.(mp4|mov|avi|webm|mkv)$/i.test(file.name);
    if (!allowed) {
      info.textContent = "Unsupported video format.";
      status.textContent = "Choose an MP4, MOV, AVI, WEBM or MKV video.";
      button.disabled = true;
      return;
    }

    info.textContent = `${file.name} · ${(file.size / (1024 * 1024)).toFixed(2)} MB`;
    previewUrl = URL.createObjectURL(file);
    video.src = previewUrl;
    video.hidden = false;
    status.textContent = "Video ready. Click Analyse footage.";
    button.disabled = false;
  });

  function renderAnalysis(data) {
    const counts = data.sustainability_counts || data.sustainability || data.counts || {};
    const findings = Array.isArray(data.findings) ? data.findings : [];
    const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];

    $("#water-count").textContent =
      counts.water_leakage ?? counts.water ?? "Not detected by current model";
    $("#electricity-count").textContent =
      counts.electricity_wastage ?? counts.electricity ?? "Not detected by current model";
    $("#trash-count").textContent =
      counts.overflowing_trash ?? counts.trash ?? "Not detected by current model";

    const summary = data.message || "Analysis completed.";
    const frameText = data.frames_processed != null
      ? `Frames processed: ${data.frames_processed}.`
      : "";

    const findingsHtml = findings.length
      ? findings.map(item => `
          <article class="recommendation-item">
            <strong>${escapeHtml(item.label || item.type || "Finding")}</strong>
            <p>${escapeHtml(item.description || item.message || "")}</p>
            ${item.suggestion ? `<p><strong>Suggestion:</strong> ${escapeHtml(item.suggestion)}</p>` : ""}
          </article>`).join("")
      : "<p>No supported sustainability detections were returned. This does not prove that no problem exists.</p>";

    $("#vision-findings").innerHTML =
      `<p>${escapeHtml(summary)} ${escapeHtml(frameText)}</p>${findingsHtml}`;

    $("#recommendations-list").innerHTML = recommendations.length
      ? `<h3>Suggested actions</h3>${recommendations.map(item =>
          `<article class="recommendation-item"><p>${escapeHtml(
            typeof item === "string" ? item : item.suggestion || item.text || item.title || ""
          )}</p></article>`
        ).join("")}`
      : "";
  }

  $("#analyse-video-button")?.addEventListener("click", async () => {
    const input = $("#video-file");
    const button = $("#analyse-video-button");
    const status = $("#video-analysis-status");
    const file = input.files?.[0];

    if (!file) {
      status.textContent = "Please choose a video first.";
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("block", selectedBlock);

    button.disabled = true;
    status.textContent = "Analysing footage. Please wait...";
    $("#vision-findings").textContent = "Processing video...";
    $("#water-count").textContent = "…";
    $("#electricity-count").textContent = "…";
    $("#trash-count").textContent = "…";
    $("#recommendations-list").innerHTML = "";

    try {
      // Must match the FastAPI route path.
      const data = await apiFetch("/api/camera/analyze-video", {
        method: "POST",
        body: formData
      });

      renderAnalysis(data);
      status.textContent = `Analysis finished for ${selectedBlock}. Review findings before reporting an issue.`;
    } catch (error) {
      status.textContent = `Analysis failed: ${error.message}`;
      $("#vision-findings").textContent =
        "The backend could not analyse this video. Check the server terminal and API route.";
      console.error("Video analysis failed:", error);
    } finally {
      button.disabled = false;
    }
  });

  // Initial page state and data
  $("#analyse-video-button").disabled = true;
  showPage("overview");
  checkBackend();
  loadIssues();

  // Clean up the local preview URL when leaving the page.
  window.addEventListener("beforeunload", () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  });
});
