"use strict";

/* =========================================
   SKILLBRIDGE EMPLOYER DASHBOARD
   ========================================= */

const EMPLOYER_API = "/api/employer";
const AUTH_ME_API = "/api/auth/me";

let employerCurrentUser = null;
let employerCompany = null;
let employerJobs = [];
let employerSkills = [];


document.addEventListener("DOMContentLoaded", () => {
    updateEmployerCopyright();
    setupEmployerLogout();
    setupCompanyForm();
    setupJobForm();
    setupEmployerRefresh();
    setupJobTableActions();
    loadEmployerUser();
});


/* =========================================
   COMMON HELPERS
   ========================================= */

function employerSetText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value ?? "";
    }
}


function employerNormalize(value) {
    return String(value ?? "")
        .trim()
        .toUpperCase()
        .replace(/[\s/-]+/g, "_");
}


function employerFormatRole(value) {
    return String(value || "EMPLOYER")
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, character => character.toUpperCase());
}


function updateEmployerCopyright() {
    employerSetText(
        "employerCurrentYear",
        new Date().getFullYear()
    );
}


function showEmployerMessage(message, type = "info") {
    const element = document.getElementById("employerMessage");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `employer-alert ${type}`;
    element.hidden = false;
}


function hideEmployerMessage() {
    const element = document.getElementById("employerMessage");

    if (element) {
        element.textContent = "";
        element.hidden = true;
    }
}


async function readEmployerResponse(response) {
    const content = await response.text();

    if (!content) {
        return {};
    }

    try {
        return JSON.parse(content);
    } catch {
        return { detail: content };
    }
}


function employerApiError(data, fallback = "The request failed.") {
    if (typeof data?.detail === "string") {
        return data.detail;
    }

    if (Array.isArray(data?.detail)) {
        return data.detail.map(item => {
            const field = Array.isArray(item.loc)
                ? item.loc.filter(part => part !== "body").join(".")
                : "";

            return field
                ? `${field}: ${item.msg || "Invalid value"}`
                : item.msg || "Invalid value";
        }).join("; ");
    }

    if (typeof data?.message === "string") {
        return data.message;
    }

    return fallback;
}


/* =========================================
   AUTHENTICATION
   ========================================= */

function getEmployerAuthorization() {
    const token = sessionStorage.getItem("access_token");

    if (!token) {
        return null;
    }

    const tokenType =
        sessionStorage.getItem("token_type") || "bearer";

    return `${tokenType} ${token}`;
}


function clearEmployerSession() {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("token_type");
    sessionStorage.removeItem("resume_id");
    sessionStorage.removeItem("resume_file_name");
}


async function employerApiRequest(path, options = {}) {
    const authorization = getEmployerAuthorization();

    if (!authorization) {
        clearEmployerSession();
        window.location.replace("/login");
        throw new Error("Your session has expired. Please log in again.");
    }

    const headers = {
        "Authorization": authorization,
        "Accept": "application/json",
        ...(options.headers || {})
    };

    const requestOptions = {
        ...options,
        headers
    };

    if (
        requestOptions.body &&
        !(requestOptions.body instanceof FormData)
    ) {
        headers["Content-Type"] = "application/json";
    }

    let response;

    try {
        response = await fetch(path, requestOptions);
    } catch {
        throw new Error(
            "Cannot connect to SkillBridge. Check that your FastAPI server is running."
        );
    }

    const result = await readEmployerResponse(response);

    if (response.status === 401) {
        clearEmployerSession();
        window.location.replace("/login");

        throw new Error("Your session has expired. Please log in again.");
    }

    if (!response.ok) {
        throw new Error(
            employerApiError(
                result,
                `Request failed with status ${response.status}.`
            )
        );
    }

    return result;
}


