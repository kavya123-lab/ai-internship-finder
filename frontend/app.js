// ---------- Autosuggest data ----------
const ROLE_SUGGESTIONS = [
  "AI/ML Intern", "Data Scientist Intern", "Data Analyst Intern", "Backend Developer Intern",
  "Frontend Developer Intern", "Full Stack Developer Intern", "Python Developer Intern",
  "Data Engineer Intern", "DevOps Intern", "Cloud Engineer Intern", "Software Engineer Intern",
  "Mobile App Developer Intern", "UI/UX Designer Intern", "Product Management Intern",
  "QA / Testing Intern", "Cybersecurity Intern", "Business Analyst Intern",
  "Digital Marketing Intern", "Content Writing Intern", "HR Intern", "GenAI Engineer Intern",
  "NLP Intern", "Computer Vision Intern",
];

const LOCATION_SUGGESTIONS = [
  "Remote", "Ahmedabad", "Bengaluru", "Mumbai", "Delhi", "Gurugram", "Noida", "Pune",
  "Hyderabad", "Chennai", "Kolkata", "Jaipur", "Surat", "Vadodara", "Indore", "Chandigarh",
];

const SKILL_SUGGESTIONS = [
  "Python", "Java", "C++", "JavaScript", "TypeScript", "React", "Node.js", "SQL",
  "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "TensorFlow", "PyTorch",
  "AWS", "Docker", "Kubernetes", "Git", "Pandas", "NumPy", "Excel", "Power BI", "Tableau",
  "Django", "Flask", "FastAPI", "HTML", "CSS", "MongoDB", "REST API", "GenAI", "LLM",
  "RAG", "LangChain", "Data Structures", "Figma", "Scikit-learn",
];

/** Wires a text input to a filtered suggestion dropdown. onSelect(value) runs
 * when a suggestion is clicked; the caller decides what to do with it. */
function attachAutosuggest(inputEl, listEl, suggestions, onSelect) {
  function render(query) {
    const q = query.trim().toLowerCase();
    if (!q) { listEl.classList.add("hidden"); listEl.innerHTML = ""; return; }
    const matches = suggestions.filter(s => s.toLowerCase().includes(q)).slice(0, 7);
    if (!matches.length) { listEl.classList.add("hidden"); listEl.innerHTML = ""; return; }
    listEl.innerHTML = matches.map(m => `<div class="suggestion-item">${escapeHtml(m)}</div>`).join("");
    listEl.classList.remove("hidden");
  }

  inputEl.addEventListener("input", () => render(inputEl.value));
  inputEl.addEventListener("focus", () => render(inputEl.value));
  listEl.addEventListener("mousedown", (e) => {
    const item = e.target.closest(".suggestion-item");
    if (!item) return;
    e.preventDefault();
    onSelect(item.textContent);
    listEl.classList.add("hidden");
  });
  document.addEventListener("click", (e) => {
    if (!inputEl.contains(e.target) && !listEl.contains(e.target)) {
      listEl.classList.add("hidden");
    }
  });
}

attachAutosuggest(
  document.getElementById("role"),
  document.getElementById("role-suggestions"),
  ROLE_SUGGESTIONS,
  (val) => { document.getElementById("role").value = val; }
);

attachAutosuggest(
  document.getElementById("location"),
  document.getElementById("location-suggestions"),
  LOCATION_SUGGESTIONS,
  (val) => { document.getElementById("location").value = val; }
);

// ---------- Skills tag input ----------
const skillsInput = document.getElementById("skills-input");
const skillsChipsEl = document.getElementById("skills-chips");
const skillsSuggestionsEl = document.getElementById("skills-suggestions");
let skillChips = [];

function renderChips() {
  skillsChipsEl.innerHTML = skillChips.map((s, idx) =>
    `<span class="skill-chip">${escapeHtml(s)}<button type="button" class="chip-remove" data-idx="${idx}" aria-label="Remove">&times;</button></span>`
  ).join("");
  skillsChipsEl.querySelectorAll(".chip-remove").forEach(btn => {
    btn.addEventListener("click", () => {
      skillChips.splice(Number(btn.dataset.idx), 1);
      renderChips();
    });
  });
}

function addSkillChip(value) {
  const v = value.trim();
  if (!v) return;
  if (!skillChips.some(s => s.toLowerCase() === v.toLowerCase())) {
    skillChips.push(v);
    renderChips();
  }
  skillsInput.value = "";
  skillsSuggestionsEl.classList.add("hidden");
}

skillsInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === ",") {
    e.preventDefault();
    addSkillChip(skillsInput.value);
  } else if (e.key === "Backspace" && !skillsInput.value && skillChips.length) {
    skillChips.pop();
    renderChips();
  }
});

attachAutosuggest(skillsInput, skillsSuggestionsEl, SKILL_SUGGESTIONS, addSkillChip);


const form = document.getElementById("search-form");
const resultsSection = document.getElementById("results-section");
const resultsGrid = document.getElementById("results-grid");
const summaryEl = document.getElementById("search-summary");
const loadingEl = document.getElementById("loading");
const emptyEl = document.getElementById("empty-state");

let currentResults = [];

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const role = document.getElementById("role").value.trim();
  const location = document.getElementById("location").value.trim();
  const workMode = document.getElementById("work_mode").value;
  const experience = document.getElementById("experience").value;

  // If the user typed a skill but didn't press Enter, still include it
  if (skillsInput.value.trim()) addSkillChip(skillsInput.value);
  const skills = skillChips.join(", ");

  if (!role) {
    alert("Please enter a role to search for.");
    return;
  }

  resultsSection.classList.remove("hidden");
  loadingEl.classList.remove("hidden");
  resultsGrid.innerHTML = "";
  emptyEl.classList.add("hidden");
  summaryEl.textContent = "";

  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role, location, work_mode: workMode, skills, experience_level: experience,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Search failed");

    currentResults = data.results;
    loadingEl.classList.add("hidden");

    if (!currentResults.length) {
      emptyEl.classList.remove("hidden");
      emptyEl.innerHTML = `<p><strong>No actively-hiring internships posted in the last 24 hours matched this search.</strong></p>
        <p class="hint-text">This filter is strict on purpose — try again in a few hours as new postings appear, or broaden your role/skills/location.</p>`;
      return;
    }

    summaryEl.innerHTML = `<strong>${data.count}</strong> internship${data.count === 1 ? "" : "s"} found — all posted in the last 24 hours and actively hiring.`;

    renderResults(currentResults);
  } catch (err) {
    loadingEl.classList.add("hidden");
    resultsGrid.innerHTML = `<p class="error-text">Something went wrong: ${escapeHtml(err.message)}. Double-check your API keys in .env and try again.</p>`;
  }
});

function sourceLabel(source) {
  const s = (source || "").toLowerCase();
  if (s.includes("linkedin")) return { text: "LinkedIn", cls: "src-linkedin" };
  if (s.includes("internshala")) return { text: "Internshala", cls: "src-internshala" };
  if (s.includes("indeed")) return { text: "Indeed", cls: "src-indeed" };
  if (s.includes("naukri")) return { text: "Naukri", cls: "src-naukri" };
  return { text: "Job Board", cls: "src-default" };
}

