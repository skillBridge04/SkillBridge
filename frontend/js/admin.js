"use strict";

/* =========================================================
   SKILLBRIDGE ADMIN DASHBOARD
   ========================================================= */

const ADMIN_API = "/api/admin";
const CURRENT_USER_API = "/api/auth/me";

let currentAdminId = null;

let pendingEmployers = [];
let allCompanies = [];
let allJobs = [];
let allSkills = [];
let allCourses = [];
let adminAccounts = [];


/* =========================================================
   INITIALIZATION
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    setText("currentYear", String(new Date().getFullYear()));

    setupLogout();
    setupEmployerActions();
    setupCompanyManagement();
    setupJobManagement();
    setupSkillManagement();
    setupCourseManagement();
    setupAdminManagement();

    initializeAdminDashboard();
});


/* =========================================================
   SHARED HELPERS
   ========================================================= */

function getElement(id) {
    return document.getElementById(id);
}


function setText(id, value) {
    const element = getElement(id);

    if (element) {
        element.textContent = value ?? "";
    }
}


function showAdminMessage(message, type = "info") {
    const element = getElement("adminMessage");

    if (!element) {
        console.log(message);
        return;
    }

    element.textContent = message;
    element.className = `admin-message ${type}`;
    element.hidden = false;
}


function hideAdminMessage() {
    const element = getElement("adminMessage");

    if (element) {
        element.textContent = "";
        element.hidden = true;
    }
}


async function readResponse(response) {
    const text = await response.text();

    if (!text) {
        return {};
    }

    try {
        return JSON.parse(text);
    } catch {
        return { detail: text };
    }
}


function getErrorMessage(
    data,
    fallback = "Something went wrong."
) {
    const detail = data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail.map((item) => {
            const location = Array.isArray(item.loc)
                ? item.loc
                    .filter((part) => part !== "body")
                    .join(".")
                : "";

            const message = item.msg || "Invalid value";

            return location
                ? `${location}: ${message}`
                : message;
        }).join("; ");
    }

    if (detail && typeof detail === "object") {
        return JSON.stringify(detail);
    }

    return data?.message || fallback;
}


function getList(value) {
    if (Array.isArray(value)) {
        return value;
    }

    if (Array.isArray(value?.items)) {
        return value.items;
    }

    if (Array.isArray(value?.data)) {
        return value.data;
    }

    return [];
}


function normalizeStatus(value, fallback = "UNKNOWN") {
    return String(value || fallback)
        .trim()
        .toUpperCase();
}


function isActive(item) {
    return normalizeStatus(item?.status) === "ACTIVE";
}


function getAccountStatus(user) {
    return normalizeStatus(
        user?.account_status || user?.status,
        "UNKNOWN"
    );
}


function getRole(user) {
    return normalizeStatus(
        user?.role || user?.user_role,
        ""
    );
}


function createCell(value) {
    const cell = document.createElement("td");

    cell.textContent = value ?? "—";

    return cell;
}


function createTextElement(tagName, className, value) {
    const element = document.createElement(tagName);

    if (className) {
        element.className = className;
    }

    element.textContent = value ?? "";

    return element;
}


function createStatusBadge(value) {
    const label = normalizeStatus(value);

    const badge = document.createElement("span");

    badge.className =
        `admin-status ${label.toLowerCase().replace(/[^a-z0-9_-]/g, "")}`;

    badge.textContent = label;

    return badge;
}


function showTableMessage(
    tableBodyId,
    message,
    columnCount
) {
    const tbody = getElement(tableBodyId);

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();

    const row = document.createElement("tr");
    const cell = document.createElement("td");

    cell.colSpan = columnCount;
    cell.className = "admin-empty";
    cell.textContent = message;

    row.appendChild(cell);
    tbody.appendChild(row);
}


function createActionButton(
    label,
    action,
    id,
    className = "admin-small-button",
    disabled = false
) {
    const button = document.createElement("button");

    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.dataset.action = action;
    button.dataset.id = String(id);
    button.disabled = disabled;

    return button;
}


function getTableActionButton(event) {
    const target = event.target;

    if (!(target instanceof Element)) {
        return null;
    }

    return target.closest("button[data-action]");
}


/* =========================================================
   AUTHENTICATION HELPERS
   ========================================================= */

function getToken() {
    return sessionStorage.getItem("access_token");
}


function getAuthorizationHeader() {
    const token = getToken();

    const tokenType =
        sessionStorage.getItem("token_type") || "bearer";

    return token ? `${tokenType} ${token}` : null;
}


function clearSession() {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("token_type");
    sessionStorage.removeItem("resume_id");
    sessionStorage.removeItem("resume_file_name");
}


/* =========================================================
   API REQUEST HELPER
   ========================================================= */

async function apiRequest(path, options = {}) {
    const authorization = getAuthorizationHeader();

    if (!authorization) {
        clearSession();
        window.location.replace("/login");

        throw new Error("Please log in again.");
    }

    const headers = {
        Authorization: authorization,
        Accept: "application/json",
        ...(options.headers || {})
    };

    let requestBody = options.body;

    if (
        requestBody !== undefined &&
        requestBody !== null &&
        !(requestBody instanceof FormData)
    ) {
        headers["Content-Type"] = "application/json";
        requestBody = JSON.stringify(requestBody);
    }

    let response;

    try {
        response = await fetch(path, {
            method: options.method || "GET",
            headers,
            body: requestBody
        });
    } catch {
        throw new Error(
            "Could not connect to the server. Make sure FastAPI is running."
        );
    }

    const data = await readResponse(response);

    if (response.status === 401) {
        clearSession();
        window.location.replace("/login");

        throw new Error(
            "Your session has expired. Please log in again."
        );
    }

    if (!response.ok) {
        throw new Error(
            getErrorMessage(
                data,
                `Request failed with status ${response.status}.`
            )
        );
    }

    return data;
}


/* =========================================================
   AUTHENTICATE ADMIN
   ========================================================= */