async function loadEmployerUser() {
    const authorization = getEmployerAuthorization();

    if (!authorization) {
        window.location.replace("/login");
        return;
    }

    showEmployerMessage("Checking your account...", "info");

    try {
        const result = await employerApiRequest(AUTH_ME_API);

        employerCurrentUser = result.user || result.data || result;

        const role = employerNormalize(
            employerCurrentUser.role ||
            employerCurrentUser.user_role
        );

        const employerRoles = [
            "EMPLOYER",
            "RECRUITER",
            "EMPLOYER_RECRUITER"
        ];

        if (role === "ADMIN") {
            window.location.replace("/admin");
            return;
        }

        if (role === "JOB_SEEKER") {
            window.location.replace("/dashboard");
            return;
        }

        if (!employerRoles.includes(role)) {
            clearEmployerSession();
            window.location.replace("/login");
            return;
        }

        displayEmployerUser(employerCurrentUser);

        const accountStatus = employerNormalize(
            employerCurrentUser.status ||
            employerCurrentUser.account_status
        );

        if (
            accountStatus &&
            !["ACTIVE", "APPROVED"].includes(accountStatus)
        ) {
            showEmployerApprovalPending(accountStatus);
            return;
        }

        await loadAllEmployerData();

    } catch (error) {
        if (
            error.message.toLowerCase().includes("pending admin approval") ||
            error.message.toLowerCase().includes("inactive")
        ) {
            showEmployerApprovalPending("PENDING");
            return;
        }

        showEmployerMessage(error.message, "error");
    }
}


function displayEmployerUser(user) {
    const name =
        user.name ||
        user.full_name ||
        user.username ||
        user.email?.split("@")[0] ||
        "Employer";

    const email = user.email || "Email not provided";

    const role = employerFormatRole(
        user.role || user.user_role || "EMPLOYER"
    );

    const initials = name
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map(part => part.charAt(0).toUpperCase())
        .join("") || "E";

    employerSetText("employerHeaderName", name);
    employerSetText("employerAvatar", initials);
    employerSetText(
        "employerWelcomeName",
        name.trim().split(/\s+/)[0]
    );

    employerSetText("employerRoleBadge", role);
    employerSetText("employerProfileName", name);
    employerSetText("employerProfileEmail", email);
    employerSetText("employerProfileRole", role);
}


function showEmployerApprovalPending(accountStatus) {
    const banner = document.getElementById("approvalBanner");
    const workspace = document.getElementById("employerWorkspace");

    if (banner) {
        banner.hidden = false;
    }

    if (workspace) {
        workspace.hidden = false;

        workspace.querySelectorAll(
            "input, select, textarea, button"
        ).forEach(control => {
            control.disabled = true;
        });
    }

    const heading = document.querySelector(
        "#approvalBanner strong"
    );

    const paragraph = document.querySelector(
        "#approvalBanner p"
    );

    if (heading) {
        heading.textContent = "Your employer account needs approval";
    }

    if (paragraph) {
        paragraph.textContent =
            `Current account status: ${accountStatus}. ` +
            "An administrator must approve or reactivate your account " +
            "before you can manage company information and job postings.";
    }

    showEmployerMessage(
        "Employer tools are disabled until account verification is complete.",
        "warning"
    );
}


/* =========================================
   LOGOUT
   ========================================= */

function setupEmployerLogout() {
    const button = document.getElementById("employerLogoutButton");

    if (!button) {
        return;
    }

    button.addEventListener("click", () => {
        clearEmployerSession();
        window.location.replace("/login");
    });
}


/* =========================================
   LOAD DASHBOARD DATA
   ========================================= */

async function loadAllEmployerData() {
    hideEmployerMessage();

    try {
        const [dashboardResult, companyResult, jobsResult, skillsResult] =
            await Promise.all([
                employerApiRequest(`${EMPLOYER_API}/dashboard`),
                employerApiRequest(`${EMPLOYER_API}/company`),
                employerApiRequest(`${EMPLOYER_API}/jobs`),
                employerApiRequest(`${EMPLOYER_API}/skills`)
            ]);

        employerCompany =
            companyResult?.company ||
            dashboardResult.company ||
            companyResult ||
            null;

        employerJobs = Array.isArray(jobsResult?.jobs)
            ? jobsResult.jobs
            : Array.isArray(jobsResult)
                ? jobsResult
                : [];

        employerSkills = Array.isArray(skillsResult?.skills)
            ? skillsResult.skills
            : Array.isArray(skillsResult)
                ? skillsResult
                : [];

        renderEmployerDashboard(dashboardResult);
        renderEmployerCompany(employerCompany);
        populateEmployerSkillOptions();
        renderEmployerJobs(employerJobs);

        hideEmployerMessage();

    } catch (error) {
        const message = error.message || "Unable to load dashboard data.";

        if (
            message.toLowerCase().includes("pending admin approval") ||
            message.toLowerCase().includes("inactive")
        ) {
            showEmployerApprovalPending("PENDING / INACTIVE");
        } else {
            showEmployerMessage(message, "error");
        }
    }
}


