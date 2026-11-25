const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>\'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 3600);
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Request failed");
  }
  return response.json();
}

function renderRequirements(requirements) {
  const list = $("#requirementsList");
  if (!requirements.length) {
    list.innerHTML = '<article class="requirement"><p>No explicit requirement statements were identified. The SRS includes the original brief and flags this as a review item.</p></article>';
    return;
  }
  list.innerHTML = requirements.map((req) => `
    <article class="requirement">
      <div class="requirement-head"><div><span class="req-id">${escapeHtml(req.id)}</span><h3>${escapeHtml(req.statement)}</h3><div class="tags">${req.categories.map((category) => `<span class="tag">${escapeHtml(category)}</span>`).join("")}</div></div><span class="state">${escapeHtml(req.approval_status)}</span></div>
      <div class="requirement-grid"><div><span class="field-label">Business justification</span><p>${escapeHtml(req.business_justification)}</p></div><div><span class="field-label">Confidence / risk</span><p>${Math.round(req.confidence * 100)}% confidence · ${escapeHtml(req.risk_level)} risk</p></div><div><span class="field-label">Acceptance criteria</span><p>${req.acceptance_criteria.map(escapeHtml).join("<br>")}</p></div><div><span class="field-label">Agent notes</span><p>${escapeHtml(req.reasoning)}</p></div></div>
      ${req.evidence.map((source) => `<div class="evidence"><span class="field-label">Source · ${escapeHtml(source.document_name)} / ${escapeHtml(source.chunk_id)}</span><p>${escapeHtml(source.excerpt)}</p></div>`).join("")}
    </article>`).join("");
}

$("#briefForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("#generateButton");
  const brief = $("#projectBrief").value.trim();
  if (brief.length < 30) {
    toast("Please enter a project brief with at least 30 characters.");
    return;
  }
  button.disabled = true;
  button.textContent = "Agents are generating your SRS…";
  try {
    const data = await request("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_brief: brief }),
    });
    $("#briefPreview").textContent = data.project_brief;
    $("#requirementCount").textContent = `${data.requirements.length} draft requirement(s)`;
    $("#agentStatus").textContent = data.agent_runs.map((run) => `${run.agent}: ${run.output}`).join(" · ");
    $("#downloadSrs").href = data.srs_download_url;
    renderRequirements(data.requirements);
    $("#resultPanel").classList.remove("is-hidden");
    $("#resultPanel").scrollIntoView({ behavior: "smooth", block: "start" });
    toast("Your draft requirements and SRS are ready.");
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Generate requirements and SRS";
  }
});