async function initializeAdminDashboard() {
    if (!getToken()) {
        window.location.replace("/login");
        return;
    }

    showAdminMessage(
        "Checking administrator access...",
        "info"
    );

    try {
        const result = await apiRequest(CURRENT_USER_API);

        const user = result?.user || result?.data || result;

        if (getRole(user) !== "ADMIN") {
            showAdminMessage(
                "Access denied. This dashboard is available only to administrators.",
                "error"
            );

            window.setTimeout(() => {
                window.location.replace("/dashboard");
            }, 1800);

            return;
        }

        const accountStatus =
            user.account_status ?? user.status;

        if (
            accountStatus &&
            normalizeStatus(accountStatus) !== "ACTIVE"
        ) {
            clearSession();

            showAdminMessage(
                "Your administrator account is not active. Please contact another administrator.",
                "error"
            );

            window.setTimeout(() => {
                window.location.replace("/login");
            }, 1800);

            return;
        }

        currentAdminId = user.id ?? null;

        setText(
            "adminHeaderName",
            user.name ||
            user.full_name ||
            user.email ||
            "Admin"
        );

        await loadAllAdminData();

    } catch (error) {
        showAdminMessage(
            error.message ||
            "Could not initialize the admin dashboard.",
            "error"
        );
    }
}


/* =========================================================
   LOAD ALL ADMIN DATA
   ========================================================= */

async function loadAllAdminData() {
    /*
     * Load companies and skills before loading jobs,
     * because the job form depends on both lists.
     */

    const initialResults = await Promise.allSettled([
        loadPendingEmployers(),
        loadCompanies(),
        loadSkills(),
        loadAdmins()
    ]);

    const failures = initialResults.filter(
        (result) => result.status === "rejected"
    );

    try {
        await loadJobs();
    } catch (error) {
        failures.push({
            status: "rejected",
            reason: error
        });
    }

    try {
        await loadCourses();
    } catch (error) {
        failures.push({
            status: "rejected",
            reason: error
        });
    }

    updateSummaryCounts();

    if (failures.length > 0) {
        const errorMessages = failures
            .map((item) => item.reason?.message)
            .filter(Boolean);

        showAdminMessage(
            errorMessages[0] ||
            "Some information could not be loaded. Use Refresh to try again.",
            "error"
        );
    } else {
        hideAdminMessage();
    }
}


/* =========================================================
   LOGOUT
   ========================================================= */

function setupLogout() {
    getElement("adminLogoutButton")
        ?.addEventListener("click", () => {
            clearSession();
            window.location.replace("/login");
        });
}


/* =========================================================
   SUMMARY COUNTS
   ========================================================= */

function updateSummaryCounts() {
    setText(
        "pendingEmployerCount",
        String(pendingEmployers.length)
    );

    setText(
        "activeCompanyCount",
        String(allCompanies.filter(isActive).length)
    );

    setText(
        "activeJobCount",
        String(allJobs.filter(isActive).length)
    );

    setText(
        "activeSkillCount",
        String(allSkills.filter(isActive).length)
    );

    setText(
        "activeCourseCount",
        String(allCourses.filter(isActive).length)
    );

    setText(
        "adminAccountCount",
        String(adminAccounts.length)
    );
}


/* =========================================================
   PENDING EMPLOYER MANAGEMENT
   ========================================================= */

function setupEmployerActions() {
    getElement("refreshEmployersButton")
        ?.addEventListener("click", async () => {
            try {
                await loadPendingEmployers();

                showAdminMessage(
                    "Pending employers refreshed.",
                    "success"
                );
            } catch (error) {
                showAdminMessage(error.message, "error");
            }
        });

    getElement("pendingEmployersTableBody")
        ?.addEventListener("click", handleEmployerAction);
}


async function loadPendingEmployers() {
    showTableMessage(
        "pendingEmployersTableBody",
        "Loading pending employers...",
        5
    );

    try {
        pendingEmployers = getList(
            await apiRequest(`${ADMIN_API}/employers/pending`)
        );

        renderPendingEmployers();
        updateSummaryCounts();

    } catch (error) {
        showTableMessage(
            "pendingEmployersTableBody",
            error.message || "Could not load pending employers.",
            5
        );

        throw error;
    }
}


function renderPendingEmployers() {
    const tbody = getElement("pendingEmployersTableBody");

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();

    if (!pendingEmployers.length) {
        showTableMessage(
            "pendingEmployersTableBody",
            "There are no employers awaiting approval.",
            5
        );

        return;
    }

    pendingEmployers.forEach((employer) => {
        const row = document.createElement("tr");

        const statusCell = document.createElement("td");

        statusCell.appendChild(
            createStatusBadge(
                employer.account_status ||
                employer.status ||
                "PENDING"
            )
        );

        const actionsCell = document.createElement("td");
        const actions = document.createElement("div");

        actions.className = "admin-table-actions";

        actions.appendChild(
            createActionButton(
                "Approve",
                "approve-employer",
                employer.id
            )
        );

        actions.appendChild(
            createActionButton(
                "Reject",
                "reject-employer",
                employer.id,
                "admin-danger-button"
            )
        );

        actionsCell.appendChild(actions);

        row.append(
            createCell(employer.id),
            createCell(employer.name || "Name not provided"),
            createCell(employer.email || "Email not provided"),
            statusCell,
            actionsCell
        );

        tbody.appendChild(row);
    });
}


async function handleEmployerAction(event) {
    const button = getTableActionButton(event);

    if (!button || button.disabled) {
        return;
    }

    const { action, id } = button.dataset;

    const isApprove = action === "approve-employer";
    const isReject = action === "reject-employer";

    if (!id || (!isApprove && !isReject)) {
        return;
    }

    const employer = pendingEmployers.find(
        (item) => String(item.id) === String(id)
    );

    if (!employer) {
        return;
    }

    const actionLabel = isApprove ? "approve" : "reject";

    if (!window.confirm(
        `Are you sure you want to ${actionLabel} ${employer.name || employer.email || "this employer"}?`
    )) {
        return;
    }

    button.disabled = true;

    try {
        await apiRequest(
            `${ADMIN_API}/employers/${encodeURIComponent(id)}/${isApprove ? "approve" : "reject"}`,
            { method: "PATCH" }
        );

        await loadPendingEmployers();

        showAdminMessage(
            isApprove
                ? "Employer approved successfully."
                : "Employer rejected successfully.",
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not update the employer account.",
            "error"
        );

        button.disabled = false;
    }
}