function renderEmployerDashboard(data = {}) {
    const activeJobs = employerJobs.filter(job =>
        employerNormalize(job.status) === "ACTIVE"
    );

    const inactiveJobs = employerJobs.length - activeJobs.length;

    employerSetText(
        "employerTotalJobs",
        data.total_jobs ?? employerJobs.length
    );

    employerSetText(
        "employerActiveJobs",
        data.active_jobs ?? activeJobs.length
    );

    employerSetText(
        "employerInactiveJobs",
        data.inactive_jobs ?? inactiveJobs
    );

    employerSetText(
        "employerCompanyStatus",
        employerCompany ? "Set up" : "Not set up"
    );

    const companyBadge = document.getElementById("companyStatusBadge");

    if (companyBadge) {
        companyBadge.textContent = employerCompany
            ? employerFormatRole(employerCompany.status || "ACTIVE")
            : "Not created";
    }
}


/* =========================================
   COMPANY PROFILE
   ========================================= */

function renderEmployerCompany(company) {
    const fields = {
        employerCompanyName: company?.name || "",
        employerCompanyIndustry: company?.industry || "",
        employerCompanyLocation: company?.location || "",
        employerCompanyWebsite: company?.website || "",
        employerCompanyDescription: company?.description || ""
    };

    Object.entries(fields).forEach(([id, value]) => {
        const element = document.getElementById(id);

        if (element) {
            element.value = value;
        }
    });

    const button = document.getElementById("saveCompanyButton");

    if (button) {
        button.textContent = company
            ? "Update Company Profile"
            : "Create Company Profile";
    }
}


function setupCompanyForm() {
    const form = document.getElementById("employerCompanyForm");

    if (!form) {
        return;
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();

        const button = document.getElementById("saveCompanyButton");

        const payload = {
            name: document.getElementById("employerCompanyName").value.trim(),
            industry: document.getElementById("employerCompanyIndustry").value.trim(),
            location: document.getElementById("employerCompanyLocation").value.trim(),
            website: document.getElementById("employerCompanyWebsite").value.trim(),
            description: document.getElementById("employerCompanyDescription").value.trim()
        };

        if (!payload.name) {
            showEmployerMessage("Company name is required.", "error");
            return;
        }

        if (
            payload.website &&
            !isValidHttpUrl(payload.website)
        ) {
            showEmployerMessage(
                "Enter a valid company website URL, such as https://example.com.",
                "error"
            );
            return;
        }

        setButtonBusy(button, true, "Saving...");

        try {
            const result = await employerApiRequest(
                `${EMPLOYER_API}/company`,
                {
                    method: "PUT",
                    body: JSON.stringify(payload)
                }
            );

            employerCompany = result.company || payload;

            showEmployerMessage(
                result.message || "Company profile saved successfully.",
                "success"
            );

            await loadAllEmployerData();

        } catch (error) {
            showEmployerMessage(error.message, "error");
        } finally {
            setButtonBusy(
                button,
                false,
                employerCompany
                    ? "Update Company Profile"
                    : "Create Company Profile"
            );
        }
    });
}


/* =========================================
   JOB SKILLS
   ========================================= */

function populateEmployerSkillOptions(selectedIds = []) {
    const select = document.getElementById("employerRequiredSkills");

    if (!select) {
        return;
    }

    select.replaceChildren();

    if (employerSkills.length === 0) {
        const option = document.createElement("option");
        option.disabled = true;
        option.textContent = "No active skills are available yet.";
        select.appendChild(option);
        return;
    }

    const selectedSet = new Set(
        selectedIds.map(id => String(id))
    );

    employerSkills.forEach(skill => {
        const option = document.createElement("option");

        option.value = String(skill.id);
        option.textContent = skill.name || `Skill ${skill.id}`;
        option.selected = selectedSet.has(String(skill.id));

        select.appendChild(option);
    });
}


function getSelectedEmployerSkillIds() {
    const select = document.getElementById("employerRequiredSkills");

    if (!select) {
        return [];
    }

    return Array.from(select.selectedOptions)
        .map(option => Number(option.value))
        .filter(id => Number.isInteger(id) && id > 0);
}


/* =========================================
   JOB FORM
   ========================================= */

