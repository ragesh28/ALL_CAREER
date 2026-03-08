/**
 * ALL_CAREER — Jobs Page Logic
 */

// ---- State ----
let allJobs = [];
let filteredJobs = [];
let currentPage = 1;
const JOBS_PER_PAGE = 100;

// ---- Init ----
document.addEventListener("DOMContentLoaded", () => {
    fetchJobs();
    window.addEventListener('scroll', () => {
        document.body.classList.toggle('scrolled', window.scrollY > 50);
    });
});

// ---- Logo Helper (same as career_explorer.html) ----
function getLogoData(companyName) {
    const cleanName = companyName.replace(/\(.*\)/, '').trim();
    const domain = cleanName.toLowerCase().replace(/ /g, '').replace(/[^\w]/g, '') + '.com';
    return {
        clearbit: `https://logo.clearbit.com/${domain}`,
        google: `https://www.google.com/s2/favicons?domain=${domain}&sz=128`,
        ddg: `https://icons.duckduckgo.com/ip3/${domain}.ico`,
        initial: cleanName.charAt(0).toUpperCase()
    };
}

// ---- Fetch Jobs ----
async function fetchJobs() {
    try {
        const res = await fetch("/api/jobs");
        const data = await res.json();
        allJobs = data.jobs || [];
        updateStats();
        filterJobs();

        if (allJobs.length === 0) {
            showToast("No jobs found.", "info");
        } else {
            showToast(`Loaded ${allJobs.length} jobs`, "success");
        }
    } catch (err) {
        console.error("Failed to fetch jobs:", err);
        showToast("Failed to load jobs.", "error");
    }
}

// ---- Render Page ----
function renderPage() {
    const totalPages = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PER_PAGE));
    if (currentPage > totalPages) currentPage = totalPages;
    const start = (currentPage - 1) * JOBS_PER_PAGE;
    const end = start + JOBS_PER_PAGE;
    const pageJobs = filteredJobs.slice(start, end);
    renderJobs(pageJobs);
    renderPagination(totalPages);

    const visibleEl = document.getElementById("visibleCount");
    if (visibleEl) visibleEl.textContent = filteredJobs.length;
}

function goToPage(page) {
    currentPage = page;
    renderPage();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---- Render Jobs ----
function renderJobs(jobs) {
    const grid = document.getElementById("jobsGrid");
    const empty = document.getElementById("emptyState");

    if (jobs.length === 0) {
        grid.innerHTML = "";
        empty.style.display = "block";
        return;
    }
    empty.style.display = "none";
    grid.innerHTML = jobs.map((job, i) => createJobCard(job, i)).join("");
}

// ---- Pagination ----
function renderPagination(totalPages) {
    const container = document.getElementById("pagination");
    if (!container) return;
    container.innerHTML = "";
    if (totalPages <= 1) return;

    // Previous button
    const prevBtn = document.createElement("button");
    prevBtn.className = "page-btn nav-btn";
    prevBtn.innerHTML = "←";
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => goToPage(currentPage - 1);
    container.appendChild(prevBtn);

    // Page numbers with ellipsis
    const pages = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        pages.push(1);
        if (currentPage > 3) pages.push("...");
        for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
            pages.push(i);
        }
        if (currentPage < totalPages - 2) pages.push("...");
        pages.push(totalPages);
    }

    pages.forEach(p => {
        if (p === "...") {
            const ellipsis = document.createElement("span");
            ellipsis.className = "page-ellipsis";
            ellipsis.textContent = "...";
            container.appendChild(ellipsis);
        } else {
            const btn = document.createElement("button");
            btn.className = "page-btn" + (p === currentPage ? " active" : "");
            btn.textContent = p;
            btn.onclick = () => goToPage(p);
            container.appendChild(btn);
        }
    });

    // Next button
    const nextBtn = document.createElement("button");
    nextBtn.className = "page-btn nav-btn";
    nextBtn.innerHTML = "→";
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => goToPage(currentPage + 1);
    container.appendChild(nextBtn);
}

function createJobCard(job, index) {
    const company = job.company || "Company";
    const logo = getLogoData(company);
    const cityDisplay = job.search_location || job.city || extractCity(job.location) || "India";
    const jobType = job.job_type ? formatJobType(job.job_type) : null;
    const date = job.date_posted && job.date_posted !== "None" && job.date_posted !== "null" && job.date_posted !== ""
        ? formatDate(job.date_posted) : null;

    const metaTags = [
        `<span class="meta-tag"><span class="meta-icon">📍</span>${escapeHtml(cityDisplay)}</span>`,
        jobType ? `<span class="meta-tag"><span class="meta-icon">💼</span>${jobType}</span>` : "",
        job.job_level && job.job_level !== "not applicable"
            ? `<span class="meta-tag"><span class="meta-icon">📊</span>${escapeHtml(job.job_level)}</span>` : "",
    ].filter(Boolean).join("");

    const applyLink = job.apply_url || job.job_url_direct || job.job_url;
    let applyButton = "";
    if (applyLink) {
        applyButton = `<a href="${escapeHtml(applyLink)}" target="_blank" rel="noopener" class="apply-btn">View & Apply</a>`;
    }

    return `
    <div class="job-card" style="animation-delay: ${index * 0.04}s">
        <div class="card-top">
            <div class="logo-box">
                <img src="${logo.clearbit}" class="company-logo-img"
                     style="position:absolute; top:4px; left:4px; width:40px; height:40px;"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <img src="${logo.google}" class="company-logo-img"
                     style="display:none; position:absolute; top:4px; left:4px; width:40px; height:40px;"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <img src="${logo.ddg}" class="company-logo-img"
                     style="display:none; position:absolute; top:4px; left:4px; width:40px; height:40px;"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                <div class="logo-fallback" style="display:none;">${logo.initial}</div>
            </div>
            <div>
                <div class="card-company-name">${escapeHtml(company)}</div>
                <h3 class="card-title-text">${escapeHtml(job.title || "Untitled Position")}</h3>
            </div>
        </div>
        <div class="card-meta">${metaTags}</div>
        <div class="card-footer">
            <span class="card-date">📅 ${date || "Recently posted"}</span>
            ${applyButton}
        </div>
    </div>`;
}

// ---- Filter ----
function filterJobs() {
    const search = (document.getElementById("searchInput").value || "").toLowerCase().trim();
    filteredJobs = allJobs.filter(job => {
        if (search) {
            const haystack = [job.title, job.company, job.city, job.location, job.search_location, job.job_type]
                .filter(Boolean).join(" ").toLowerCase();
            if (!haystack.includes(search)) return false;
        }
        return true;
    });
    currentPage = 1;
    renderPage();
}

// ---- Stats ----
function updateStats() {
    const el = document.getElementById("totalJobs");
    if (el) el.textContent = allJobs.length;
}

// ---- Toast ----
function showToast(message, type = "info") {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.className = "toast " + type + " show";
    setTimeout(() => toast.classList.remove("show"), 4000);
}

// ---- Helpers ----
function formatJobType(type) {
    if (!type) return null;
    const map = { fulltime: "Full-time", parttime: "Part-time", contract: "Contract", internship: "Internship" };
    return map[type.toLowerCase()] || type;
}

function formatDate(dateStr) {
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return null;
        const now = new Date();
        const diff = Math.floor((now - d) / (1000 * 60 * 60 * 24));
        if (diff === 0) return "Today";
        if (diff === 1) return "Yesterday";
        if (diff < 7) return `${diff} days ago`;
        return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
    } catch { return null; }
}

function extractCity(location) {
    if (!location) return null;
    const parts = String(location).split(",");
    return parts[0]?.trim() || String(location);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