/* =========================================================
   COMPANY MANAGEMENT
   ========================================================= */

function setupCompanyManagement() {
    getElement("companyForm")
        ?.addEventListener("submit", saveCompany);

    getElement("cancelCompanyEditButton")
        ?.addEventListener("click", resetCompanyForm);

    getElement("refreshCompaniesButton")
        ?.addEventListener("click", async () => {
            try {
                await loadCompanies();

                showAdminMessage(
                    "Companies refreshed.",
                    "success"
                );
            } catch (error) {
                showAdminMessage(error.message, "error");
            }
        });

    getElement("includeInactiveCompanies")
        ?.addEventListener("change", renderCompanies);

    getElement("companiesTableBody")
        ?.addEventListener("click", handleCompanyAction);
}


async function loadCompanies() {
    showTableMessage(
        "companiesTableBody",
        "Loading companies...",
        6
    );

    try {
        allCompanies = getList(
            await apiRequest(
                `${ADMIN_API}/companies?include_inactive=true`
            )
        );

        renderCompanies();
        populateCompanySelect();
        updateSummaryCounts();

    } catch (error) {
        showTableMessage(
            "companiesTableBody",
            error.message || "Could not load companies.",
            6
        );

        throw error;
    }
}


function renderCompanies() {
    const tbody = getElement("companiesTableBody");

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();

    const includeInactive =
        Boolean(getElement("includeInactiveCompanies")?.checked);

    const visibleCompanies = allCompanies.filter(
        (company) => includeInactive || isActive(company)
    );

    if (!visibleCompanies.length) {
        showTableMessage(
            "companiesTableBody",
            "No companies found. Add a company using the form above.",
            6
        );

        return;
    }

    visibleCompanies.forEach((company) => {
        const row = document.createElement("tr");
        const statusCell = document.createElement("td");

        statusCell.appendChild(
            createStatusBadge(company.status)
        );

        const actionsCell = document.createElement("td");
        const actions = document.createElement("div");

        actions.className = "admin-table-actions";

        actions.appendChild(
            createActionButton("Edit", "edit-company", company.id)
        );

        actions.appendChild(
            createActionButton(
                isActive(company) ? "Deactivate" : "Activate",
                "toggle-company",
                company.id,
                isActive(company)
                    ? "admin-danger-button"
                    : "admin-small-button"
            )
        );

        actionsCell.appendChild(actions);

        row.append(
            createCell(company.id),
            createCell(company.name),
            createCell(company.industry || "—"),
            createCell(company.location || "—"),
            statusCell,
            actionsCell
        );

        tbody.appendChild(row);
    });
}


function resetCompanyForm() {
    getElement("companyForm")?.reset();

    if (getElement("companyId")) {
        getElement("companyId").value = "";
    }

    setText("saveCompanyButton", "Add Company");

    const cancel = getElement("cancelCompanyEditButton");

    if (cancel) {
        cancel.hidden = true;
    }
}