function setupJobForm() {
    const form = document.getElementById("employerJobForm");

    if (!form) {
        return;
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();

        const jobId = document.getElementById("employerJobId").value.trim();

        const salaryMinValue =
            document.getElementById("employerSalaryMin").value;

        const salaryMaxValue =
            document.getElementById("employerSalaryMax").value;

        const salaryMin = salaryMinValue === ""
            ? null
            : Number(salaryMinValue);

        const salaryMax = salaryMaxValue === ""
            ? null
            : Number(salaryMaxValue);

        if (
            salaryMin !== null &&
            salaryMax !== null &&
            salaryMin > salaryMax
        ) {
            showEmployerMessage(
                "Minimum salary cannot be greater than maximum salary.",
                "error"
            );
            return;
        }

        if (
            (salaryMin !== null && salaryMin < 0) ||
            (salaryMax !== null && salaryMax < 0)
        ) {
            showEmployerMessage(
                "Salary must be zero or greater.",
                "error"
            );
            return;
        }

        const requiredSkillIds = getSelectedEmployerSkillIds();

        if (requiredSkillIds.length === 0) {
            showEmployerMessage(
                "Select at least one required skill for the job.",
                "error"
            );
            return;
        }

        const payload = {
            title: document.getElementById("employerJobTitle").value.trim(),
            location: document.getElementById("employerJobLocation").value.trim(),
            employment_type: document.getElementById("employerEmploymentType").value,
            salary_min: salaryMin,
            salary_max: salaryMax,
            currency: document.getElementById("employerCurrency").value,
            experience_required: document.getElementById("employerExperience").value.trim(),
            education_required: document.getElementById("employerEducation").value.trim(),
            application_url: document.getElementById("employerApplicationUrl").value.trim(),
            deadline: document.getElementById("employerJobDeadline").value || null,
            description: document.getElementById("employerJobDescription").value.trim(),
            status: document.getElementById("employerJobStatus").value,
            required_skill_ids: requiredSkillIds
        };

        if (!payload.title) {
            showEmployerMessage("Job title is required.", "error");
            return;
        }

        if (!payload.description) {
            showEmployerMessage("Job description is required.", "error");
            return;
        }

        if (
            payload.application_url &&
            !isValidHttpUrl(payload.application_url)
        ) {
            showEmployerMessage(
                "Enter a valid application URL beginning with https:// or http://.",
                "error"
            );
            return;
        }

        const button = document.getElementById("saveEmployerJobButton");
        const originalText = jobId
            ? "Update Job Posting"
            : "Create Job Posting";

        setButtonBusy(button, true, "Saving...");

        try {
            const endpoint = jobId
                ? `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}`
                : `${EMPLOYER_API}/jobs`;

            const result = await employerApiRequest(endpoint, {
                method: jobId ? "PUT" : "POST",
                body: JSON.stringify(payload)
            });

            showEmployerMessage(
                result.message ||
                (jobId
                    ? "Job posting updated successfully."
                    : "Job posting created successfully."),
                "success"
            );

            resetEmployerJobForm();
            await loadAllEmployerData();

        } catch (error) {
            showEmployerMessage(error.message, "error");
        } finally {
            setButtonBusy(
                button,
                false,
                document.getElementById("employerJobId").value
                    ? "Update Job Posting"
                    : originalText
            );
        }
    });

    document.getElementById("cancelEmployerJobEditButton")
        ?.addEventListener("click", resetEmployerJobForm);
}


function resetEmployerJobForm() {
    const form = document.getElementById("employerJobForm");

    if (form) {
        form.reset();
    }

    employerSetText("jobEditorHeading", "Create a Job Posting");
    employerSetText("saveEmployerJobButton", "Create Job Posting");

    const hiddenId = document.getElementById("employerJobId");

    if (hiddenId) {
        hiddenId.value = "";
    }

    const status = document.getElementById("employerJobStatus");

    if (status) {
        status.value = "ACTIVE";
    }

    const cancelButton = document.getElementById(
        "cancelEmployerJobEditButton"
    );

    if (cancelButton) {
        cancelButton.hidden = true;
    }

    populateEmployerSkillOptions([]);
}