function renderResults(results) {
  resultsGrid.innerHTML = results.map((r, idx) => {
    const src = sourceLabel(r.source);
    const skillsHtml = (r.skills_required || []).slice(0, 6)
      .map(s => `<span class="chip">${escapeHtml(s)}</span>`).join("");

    return `
    <article class="card">
      <div class="card-top">
        <span class="badge ${src.cls}">${src.text}</span>
        <span class="badge badge-new">Actively Hiring</span>
        ${r.company_verified ? `<span class="badge badge-verified">Verified</span>` : ""}
      </div>

      <h3 class="card-role">${escapeHtml(r.role)}</h3>
      <p class="card-company">${escapeHtml(r.company)}</p>

      <div class="card-meta">
        <span>${iconPin()} ${escapeHtml(r.location)}</span>
        <span>${iconBriefcase()} ${escapeHtml(r.work_mode)}</span>
      </div>
      <div class="card-meta">
        <span>${iconClock()} ${escapeHtml(r.posted)}</span>
        <span>${iconCalendar()} ${escapeHtml(r.duration)}</span>
        <span>${iconMoney()} ${escapeHtml(r.stipend)}</span>
      </div>

      ${skillsHtml ? `<div class="chips">${skillsHtml}</div>` : ""}

      <div class="card-footer">
        <div class="score">
          <span class="score-num">${r.match_score}</span>
          <span class="score-label">match</span>
        </div>
        <div class="card-actions">
          <a class="btn-outline" href="${r.application_link}" target="_blank" rel="noopener">View Listing</a>
          <button class="btn-primary" type="button" onclick="openApplyModal(${idx})">Apply Now</button>
        </div>
      </div>
    </article>`;
  }).join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---------- tiny inline icons ----------
function iconPin() { return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-6.2-7-11a7 7 0 1 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>`; }
function iconClock() { return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>`; }
function iconCalendar() { return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>`; }
function iconMoney() { return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/></svg>`; }
function iconBriefcase() { return `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`; }

// ---------- Apply modal ----------
const modal = document.getElementById("apply-modal");
const applyForm = document.getElementById("apply-form");
const modalTitle = document.getElementById("modal-role-title");
const applyStatus = document.getElementById("apply-status");
let selectedInternship = null;

async function openApplyModal(idx) {
  selectedInternship = currentResults[idx];
  modalTitle.textContent = `${selectedInternship.role} at ${selectedInternship.company}`;
  applyForm.reset();
  applyForm.querySelectorAll("input").forEach(i => i.disabled = false);
  applyStatus.innerHTML = "";
  const submitBtn = applyForm.querySelector("button[type=submit]");
  submitBtn.disabled = false;
  submitBtn.textContent = "Submit Application";
  modal.classList.remove("hidden");

  const recruiterInput = document.getElementById("recruiter_email");
  const recruiterStatus = document.getElementById("recruiter-email-status");
  recruiterInput.value = "";

  // If the original listing already contained a recruiter email, use it immediately.
  if (selectedInternship.recruiter_email) {
    recruiterInput.value = selectedInternship.recruiter_email;
    recruiterStatus.textContent = "Found in the original listing — please verify.";
    recruiterStatus.className = "hint hint-warn";
    return;
  }

  // Otherwise, auto-search the company's own website for a published HR email.
  recruiterInput.placeholder = "Searching company website...";
  recruiterStatus.textContent = "🔎 Looking up the company's HR/careers email...";
  recruiterStatus.className = "hint";

  try {
    const res = await fetch("/api/find-recruiter-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company: selectedInternship.company,
        application_link: selectedInternship.application_link,
      }),
    });
    const data = await res.json();

    if (data.email && data.confidence === "verified") {
      recruiterInput.value = data.email;
      const host = data.source_url ? new URL(data.source_url).hostname : "the company site";
      recruiterStatus.textContent = `✅ Found on ${host} — please confirm before sending.`;
      recruiterStatus.className = "hint hint-found";
    } else {
      recruiterInput.placeholder = "Enter the recruiter/company email";
      recruiterStatus.textContent = "❌ Couldn't confidently confirm an email for this company — please enter it manually.";
      recruiterStatus.className = "hint hint-warn";
    }
  } catch (err) {
    recruiterInput.placeholder = "Enter the recruiter/company email";
    recruiterStatus.textContent = "Auto-lookup failed — please enter manually.";
    recruiterStatus.className = "hint hint-warn";
  }
}

function closeApplyModal() {
  modal.classList.add("hidden");
  selectedInternship = null;
}

document.getElementById("modal-close").addEventListener("click", closeApplyModal);
modal.addEventListener("click", (e) => { if (e.target === modal) closeApplyModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeApplyModal(); });

applyForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!selectedInternship) return;

  const submitBtn = applyForm.querySelector("button[type=submit]");
  submitBtn.disabled = true;
  submitBtn.textContent = "Sending...";
  applyStatus.innerHTML = "";

  const fd = new FormData(applyForm);
  fd.append("role", selectedInternship.role);
  fd.append("company", selectedInternship.company);

  try {
    const res = await fetch("/api/apply", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Application failed");

    applyStatus.innerHTML = `<div class="success-box">✅ Applied successfully — your application was sent for <strong>${escapeHtml(selectedInternship.role)}</strong> at <strong>${escapeHtml(selectedInternship.company)}</strong>.</div>`;
    applyForm.querySelectorAll("input").forEach(i => i.disabled = true);
    submitBtn.textContent = "Applied ✓";
  } catch (err) {
    applyStatus.innerHTML = `<div class="error-box">❌ ${escapeHtml(err.message)}</div>`;
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Application";
  }
});

// expose for inline onclick
window.openApplyModal = openApplyModal;