function startCompanyEdit(company) {
    const fields = {
        companyId: company.id,
        companyName: company.name || "",
        companyIndustry: company.industry || "",
        companyLocation: company.location || "",
        companyWebsite: company.website || "",
        companyDescription: company.description || ""
    };

    for (const [id, value] of Object.entries(fields)) {
        const element = getElement(id);

        if (element) {
            element.value = String(value);
        }
    }

    setText("saveCompanyButton", "Update Company");

    const cancel = getElement("cancelCompanyEditButton");

    if (cancel) {
        cancel.hidden = false;
    }

    getElement("companyManagement")?.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


async function saveCompany(event) {
    event.preventDefault();

    const id = getElement("companyId")?.value.trim() || "";
    const name = getElement("companyName")?.value.trim() || "";
    const industry = getElement("companyIndustry")?.value.trim() || "";
    const location = getElement("companyLocation")?.value.trim() || "";
    const website = getElement("companyWebsite")?.value.trim() || "";
    const description = getElement("companyDescription")?.value.trim() || "";

    if (name.length < 2) {
        showAdminMessage(
            "Company name must contain at least two characters.",
            "error"
        );

        return;
    }

    if (website) {
        try {
            const parsed = new URL(website);

            if (!["http:", "https:"].includes(parsed.protocol)) {
                throw new Error();
            }
        } catch {
            showAdminMessage(
                "Enter a valid company website beginning with http:// or https://.",
                "error"
            );

            return;
        }
    }

    const payload = {
        name,
        industry: industry || null,
        location: location || null,
        website: website || null,
        description: description || null
    };

    const button = getElement("saveCompanyButton");

    if (!button) {
        return;
    }

    button.disabled = true;
    button.textContent = "Saving...";

    try {
        if (id) {
            await apiRequest(
                `${ADMIN_API}/companies/${encodeURIComponent(id)}`,
                {
                    method: "PATCH",
                    body: payload
                }
            );
        } else {
            await apiRequest(
                `${ADMIN_API}/companies`,
                {
                    method: "POST",
                    body: payload
                }
            );
        }

        resetCompanyForm();

        await loadCompanies();
        await loadJobs();

        showAdminMessage(
            id ? "Company updated successfully." : "Company added successfully.",
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not save the company.",
            "error"
        );
    } finally {
        button.disabled = false;
        button.textContent = "Add Company";
    }
}


async function handleCompanyAction(event) {
    const button = getTableActionButton(event);

    if (!button || button.disabled) {
        return;
    }

    const { action, id } = button.dataset;

    const company = allCompanies.find(
        (item) => String(item.id) === String(id)
    );

    if (!company) {
        return;
    }

    if (action === "edit-company") {
        startCompanyEdit(company);
        return;
    }

    if (action !== "toggle-company") {
        return;
    }

    const nextStatus = isActive(company)
        ? "INACTIVE"
        : "ACTIVE";

    if (!window.confirm(
        `${nextStatus === "ACTIVE" ? "Activate" : "Deactivate"} ${company.name}?`
    )) {
        return;
    }

    button.disabled = true;

    try {
        await apiRequest(
            `${ADMIN_API}/companies/${encodeURIComponent(id)}`,
            {
                method: "PATCH",
                body: { status: nextStatus }
            }
        );

        await loadCompanies();
        await loadJobs();

        showAdminMessage(
            `Company ${nextStatus.toLowerCase()} successfully.`,
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not update the company.",
            "error"
        );

        button.disabled = false;
    }
}


/* =========================================================
   SKILL MANAGEMENT
   ========================================================= */

function setupSkillManagement() {
    getElement("refreshSkillsButton")
        ?.addEventListener("click", async () => {
            try {
                await loadSkills();

                showAdminMessage("Skills refreshed.", "success");
            } catch (error) {
                showAdminMessage(error.message, "error");
            }
        });

    getElement("includeInactiveSkills")
        ?.addEventListener("change", renderSkills);

    getElement("skillForm")
        ?.addEventListener("submit", saveSkill);

    getElement("cancelSkillEditButton")
        ?.addEventListener("click", resetSkillForm);

    getElement("skillsTableBody")
        ?.addEventListener("click", handleSkillTableAction);
}


async function loadSkills() {
    showTableMessage("skillsTableBody", "Loading skills...", 5);

    try {
        allSkills = getList(
            await apiRequest(
                `${ADMIN_API}/skills?include_inactive=true`
            )
        );

        renderSkills();
        populateCourseSkillSelect();
        renderJobSkillChoices();

        updateSummaryCounts();

    } catch (error) {
        showTableMessage(
            "skillsTableBody",
            error.message || "Could not load skills.",
            5
        );

        throw error;
    }
}


function renderSkills() {
    const tbody = getElement("skillsTableBody");

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();

    const includeInactive =
        Boolean(getElement("includeInactiveSkills")?.checked);

    const visibleSkills = allSkills.filter(
        (skill) => includeInactive || isActive(skill)
    );

    if (!visibleSkills.length) {
        showTableMessage(
            "skillsTableBody",
            "No skills match this filter. Add a skill above.",
            5
        );

        return;
    }

    visibleSkills.forEach((skill) => {
        const row = document.createElement("tr");
        const statusCell = document.createElement("td");

        statusCell.appendChild(
            createStatusBadge(skill.status)
        );

        const actionsCell = document.createElement("td");
        const actions = document.createElement("div");

        actions.className = "admin-table-actions";

        actions.appendChild(
            createActionButton("Edit", "edit-skill", skill.id)
        );

        actions.appendChild(
            createActionButton(
                isActive(skill) ? "Deactivate" : "Activate",
                "toggle-skill",
                skill.id,
                isActive(skill)
                    ? "admin-danger-button"
                    : "admin-small-button"
            )
        );

        actionsCell.appendChild(actions);

        row.append(
            createCell(skill.id),
            createCell(skill.name),
            createCell(skill.category || "—"),
            statusCell,
            actionsCell
        );

        tbody.appendChild(row);
    });
}


function resetSkillForm() {
    getElement("skillForm")?.reset();

    if (getElement("skillId")) {
        getElement("skillId").value = "";
    }

    setText("saveSkillButton", "Add Skill");

    const cancel = getElement("cancelSkillEditButton");

    if (cancel) {
        cancel.hidden = true;
    }
}


function startSkillEdit(skill) {
    const id = getElement("skillId");
    const name = getElement("skillName");
    const category = getElement("skillCategory");

    if (!id || !name || !category) {
        showAdminMessage(
            "The skill edit form is missing a required field.",
            "error"
        );

        return;
    }

    id.value = String(skill.id);
    name.value = skill.name || "";
    category.value = skill.category || "";

    setText("saveSkillButton", "Update Skill");

    const cancel = getElement("cancelSkillEditButton");

    if (cancel) {
        cancel.hidden = false;
    }

    getElement("skillsManagement")?.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


async function saveSkill(event) {
    event.preventDefault();

    const id = getElement("skillId")?.value.trim() || "";
    const name = getElement("skillName")?.value.trim() || "";
    const category = getElement("skillCategory")?.value.trim() || "";

    if (!name) {
        showAdminMessage("Please enter a skill name.", "error");
        return;
    }

    const payload = {
        name,
        category: category || null
    };

    const button = getElement("saveSkillButton");

    if (!button) {
        return;
    }

    button.disabled = true;
    button.textContent = "Saving...";

    try {
        await apiRequest(
            id
                ? `${ADMIN_API}/skills/${encodeURIComponent(id)}`
                : `${ADMIN_API}/skills`,
            {
                method: id ? "PATCH" : "POST",
                body: payload
            }
        );

        resetSkillForm();

        await loadSkills();
        await loadCourses();
        await loadJobs();

        showAdminMessage(
            id ? "Skill updated successfully." : "Skill added successfully.",
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not save the skill.",
            "error"
        );
    } finally {
        button.disabled = false;
        button.textContent = "Add Skill";
    }
}


async function handleSkillTableAction(event) {
    const button = getTableActionButton(event);

    if (!button || button.disabled) {
        return;
    }

    const { action, id } = button.dataset;

    const skill = allSkills.find(
        (item) => String(item.id) === String(id)
    );

    if (!skill) {
        return;
    }

    if (action === "edit-skill") {
        startSkillEdit(skill);
        return;
    }

    if (action !== "toggle-skill") {
        return;
    }

    const nextStatus = isActive(skill)
        ? "INACTIVE"
        : "ACTIVE";

    if (!window.confirm(
        `${nextStatus === "ACTIVE" ? "Activate" : "Deactivate"} the skill "${skill.name}"?`
    )) {
        return;
    }

    button.disabled = true;

    try {
        await apiRequest(
            `${ADMIN_API}/skills/${encodeURIComponent(id)}`,
            {
                method: "PATCH",
                body: { status: nextStatus }
            }
        );

        await loadSkills();
        await loadCourses();
        await loadJobs();

        showAdminMessage(
            `Skill ${nextStatus.toLowerCase()} successfully.`,
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not update the skill.",
            "error"
        );

        button.disabled = false;
    }
}


/* =========================================================
   JOB MANAGEMENT
   ========================================================= */

function setupJobManagement() {
    getElement("refreshJobsButton")
        ?.addEventListener("click", async () => {
            try {
                await loadJobs();

                showAdminMessage("Jobs refreshed.", "success");
            } catch (error) {
                showAdminMessage(error.message, "error");
            }
        });

    getElement("includeInactiveJobs")
        ?.addEventListener("change", renderJobs);

    getElement("jobForm")
        ?.addEventListener("submit", saveJob);

    getElement("cancelJobEditButton")
        ?.addEventListener("click", resetJobForm);

    getElement("jobsTableBody")
        ?.addEventListener("click", handleJobAction);
}


function populateCompanySelect() {
    const select = getElement("jobCompanyId");

    if (!select) {
        return;
    }

    const previousValue = select.value;

    select.replaceChildren();

    const placeholder = document.createElement("option");

    placeholder.value = "";
    placeholder.textContent = "Select an active company";

    select.appendChild(placeholder);

    allCompanies
        .filter(isActive)
        .sort((a, b) =>
            String(a.name || "").localeCompare(String(b.name || ""))
        )
        .forEach((company) => {
            const option = document.createElement("option");

            option.value = String(company.id);
            option.textContent = company.name || `Company #${company.id}`;

            select.appendChild(option);
        });

    if (
        previousValue &&
        Array.from(select.options).some(
            (option) => option.value === previousValue
        )
    ) {
        select.value = previousValue;
    }
}


function renderJobSkillChoices(selectedIds = []) {
    const container = getElement("jobRequiredSkills");

    if (!container) {
        return;
    }

    container.replaceChildren();

    const selected = new Set(
        selectedIds.map((id) => String(id))
    );

    const activeSkills = allSkills
        .filter(isActive)
        .sort((a, b) =>
            String(a.name || "").localeCompare(String(b.name || ""))
        );

    if (!activeSkills.length) {
        container.appendChild(
            createTextElement(
                "p",
                "admin-help-text",
                "Add and activate skills before creating jobs."
            )
        );

        return;
    }

    activeSkills.forEach((skill) => {
        const label = document.createElement("label");

        label.className = "admin-checkbox-row";

        const checkbox = document.createElement("input");

        checkbox.type = "checkbox";
        checkbox.name = "required_skill_ids";
        checkbox.value = String(skill.id);
        checkbox.checked = selected.has(String(skill.id));

        label.appendChild(checkbox);
        label.appendChild(
            document.createTextNode(` ${skill.name}`)
        );

        container.appendChild(label);
    });
}


function getSelectedJobSkillIds() {
    return Array.from(
        document.querySelectorAll(
            '#jobRequiredSkills input[name="required_skill_ids"]:checked'
        )
    ).map((input) => Number(input.value));
}


async function loadJobs() {
    populateCompanySelect();
    renderJobSkillChoices();

    showTableMessage("jobsTableBody", "Loading jobs...", 7);

    try {
        allJobs = getList(
            await apiRequest(
                `${ADMIN_API}/jobs?include_inactive=true`
            )
        );

        renderJobs();
        updateSummaryCounts();

    } catch (error) {
        showTableMessage(
            "jobsTableBody",
            error.message || "Could not load jobs.",
            7
        );

        throw error;
    }
}


function renderJobs() {
    const tbody = getElement("jobsTableBody");

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();

    const includeInactive =
        Boolean(getElement("includeInactiveJobs")?.checked);

    const visibleJobs = allJobs.filter(
        (job) => includeInactive || isActive(job)
    );

    if (!visibleJobs.length) {
        showTableMessage(
            "jobsTableBody",
            "No jobs found. Add a job using the form above.",
            7
        );

        return;
    }

    visibleJobs.forEach((job) => {
        const row = document.createElement("tr");

        const skills = Array.isArray(job.required_skills)
            ? job.required_skills.map((skill) => skill.name).filter(Boolean)
            : [];

        const statusCell = document.createElement("td");

        statusCell.appendChild(
            createStatusBadge(job.status)
        );

        const actionsCell = document.createElement("td");
        const actions = document.createElement("div");

        actions.className = "admin-table-actions";

        actions.appendChild(
            createActionButton("Edit", "edit-job", job.id)
        );

        actions.appendChild(
            createActionButton(
                isActive(job) ? "Deactivate" : "Activate",
                "toggle-job",
                job.id,
                isActive(job)
                    ? "admin-danger-button"
                    : "admin-small-button"
            )
        );

        actionsCell.appendChild(actions);

        row.append(
            createCell(job.id),
            createCell(job.title),
            createCell(job.company_name || "—"),
            createCell(job.location || "—"),
            createCell(skills.join(", ") || "No active skills"),
            statusCell,
            actionsCell
        );

        tbody.appendChild(row);
    });
}


function resetJobForm() {
    getElement("jobForm")?.reset();

    if (getElement("jobId")) {
        getElement("jobId").value = "";
    }

    setText("saveJobButton", "Add Job");

    const cancel = getElement("cancelJobEditButton");

    if (cancel) {
        cancel.hidden = true;
    }

    populateCompanySelect();
    renderJobSkillChoices();
}


function startJobEdit(job) {
    const fields = {
        jobId: job.id,
        jobTitle: job.title || "",
        jobLocation: job.location || "",
        jobEmploymentType: job.employment_type || "",
        jobSalaryMin: job.salary_min ?? "",
        jobSalaryMax: job.salary_max ?? "",
        jobCurrency: job.currency || "BDT",
        jobExperienceRequired: job.experience_required || "",
        jobEducationRequired: job.education_required || "",
        jobApplicationUrl: job.application_url || "",
        jobDescription: job.description || ""
    };

    for (const [id, value] of Object.entries(fields)) {
        const element = getElement(id);

        if (element) {
            element.value = String(value);
        }
    }

    populateCompanySelect();

    const companySelect = getElement("jobCompanyId");

    if (companySelect) {
        companySelect.value = String(job.company_id);
    }

    const selectedSkillIds = (job.required_skills || [])
        .filter((skill) => skill.is_required)
        .map((skill) => skill.skill_id);

    renderJobSkillChoices(selectedSkillIds);

    setText("saveJobButton", "Update Job");

    const cancel = getElement("cancelJobEditButton");

    if (cancel) {
        cancel.hidden = false;
    }

    getElement("jobManagement")?.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


async function saveJob(event) {
    event.preventDefault();

    const id = getElement("jobId")?.value.trim() || "";
    const title = getElement("jobTitle")?.value.trim() || "";
    const companyId = getElement("jobCompanyId")?.value || "";
    const selectedSkillIds = getSelectedJobSkillIds();

    if (!title || !companyId || selectedSkillIds.length === 0) {
        showAdminMessage(
            "Enter a job title, select a company, and select at least one required skill.",
            "error"
        );

        return;
    }

    const selectedCompany = allCompanies.find(
        (company) => String(company.id) === String(companyId)
    );

    if (!selectedCompany || !isActive(selectedCompany)) {
        showAdminMessage(
            "Select an active company for this job.",
            "error"
        );

        return;
    }

    const numberOrNull = (fieldId) => {
        const value = getElement(fieldId)?.value.trim() || "";

        return value === "" ? null : Number(value);
    };

    const salaryMin = numberOrNull("jobSalaryMin");
    const salaryMax = numberOrNull("jobSalaryMax");

    if (
        (salaryMin !== null && salaryMin < 0) ||
        (salaryMax !== null && salaryMax < 0)
    ) {
        showAdminMessage(
            "Salary values cannot be negative.",
            "error"
        );

        return;
    }

    if (
        salaryMin !== null &&
        salaryMax !== null &&
        salaryMin > salaryMax
    ) {
        showAdminMessage(
            "Minimum salary cannot be greater than maximum salary.",
            "error"
        );

        return;
    }

    const payload = {
        company_id: Number(companyId),
        title,
        location:
            getElement("jobLocation")?.value.trim() || null,
        employment_type:
            getElement("jobEmploymentType")?.value.trim() || null,
        salary_min: salaryMin,
        salary_max: salaryMax,
        currency:
            getElement("jobCurrency")?.value.trim() || "BDT",
        experience_required:
            getElement("jobExperienceRequired")?.value.trim() || null,
        education_required:
            getElement("jobEducationRequired")?.value.trim() || null,
        application_url:
            getElement("jobApplicationUrl")?.value.trim() || null,
        description:
            getElement("jobDescription")?.value.trim() || null,
        required_skill_ids: selectedSkillIds
    };

    const applicationUrl = payload.application_url;

    if (applicationUrl) {
        try {
            const parsed = new URL(applicationUrl);

            if (!["http:", "https:"].includes(parsed.protocol)) {
                throw new Error();
            }
        } catch {
            showAdminMessage(
                "Enter a valid application URL beginning with http:// or https://.",
                "error"
            );

            return;
        }
    }

    const button = getElement("saveJobButton");

    if (!button) {
        return;
    }

    button.disabled = true;
    button.textContent = "Saving...";

    try {
        await apiRequest(
            id
                ? `${ADMIN_API}/jobs/${encodeURIComponent(id)}`
                : `${ADMIN_API}/jobs`,
            {
                method: id ? "PATCH" : "POST",
                body: payload
            }
        );

        resetJobForm();

        await loadJobs();

        showAdminMessage(
            id ? "Job updated successfully." : "Job created successfully.",
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not save the job.",
            "error"
        );
    } finally {
        button.disabled = false;
        button.textContent = "Add Job";
    }
}


async function handleJobAction(event) {
    const button = getTableActionButton(event);

    if (!button || button.disabled) {
        return;
    }

    const { action, id } = button.dataset;

    const job = allJobs.find(
        (item) => String(item.id) === String(id)
    );

    if (!job) {
        return;
    }

    if (action === "edit-job") {
        startJobEdit(job);
        return;
    }

    if (action !== "toggle-job") {
        return;
    }

    const nextStatus = isActive(job)
        ? "INACTIVE"
        : "ACTIVE";

    if (nextStatus === "ACTIVE") {
        const company = allCompanies.find(
            (item) => String(item.id) === String(job.company_id)
        );

        if (!company || !isActive(company)) {
            showAdminMessage(
                "Activate the company before activating this job.",
                "error"
            );

            return;
        }

        const skillIds = (job.required_skills || [])
            .filter((skill) => skill.is_required)
            .map((skill) => String(skill.skill_id));

        const allSkillsActive = skillIds.every((skillId) =>
            allSkills.some(
                (skill) =>
                    String(skill.id) === skillId &&
                    isActive(skill)
            )
        );

        if (!skillIds.length || !allSkillsActive) {
            showAdminMessage(
                "This job needs at least one active required skill before activation.",
                "error"
            );

            return;
        }
    }

    if (!window.confirm(
        `${nextStatus === "ACTIVE" ? "Activate" : "Deactivate"} "${job.title}"?`
    )) {
        return;
    }

    button.disabled = true;

    try {
        await apiRequest(
            `${ADMIN_API}/jobs/${encodeURIComponent(id)}`,
            {
                method: "PATCH",
                body: { status: nextStatus }
            }
        );

        await loadJobs();

        showAdminMessage(
            `Job ${nextStatus.toLowerCase()} successfully.`,
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not update the job.",
            "error"
        );

        button.disabled = false;
    }
}


/* =========================================================
   COURSE MANAGEMENT
   ========================================================= */

function setupCourseManagement() {
    getElement("refreshCoursesButton")
        ?.addEventListener("click", async () => {
            try {
                await loadCourses();

                showAdminMessage("Courses refreshed.", "success");
            } catch (error) {
                showAdminMessage(error.message, "error");
            }
        });

    getElement("includeInactiveCourses")
        ?.addEventListener("change", renderCourses);

    getElement("courseForm")
        ?.addEventListener("submit", saveCourse);

    getElement("cancelCourseEditButton")
        ?.addEventListener("click", resetCourseForm);

    getElement("coursesTableBody")
        ?.addEventListener("click", handleCourseTableAction);
}


function populateCourseSkillSelect() {
    const select = getElement("courseSkillId");

    if (!select) {
        return;
    }

    const previousValue = select.value;

    select.replaceChildren();

    const placeholder = document.createElement("option");

    placeholder.value = "";
    placeholder.textContent = "Select an active skill";

    select.appendChild(placeholder);

    allSkills
        .filter(isActive)
        .sort((a, b) =>
            String(a.name || "").localeCompare(String(b.name || ""))
        )
        .forEach((skill) => {
            const option = document.createElement("option");

            option.value = String(skill.id);
            option.textContent = skill.name || `Skill #${skill.id}`;

            select.appendChild(option);
        });

    if (
        previousValue &&
        Array.from(select.options).some(
            (option) => option.value === previousValue
        )
    ) {
        select.value = previousValue;
    }
}


function getSkillNameById(skillId) {
    const skill = allSkills.find(
        (item) => String(item.id) === String(skillId)
    );

    if (!skill) {
        return `Skill #${skillId ?? "unknown"}`;
    }

    return isActive(skill)
        ? skill.name
        : `${skill.name} (inactive)`;
}


async function loadCourses() {
    showTableMessage(
        "coursesTableBody",
        "Loading courses...",
        7
    );

    try {
        allCourses = getList(
            await apiRequest(
                `${ADMIN_API}/courses?include_inactive=true`
            )
        );

        renderCourses();
        updateSummaryCounts();

    } catch (error) {
        showTableMessage(
            "coursesTableBody",
            error.message || "Could not load courses.",
            7
        );

        throw error;
    }
}


function renderCourses() {
    const tbody = getElement("coursesTableBody");

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();

    const includeInactive =
        Boolean(getElement("includeInactiveCourses")?.checked);

    const visibleCourses = allCourses.filter(
        (course) => includeInactive || isActive(course)
    );

    if (!visibleCourses.length) {
        showTableMessage(
            "coursesTableBody",
            "No courses match this filter. Add a course above.",
            7
        );

        return;
    }

    visibleCourses.forEach((course) => {
        const row = document.createElement("tr");

        const statusCell = document.createElement("td");

        statusCell.appendChild(
            createStatusBadge(course.status)
        );

        const actionsCell = document.createElement("td");
        const actions = document.createElement("div");

        actions.className = "admin-table-actions";

        actions.appendChild(
            createActionButton("Edit", "edit-course", course.id)
        );

        actions.appendChild(
            createActionButton(
                isActive(course) ? "Deactivate" : "Activate",
                "toggle-course",
                course.id,
                isActive(course)
                    ? "admin-danger-button"
                    : "admin-small-button"
            )
        );

        actionsCell.appendChild(actions);

        row.append(
            createCell(course.id),
            createCell(course.title || "Untitled course"),
            createCell(course.provider || "—"),
            createCell(getSkillNameById(course.skill_id)),
            createCell(course.is_free ? "Free" : "Paid"),
            statusCell,
            actionsCell
        );

        tbody.appendChild(row);
    });
}


function resetCourseForm() {
    getElement("courseForm")?.reset();

    if (getElement("courseId")) {
        getElement("courseId").value = "";
    }

    setText("saveCourseButton", "Add Course");

    const cancel = getElement("cancelCourseEditButton");

    if (cancel) {
        cancel.hidden = true;
    }

    populateCourseSkillSelect();
}


function startCourseEdit(course) {
    const skill = allSkills.find(
        (item) => String(item.id) === String(course.skill_id)
    );

    if (!skill || !isActive(skill)) {
        showAdminMessage(
            "This course is linked to an inactive or missing skill. Activate the skill before editing this course.",
            "error"
        );

        return;
    }

    const fields = {
        courseId: course.id,
        courseTitle: course.title || "",
        courseProvider: course.provider || "",
        courseLevel: course.level || "",
        courseDuration: course.duration || "",
        courseUrl: course.url || "",
        courseDescription: course.description || ""
    };

    for (const [id, value] of Object.entries(fields)) {
        const element = getElement(id);

        if (element) {
            element.value = String(value);
        }
    }

    populateCourseSkillSelect();

    const skillSelect = getElement("courseSkillId");

    if (skillSelect) {
        skillSelect.value = String(course.skill_id);
    }

    const freeCheckbox = getElement("courseIsFree");

    if (freeCheckbox) {
        freeCheckbox.checked = Boolean(course.is_free);
    }

    setText("saveCourseButton", "Update Course");

    const cancel = getElement("cancelCourseEditButton");

    if (cancel) {
        cancel.hidden = false;
    }

    getElement("coursesManagement")?.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


async function saveCourse(event) {
    event.preventDefault();

    const id = getElement("courseId")?.value.trim() || "";
    const title = getElement("courseTitle")?.value.trim() || "";
    const provider = getElement("courseProvider")?.value.trim() || "";
    const skillId = getElement("courseSkillId")?.value || "";
    const level = getElement("courseLevel")?.value.trim() || "";
    const duration = getElement("courseDuration")?.value.trim() || "";
    const url = getElement("courseUrl")?.value.trim() || "";

    const isFree = Boolean(getElement("courseIsFree")?.checked);

    const description =
        getElement("courseDescription")?.value.trim() || "";

    if (!title || !provider || !skillId || !url) {
        showAdminMessage(
            "Please fill in the course title, provider, skill, and URL.",
            "error"
        );

        return;
    }

    let parsedUrl;

    try {
        parsedUrl = new URL(url);
    } catch {
        showAdminMessage(
            "Please enter a valid course URL.",
            "error"
        );

        return;
    }

    if (!["http:", "https:"].includes(parsedUrl.protocol)) {
        showAdminMessage(
            "Course URLs must use HTTP or HTTPS.",
            "error"
        );

        return;
    }

    const payload = {
        title,
        provider,
        skill_id: Number(skillId),
        level: level || null,
        duration: duration || null,
        url,
        is_free: isFree,
        description: description || null
    };

    const button = getElement("saveCourseButton");

    if (!button) {
        return;
    }

    button.disabled = true;
    button.textContent = "Saving...";

    try {
        await apiRequest(
            id
                ? `${ADMIN_API}/courses/${encodeURIComponent(id)}`
                : `${ADMIN_API}/courses`,
            {
                method: id ? "PATCH" : "POST",
                body: payload
            }
        );

        resetCourseForm();

        await loadCourses();

        showAdminMessage(
            id ? "Course updated successfully." : "Course added successfully.",
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not save the course.",
            "error"
        );

    } finally {
        button.disabled = false;
        button.textContent = "Add Course";
    }
}


async function handleCourseTableAction(event) {
    const button = getTableActionButton(event);

    if (!button || button.disabled) {
        return;
    }

    const { action, id } = button.dataset;

    const course = allCourses.find(
        (item) => String(item.id) === String(id)
    );

    if (!course) {
        return;
    }

    if (action === "edit-course") {
        startCourseEdit(course);
        return;
    }

    if (action !== "toggle-course") {
        return;
    }

    const nextStatus = isActive(course)
        ? "INACTIVE"
        : "ACTIVE";

    if (nextStatus === "ACTIVE") {
        const linkedSkill = allSkills.find(
            (skill) =>
                String(skill.id) === String(course.skill_id)
        );

        if (!linkedSkill || !isActive(linkedSkill)) {
            showAdminMessage(
                "Activate the course's linked skill before activating this course.",
                "error"
            );

            return;
        }
    }

    if (!window.confirm(
        `${nextStatus === "ACTIVE" ? "Activate" : "Deactivate"} the course "${course.title}"?`
    )) {
        return;
    }

    button.disabled = true;

    try {
        await apiRequest(
            `${ADMIN_API}/courses/${encodeURIComponent(id)}`,
            {
                method: "PATCH",
                body: { status: nextStatus }
            }
        );

        await loadCourses();

        showAdminMessage(
            `Course ${nextStatus.toLowerCase()} successfully.`,
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not update the course.",
            "error"
        );

        button.disabled = false;
    }
}


/* =========================================================
   ADMIN ACCOUNT MANAGEMENT
   ========================================================= */

function setupAdminManagement() {
    getElement("refreshAdminsButton")
        ?.addEventListener("click", async () => {
            try {
                await loadAdmins();

                showAdminMessage(
                    "Admin accounts refreshed.",
                    "success"
                );
            } catch (error) {
                showAdminMessage(error.message, "error");
            }
        });

    getElement("adminCreateForm")
        ?.addEventListener("submit", createAdminAccount);

    getElement("adminsTableBody")
        ?.addEventListener("click", handleAdminTableAction);
}


async function loadAdmins() {
    showTableMessage(
        "adminsTableBody",
        "Loading administrators...",
        5
    );

    try {
        adminAccounts = getList(
            await apiRequest(`${ADMIN_API}/admins`)
        );

        renderAdmins();
        updateSummaryCounts();

    } catch (error) {
        showTableMessage(
            "adminsTableBody",
            error.message || "Could not load admin accounts.",
            5
        );

        throw error;
    }
}


function renderAdmins() {
    const tbody = getElement("adminsTableBody");

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();

    if (!adminAccounts.length) {
        showTableMessage(
            "adminsTableBody",
            "No admin accounts were returned.",
            5
        );

        return;
    }

    adminAccounts.forEach((admin) => {
        const row = document.createElement("tr");

        const accountStatus = getAccountStatus(admin);

        const statusCell = document.createElement("td");

        statusCell.appendChild(
            createStatusBadge(accountStatus)
        );

        const actionsCell = document.createElement("td");
        const actions = document.createElement("div");

        actions.className = "admin-table-actions";

        const isCurrentAdmin =
            currentAdminId !== null &&
            String(admin.id) === String(currentAdminId);

        const currentlyActive = accountStatus === "ACTIVE";

        actions.appendChild(
            createActionButton(
                currentlyActive ? "Deactivate" : "Activate",
                currentlyActive ? "deactivate-admin" : "activate-admin",
                admin.id,
                currentlyActive
                    ? "admin-danger-button"
                    : "admin-small-button",
                isCurrentAdmin && currentlyActive
            )
        );

        actionsCell.appendChild(actions);

        row.append(
            createCell(admin.id),
            createCell(admin.name || "—"),
            createCell(admin.email || "—"),
            statusCell,
            actionsCell
        );

        tbody.appendChild(row);
    });
}


async function createAdminAccount(event) {
    event.preventDefault();

    const name = getElement("newAdminName")?.value.trim() || "";
    const email = getElement("newAdminEmail")?.value.trim() || "";
    const password = getElement("newAdminPassword")?.value || "";

    if (name.length < 2 || !email || password.length < 8) {
        showAdminMessage(
            "Enter a name, valid email, and password with at least 8 characters.",
            "error"
        );

        return;
    }

    const button = getElement("createAdminButton");

    if (!button) {
        return;
    }

    button.disabled = true;
    button.textContent = "Creating...";

    try {
        await apiRequest(`${ADMIN_API}/admins`, {
            method: "POST",
            body: {
                name,
                email,
                password
            }
        });

        getElement("adminCreateForm")?.reset();

        await loadAdmins();

        showAdminMessage(
            "Admin account created successfully.",
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not create the admin account.",
            "error"
        );

    } finally {
        button.disabled = false;
        button.textContent = "Create Admin";
    }
}


async function handleAdminTableAction(event) {
    const button = getTableActionButton(event);

    if (!button || button.disabled) {
        return;
    }

    const { action, id } = button.dataset;

    if (
        action !== "activate-admin" &&
        action !== "deactivate-admin"
    ) {
        return;
    }

    const admin = adminAccounts.find(
        (item) => String(item.id) === String(id)
    );

    if (!admin) {
        return;
    }

    if (
        action === "deactivate-admin" &&
        currentAdminId !== null &&
        String(id) === String(currentAdminId)
    ) {
        showAdminMessage(
            "You cannot deactivate your own admin account.",
            "error"
        );

        return;
    }

    const activate = action === "activate-admin";

    if (!window.confirm(
        `${activate ? "Activate" : "Deactivate"} admin account ${admin.email || admin.id}?`
    )) {
        return;
    }

    button.disabled = true;

    try {
        await apiRequest(
            `${ADMIN_API}/admins/${encodeURIComponent(id)}/${activate ? "activate" : "deactivate"}`,
            {
                method: "PATCH"
            }
        );

        await loadAdmins();

        showAdminMessage(
            `Admin account ${activate ? "activated" : "deactivated"} successfully.`,
            "success"
        );

    } catch (error) {
        showAdminMessage(
            error.message || "Could not update the admin account.",
            "error"
        );

        button.disabled = false;
    }
}