function editEmployerJob(jobId) {
    const job = employerJobs.find(
        item => String(item.id) === String(jobId)
    );

    if (!job) {
        showEmployerMessage("Could not find that job posting.", "error");
        return;
    }

    document.getElementById("employerJobId").value = job.id;
    document.getElementById("employerJobTitle").value = job.title || "";
    document.getElementById("employerJobLocation").value = job.location || "";
    document.getElementById("employerEmploymentType").value =
        job.employment_type || "Full-time";

    document.getElementById("employerSalaryMin").value =
        job.salary_min ?? "";

    document.getElementById("employerSalaryMax").value =
        job.salary_max ?? "";

    document.getElementById("employerCurrency").value =
        job.currency || "BDT";

    document.getElementById("employerExperience").value =
        job.experience_required || "";

    document.getElementById("employerEducation").value =
        job.education_required || "";

    document.getElementById("employerApplicationUrl").value =
        job.application_url || "";

    document.getElementById("employerJobDescription").value =
        job.description || "";

    document.getElementById("employerJobStatus").value =
        ["ACTIVE", "DRAFT", "INACTIVE"].includes(
            employerNormalize(job.status)
        )
            ? employerNormalize(job.status)
            : "ACTIVE";

    const deadlineInput = document.getElementById("employerJobDeadline");

    if (deadlineInput) {
        deadlineInput.value = job.deadline
            ? formatForDateTimeLocal(job.deadline)
            : "";
    }

    const selectedIds = Array.isArray(job.required_skills)
        ? job.required_skills.map(skill =>
            typeof skill === "object" ? skill.id : skill
        )
        : [];

    populateEmployerSkillOptions(selectedIds);

    employerSetText("jobEditorHeading", "Edit Job Posting");
    employerSetText("saveEmployerJobButton", "Update Job Posting");

    const cancelButton = document.getElementById(
        "cancelEmployerJobEditButton"
    );

    if (cancelButton) {
        cancelButton.hidden = false;
    }

    document.getElementById("jobEditor").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


function formatForDateTimeLocal(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    const pad = number => String(number).padStart(2, "0");

    return (
        `${date.getFullYear()}-${pad(date.getMonth() + 1)}-` +
        `${pad(date.getDate())}T${pad(date.getHours())}:` +
        `${pad(date.getMinutes())}`
    );
}


/* =========================================
   RENDER JOB TABLE
   ========================================= */

function renderEmployerJobs(jobs) {
    const tbody = document.getElementById("employerJobsTableBody");

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();

    if (!jobs.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 6;
        cell.className = "employer-empty-state";
        cell.textContent =
            "You have not created any job postings yet. Create your first job above.";

        row.appendChild(cell);
        tbody.appendChild(row);

        return;
    }

    jobs.forEach(job => {
        const row = document.createElement("tr");

        const titleCell = document.createElement("td");
        const title = document.createElement("strong");
        title.textContent = job.title || "Untitled job";

        titleCell.appendChild(title);

        if (job.employment_type) {
            const type = document.createElement("div");
            type.className = "employer-help";
            type.textContent = job.employment_type;
            titleCell.appendChild(type);
        }

        row.appendChild(titleCell);

        row.appendChild(
            createEmployerCell(job.location || "Not specified")
        );

        row.appendChild(
            createEmployerCell(formatEmployerSalary(job))
        );

        const statusCell = document.createElement("td");
        const badge = document.createElement("span");
        const normalizedStatus = employerNormalize(job.status || "ACTIVE");

        badge.className = "employer-status";

        if (normalizedStatus === "ACTIVE") {
            badge.classList.add("active");
        } else if (normalizedStatus === "DRAFT") {
            badge.classList.add("draft");
        } else {
            badge.classList.add("inactive");
        }

        badge.textContent = employerFormatRole(normalizedStatus);
        statusCell.appendChild(badge);
        row.appendChild(statusCell);

        const skillsCell = document.createElement("td");

        const skillNames = Array.isArray(job.required_skills)
            ? job.required_skills.map(skill =>
                typeof skill === "string"
                    ? skill
                    : skill.name || "Unnamed skill"
            )
            : [];

        skillsCell.textContent = skillNames.length
            ? skillNames.join(", ")
            : "No skills listed";

        row.appendChild(skillsCell);

        const actionsCell = document.createElement("td");
        const actions = document.createElement("div");

        actions.className = "employer-table-actions";

        actions.appendChild(
            createJobActionButton("Edit", "edit", job.id, "secondary")
        );

        const nextStatus = normalizedStatus === "ACTIVE"
            ? "INACTIVE"
            : "ACTIVE";

        actions.appendChild(
            createJobActionButton(
                normalizedStatus === "ACTIVE" ? "Deactivate" : "Publish",
                "status",
                job.id,
                "secondary",
                nextStatus
            )
        );

        actions.appendChild(
            createJobActionButton(
                "Archive",
                "archive",
                job.id,
                "danger"
            )
        );

        actionsCell.appendChild(actions);
        row.appendChild(actionsCell);

        tbody.appendChild(row);
    });
}


function createEmployerCell(value) {
    const cell = document.createElement("td");
    cell.textContent = value;
    return cell;
}


function formatEmployerSalary(job) {
    const minimum = job.salary_min;
    const maximum = job.salary_max;
    const currency = job.currency || "BDT";

    if (minimum == null && maximum == null) {
        return "Not specified";
    }

    const formatter = value =>
        Number(value).toLocaleString(undefined, {
            maximumFractionDigits: 2
        });

    if (minimum != null && maximum != null) {
        return `${currency} ${formatter(minimum)} – ${formatter(maximum)}`;
    }

    if (minimum != null) {
        return `From ${currency} ${formatter(minimum)}`;
    }

    return `Up to ${currency} ${formatter(maximum)}`;
}


function createJobActionButton(
    label,
    action,
    jobId,
    variant = "secondary",
    status = ""
) {
    const button = document.createElement("button");

    button.type = "button";
    button.className = `employer-button ${variant}`;
    button.textContent = label;

    button.dataset.action = action;
    button.dataset.jobId = String(jobId);

    if (status) {
        button.dataset.status = status;
    }

    return button;
}


/* =========================================
   JOB TABLE ACTIONS
   ========================================= */

function setupJobTableActions() {
    const tbody = document.getElementById("employerJobsTableBody");

    if (!tbody) {
        return;
    }

    tbody.addEventListener("click", async event => {
        const button = event.target.closest("button[data-action]");

        if (!button) {
            return;
        }

        const action = button.dataset.action;
        const jobId = button.dataset.jobId;

        if (action === "edit") {
            editEmployerJob(jobId);
            return;
        }

        if (action === "status") {
            const nextStatus = button.dataset.status;

            const confirmMessage = nextStatus === "ACTIVE"
                ? "Publish or reactivate this job?"
                : "Deactivate this job posting?";

            if (!window.confirm(confirmMessage)) {
                return;
            }

            button.disabled = true;

            try {
                const result = await employerApiRequest(
                    `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}/status`,
                    {
                        method: "PATCH",
                        body: JSON.stringify({ status: nextStatus })
                    }
                );

                showEmployerMessage(
                    result.message || "Job status updated.",
                    "success"
                );

                await loadAllEmployerData();

            } catch (error) {
                showEmployerMessage(error.message, "error");
                button.disabled = false;
            }

            return;
        }

        if (action === "archive") {
            const confirmed = window.confirm(
                "Archive this job posting? It will be marked inactive and removed from active job recommendations."
            );

            if (!confirmed) {
                return;
            }

            button.disabled = true;

            try {
                const result = await employerApiRequest(
                    `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}`,
                    {
                        method: "DELETE"
                    }
                );

                showEmployerMessage(
                    result.message || "Job posting archived.",
                    "success"
                );

                if (
                    String(
                        document.getElementById("employerJobId").value
                    ) === String(jobId)
                ) {
                    resetEmployerJobForm();
                }

                await loadAllEmployerData();

            } catch (error) {
                showEmployerMessage(error.message, "error");
                button.disabled = false;
            }
        }
    });
}


/* =========================================
   REFRESH BUTTONS
   ========================================= */

function setupEmployerRefresh() {
    document.getElementById("refreshEmployerButton")
        ?.addEventListener("click", loadAllEmployerData);

    document.getElementById("refreshEmployerJobsButton")
        ?.addEventListener("click", loadAllEmployerData);
}


/* =========================================
   GENERAL UTILITIES
   ========================================= */

function setButtonBusy(button, busy, text) {
    if (!button) {
        return;
    }

    if (busy) {
        button.dataset.originalText = button.textContent;
        button.disabled = true;
        button.textContent = text;
    } else {
        button.disabled = false;
        button.textContent = text || button.dataset.originalText || "Save";
    }
}


function isValidHttpUrl(value) {
    try {
        const url = new URL(value);

        return url.protocol === "http:" ||
            url.protocol === "https:";
    } catch {
        return false;
    }
}