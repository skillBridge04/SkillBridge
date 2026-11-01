"use strict";

/* =========================================
   SKILLBRIDGE EMPLOYER DASHBOARD
   ========================================= */

const EMPLOYER_API = "/api/employer";
const AUTH_ME_API = "/api/auth/me";
const EMPLOYER_SKILLS_API = `${EMPLOYER_API}/skills`;

let employerCurrentUser = null;
let employerCompany = null;
let employerCompanyLoaded = false;
let employerJobs = [];
let employerSkills = [];
let employerSkillsAvailable = false;


/* =========================================
   INITIALIZE DASHBOARD
   ========================================= */

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


/* =========================================
   DISPLAY SUCCESS / ERROR MESSAGE
   ========================================= */

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

    if (!element) {
        return;
    }

    element.textContent = "";
    element.hidden = true;
}


/* =========================================
   READ API RESPONSE
   ========================================= */

async function readEmployerResponse(response) {
    const content = await response.text();

    if (!content) {
        return {};
    }

    try {
        return JSON.parse(content);

    } catch {
        return {
            detail: content
        };
    }
}


/* =========================================
   EXTRACT API ERROR MESSAGE
   ========================================= */

function employerApiError(
    data,
    fallback = "The request failed."
) {
    if (typeof data?.detail === "string") {
        return data.detail;
    }

    if (Array.isArray(data?.detail)) {
        return data.detail.map(item => {

            const field = Array.isArray(item.loc)
                ? item.loc
                    .filter(part => part !== "body")
                    .join(".")
                : "";

            const message = item.msg || "Invalid value";

            return field
                ? `${field}: ${message}`
                : message;

        }).join("; ");
    }

    if (typeof data?.message === "string") {
        return data.message;
    }

    return fallback;
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
        button.textContent = text || "Please wait...";

    } else {
        button.disabled = false;

        button.textContent =
            text ||
            button.dataset.originalText ||
            "Save";
    }
}


function toNullableString(value) {
    const cleaned = String(value ?? "").trim();

    return cleaned || null;
}


function toNullableNumber(value) {
    if (
        value === "" ||
        value === null ||
        value === undefined
    ) {
        return null;
    }

    const number = Number(value);

    return Number.isFinite(number)
        ? number
        : null;
}


function isValidHttpUrl(value) {
    try {
        const url = new URL(value);

        return (
            url.protocol === "http:" ||
            url.protocol === "https:"
        );

    } catch {
        return false;
    }
}


function formatForDateTimeLocal(value) {
    if (!value) {
        return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "";
    }

    const pad = number =>
        String(number).padStart(2, "0");

    return (
        `${date.getFullYear()}-` +
        `${pad(date.getMonth() + 1)}-` +
        `${pad(date.getDate())}T` +
        `${pad(date.getHours())}:` +
        `${pad(date.getMinutes())}`
    );
}


function employerDateToIso(value) {
    if (!value) {
        return null;
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        throw new Error(
            "Please enter a valid application deadline."
        );
    }

    return date.toISOString();
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


/* =========================================
   COMMON API REQUEST
   ========================================= */

async function employerApiRequest(path, options = {}) {

    const authorization = getEmployerAuthorization();

    if (!authorization) {
        clearEmployerSession();

        window.location.replace("/login");

        throw new Error(
            "Your session has expired. Please log in again."
        );
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
            "Cannot connect to SkillBridge. " +
            "Check that your FastAPI server is running."
        );
    }

    const result = await readEmployerResponse(response);

    // Session expired.
    if (response.status === 401) {
        clearEmployerSession();

        window.location.replace("/login");

        const error = new Error(
            "Your session has expired. Please log in again."
        );

        error.status = 401;

        throw error;
    }

    // Handle API errors.
    if (!response.ok) {

        const error = new Error(
            employerApiError(
                result,
                `Request failed with status ${response.status}.`
            )
        );

        error.status = response.status;
        error.data = result;

        throw error;
    }

    return result;
}


/* =========================================
   GET MY COMPANY
   ========================================= */

async function getMyEmployerCompany() {

    try {
        const result = await employerApiRequest(
            `${EMPLOYER_API}/company`
        );

        return result?.company || result || null;

    } catch (error) {

        // The backend returns 404 when the employer
        // has not created a company yet.

        if (error.status === 404) {
            return null;
        }

        throw error;
    }
}


/* =========================================
   GET AVAILABLE SKILLS
   ========================================= */

async function getEmployerSkills() {

    const result = await employerApiRequest(
        EMPLOYER_SKILLS_API
    );

    const skills = Array.isArray(result?.skills)
        ? result.skills
        : Array.isArray(result)
            ? result
            : [];

    return skills.filter(skill =>
        skill &&
        Number.isInteger(Number(skill.id)) &&
        skill.name
    );
}


/* =========================================
   LOAD CURRENT EMPLOYER
   ========================================= */

async function loadEmployerUser() {

    const authorization = getEmployerAuthorization();

    if (!authorization) {
        window.location.replace("/login");
        return;
    }

    showEmployerMessage(
        "Checking your account...",
        "info"
    );

    try {

        const result = await employerApiRequest(
            AUTH_ME_API
        );

        employerCurrentUser =
            result.user ||
            result.data ||
            result;

        const role = employerNormalize(
            employerCurrentUser.role ||
            employerCurrentUser.user_role
        );

        // Redirect Admin.
        if (role === "ADMIN") {
            window.location.replace("/admin");
            return;
        }

        // Redirect Job Seeker.
        if (role === "JOB_SEEKER") {
            window.location.replace("/dashboard");
            return;
        }

        // Validate Employer role.
        const employerRoles = [
            "EMPLOYER",
            "RECRUITER",
            "EMPLOYER_RECRUITER"
        ];

        if (!employerRoles.includes(role)) {
            clearEmployerSession();

            window.location.replace("/login");
            return;
        }

        displayEmployerUser(employerCurrentUser);

        // Check account status.
        const accountStatus = employerNormalize(
            employerCurrentUser.account_status ||
            employerCurrentUser.status
        );

        if (
            accountStatus &&
            !["ACTIVE", "APPROVED"].includes(accountStatus)
        ) {
            showEmployerApprovalPending(accountStatus);
            return;
        }

        // Load dashboard data.
        await loadAllEmployerData();

    } catch (error) {

        const message = String(
            error.message || ""
        ).toLowerCase();

        if (
            message.includes("pending admin approval") ||
            message.includes("inactive")
        ) {
            showEmployerApprovalPending(
                "PENDING / INACTIVE"
            );

            return;
        }

        showEmployerMessage(
            error.message ||
            "Unable to verify your account.",
            "error"
        );
    }
}


/* =========================================
   DISPLAY EMPLOYER INFORMATION
   ========================================= */

function displayEmployerUser(user) {

    const name =
        user.name ||
        user.full_name ||
        user.username ||
        user.email?.split("@")[0] ||
        "Employer";

    const email = user.email || "Email not provided";

    const role = employerFormatRole(
        user.role ||
        user.user_role ||
        "EMPLOYER"
    );

    const initials = name
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map(part => part.charAt(0).toUpperCase())
        .join("") || "E";

    employerSetText(
        "employerHeaderName",
        name
    );

    employerSetText(
        "employerAvatar",
        initials
    );

    employerSetText(
        "employerWelcomeName",
        name.trim().split(/\s+/)[0]
    );

    employerSetText(
        "employerRoleBadge",
        role
    );

    employerSetText(
        "employerProfileName",
        name
    );

    employerSetText(
        "employerProfileEmail",
        email
    );

    employerSetText(
        "employerProfileRole",
        role
    );
}


/* =========================================
   EMPLOYER APPROVAL PENDING
   ========================================= */

function showEmployerApprovalPending(accountStatus) {

    const banner = document.getElementById("approvalBanner");

    const workspace = document.getElementById(
        "employerWorkspace"
    );

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
        heading.textContent =
            "Your employer account needs approval";
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

    const button = document.getElementById(
        "employerLogoutButton"
    );

    if (!button) {
        return;
    }

    button.addEventListener("click", () => {

        clearEmployerSession();

        window.location.replace("/login");
    });
}


/* =========================================
   LOAD ALL EMPLOYER DASHBOARD DATA
   ========================================= */

async function loadAllEmployerData() {

    hideEmployerMessage();

    try {

        /*
         * The current backend does not have:
         *
         * GET /api/employer/dashboard
         *
         * Therefore, dashboard statistics are calculated
         * from the employer's job list.
         */

        employerCompany = await getMyEmployerCompany();

        employerCompanyLoaded = true;

        // Load jobs only if the company exists.
        if (employerCompany) {

            const jobsResult = await employerApiRequest(
                `${EMPLOYER_API}/jobs`
            );

            employerJobs = Array.isArray(jobsResult?.jobs)
                ? jobsResult.jobs
                : Array.isArray(jobsResult)
                    ? jobsResult
                    : [];

        } else {

            employerJobs = [];
        }


        /*
         * Load the skill catalog.
         *
         * Requires GET /api/employer/skills in employer.py.
         */

        employerSkillsAvailable = false;
        employerSkills = [];

        try {

            employerSkills = await getEmployerSkills();

            employerSkillsAvailable = true;

        } catch (skillError) {

            if (skillError.status !== 404) {
                console.warn(
                    "Could not load employer skill catalog:",
                    skillError
                );
            }
        }


        /*
         * JobResponse does not include required skills.
         *
         * Therefore, retrieve them separately for each job.
         */

        if (
            employerCompany &&
            employerJobs.length > 0
        ) {

            employerJobs = await Promise.all(
                employerJobs.map(async job => {

                    try {

                        const linksResult = await employerApiRequest(
                            `${EMPLOYER_API}/jobs/${encodeURIComponent(job.id)}/skills`
                        );

                        const links = Array.isArray(linksResult?.skills)
                            ? linksResult.skills
                            : Array.isArray(linksResult)
                                ? linksResult
                                : [];

                        return {
                            ...job,

                            required_skills: links.map(link => {

                                const skill = employerSkills.find(
                                    item =>
                                        Number(item.id) ===
                                        Number(link.skill_id)
                                );

                                return {
                                    id: link.skill_id,
                                    skill_id: link.skill_id,
                                    name: skill?.name ||
                                        `Skill #${link.skill_id}`,
                                    is_required: link.is_required
                                };
                            })
                        };

                    } catch (error) {

                        console.warn(
                            `Could not load skills for job ${job.id}:`,
                            error
                        );

                        return {
                            ...job,
                            required_skills: []
                        };
                    }
                })
            );
        }


        // Render dashboard components.

        renderEmployerDashboard();

        renderEmployerCompany(employerCompany);

        populateEmployerSkillOptions();

        renderEmployerJobs(employerJobs);


        if (!employerSkillsAvailable) {

            showEmployerMessage(
                "Company and job data loaded. The skill selector " +
                "is unavailable because GET /api/employer/skills " +
                "has not been added to the backend yet.",
                "warning"
            );

        } else {

            hideEmployerMessage();
        }

    } catch (error) {

        showEmployerMessage(
            error.message ||
            "Unable to load dashboard data.",
            "error"
        );
    }
}


/* =========================================
   RENDER DASHBOARD STATISTICS
   ========================================= */

function renderEmployerDashboard() {

    const totalJobs = employerJobs.length;

    /*
     * The current JobResponse schema does not return status.
     * The current Job model defaults newly created jobs to ACTIVE.
     *
     * Therefore, these statistics are based on the current
     * backend behavior and will need an API update if drafts
     * and inactive jobs are introduced.
     */

    const activeJobs = totalJobs;

    const inactiveJobs = 0;

    employerSetText(
        "employerTotalJobs",
        totalJobs
    );

    employerSetText(
        "employerActiveJobs",
        activeJobs
    );

    employerSetText(
        "employerInactiveJobs",
        inactiveJobs
    );

    employerSetText(
        "employerCompanyStatus",
        employerCompany ? "Set up" : "Not set up"
    );

    const badge = document.getElementById(
        "companyStatusBadge"
    );

    if (badge) {
        badge.textContent = employerCompany
            ? "Active"
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

    const button = document.getElementById(
        "saveCompanyButton"
    );

    if (button) {
        button.textContent = company
            ? "Update Company Profile"
            : "Create Company Profile";
    }
}


/* =========================================
   CREATE OR UPDATE COMPANY
   ========================================= */

function setupCompanyForm() {

    const form = document.getElementById(
        "employerCompanyForm"
    );

    if (!form) {
        return;
    }

    form.addEventListener("submit", async event => {

        event.preventDefault();

        const button = document.getElementById(
            "saveCompanyButton"
        );

        const website = document.getElementById(
            "employerCompanyWebsite"
        ).value.trim();

        const payload = {

            name: document.getElementById(
                "employerCompanyName"
            ).value.trim(),

            industry: toNullableString(
                document.getElementById(
                    "employerCompanyIndustry"
                ).value
            ),

            location: toNullableString(
                document.getElementById(
                    "employerCompanyLocation"
                ).value
            ),

            website: toNullableString(website),

            description: toNullableString(
                document.getElementById(
                    "employerCompanyDescription"
                ).value
            )
        };


        // Validate company name.

        if (payload.name.length < 2) {

            showEmployerMessage(
                "Company name must contain at least two characters.",
                "error"
            );

            return;
        }


        // Validate website.

        if (
            website &&
            !isValidHttpUrl(website)
        ) {

            showEmployerMessage(
                "Enter a valid company website URL beginning with http:// or https://.",
                "error"
            );

            return;
        }


        setButtonBusy(
            button,
            true,
            "Saving..."
        );

        try {

            // Make sure company state is up to date.

            if (!employerCompanyLoaded) {

                employerCompany = await getMyEmployerCompany();

                employerCompanyLoaded = true;
            }


            /*
             * Correct HTTP methods:
             *
             * POST  = Create company.
             * PATCH = Update company.
             */

            const method = employerCompany
                ? "PATCH"
                : "POST";

            const result = await employerApiRequest(
                `${EMPLOYER_API}/company`,
                {
                    method: method,
                    body: JSON.stringify(payload)
                }
            );


            employerCompany = result?.company || result;

            employerCompanyLoaded = true;


            // Update the UI.

            renderEmployerCompany(employerCompany);

            renderEmployerDashboard();

            const badge = document.getElementById(
                "companyStatusBadge"
            );

            if (badge) {
                badge.textContent = "Active";
            }


            showEmployerMessage(
                method === "POST"
                    ? "Company profile created successfully."
                    : "Company profile updated successfully.",
                "success"
            );

        } catch (error) {

            showEmployerMessage(
                error.message ||
                "Unable to save company profile.",
                "error"
            );

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

    const select = document.getElementById(
        "employerRequiredSkills"
    );

    if (!select) {
        return;
    }

    select.replaceChildren();


    // Skill catalog unavailable.

    if (
        !employerSkillsAvailable ||
        employerSkills.length === 0
    ) {

        const option = document.createElement("option");

        option.disabled = true;

        option.textContent = employerSkillsAvailable
            ? "No active skills are available. Ask an administrator to add skills."
            : "Skill catalog is not available yet.";

        select.appendChild(option);

        select.disabled = true;

        return;
    }


    select.disabled = false;

    const selectedSet = new Set(
        selectedIds.map(id => String(id))
    );


    employerSkills.forEach(skill => {

        const option = document.createElement("option");

        option.value = String(skill.id);

        option.textContent =
            skill.name || `Skill ${skill.id}`;

        option.selected = selectedSet.has(
            String(skill.id)
        );

        select.appendChild(option);
    });
}


/* =========================================
   GET SELECTED SKILL IDS
   ========================================= */

function getSelectedEmployerSkillIds() {

    const select = document.getElementById(
        "employerRequiredSkills"
    );

    if (!select) {
        return [];
    }

    return Array.from(select.selectedOptions)

        .map(option => Number(option.value))

        .filter(id =>
            Number.isInteger(id) && id > 0
        );
}


/* =========================================
   GET SKILLS ALREADY ASSIGNED TO A JOB
   ========================================= */

async function loadJobSkillLinks(jobId) {

    const result = await employerApiRequest(
        `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}/skills`
    );

    return Array.isArray(result?.skills)
        ? result.skills
        : Array.isArray(result)
            ? result
            : [];
}


/* =========================================
   SYNCHRONIZE JOB SKILLS
   ========================================= */

async function syncJobSkills(jobId, selectedSkillIds) {

    const existingLinks = await loadJobSkillLinks(jobId);

    const existingBySkillId = new Map(
        existingLinks.map(link => [
            Number(link.skill_id),
            link
        ])
    );

    const selectedSet = new Set(
        selectedSkillIds.map(Number)
    );


    // Remove skills that are no longer selected.

    for (const link of existingLinks) {

        const skillId = Number(link.skill_id);

        if (!selectedSet.has(skillId)) {

            await employerApiRequest(
                `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}/skills/${encodeURIComponent(skillId)}`,
                {
                    method: "DELETE"
                }
            );
        }
    }


    // Add new skills or make selected skills required.

    for (const skillId of selectedSet) {

        const existingLink = existingBySkillId.get(skillId);

        if (!existingLink) {

            await employerApiRequest(
                `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}/skills`,
                {
                    method: "POST",

                    body: JSON.stringify({
                        skill_id: skillId,
                        is_required: true
                    })
                }
            );

        } else if (existingLink.is_required !== true) {

            await employerApiRequest(
                `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}/skills/${encodeURIComponent(skillId)}`,
                {
                    method: "PATCH",

                    body: JSON.stringify({
                        is_required: true
                    })
                }
            );
        }
    }
}


/* =========================================
   JOB FORM
   ========================================= */

function setupJobForm() {

    const form = document.getElementById(
        "employerJobForm"
    );

    if (!form) {
        return;
    }

    form.addEventListener("submit", async event => {

        event.preventDefault();


        // Company must exist before creating a job.

        if (!employerCompany) {

            showEmployerMessage(
                "Create your company profile before creating a job posting.",
                "warning"
            );

            document.getElementById(
                "companyProfile"
            )?.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

            return;
        }


        // Skill catalog must be available.

        if (!employerSkillsAvailable) {

            showEmployerMessage(
                "The skill catalog endpoint is not available. " +
                "Add GET /api/employer/skills to the backend " +
                "before creating jobs with required skills.",
                "error"
            );

            return;
        }


        const jobId = document.getElementById(
            "employerJobId"
        ).value.trim();


        const salaryMin = toNullableNumber(
            document.getElementById(
                "employerSalaryMin"
            ).value
        );

        const salaryMax = toNullableNumber(
            document.getElementById(
                "employerSalaryMax"
            ).value
        );


        const selectedSkillIds =
            getSelectedEmployerSkillIds();


        // Current backend does not support draft status.

        const statusValue = employerNormalize(
            document.getElementById(
                "employerJobStatus"
            )?.value || "ACTIVE"
        );

        if (statusValue === "DRAFT") {

            showEmployerMessage(
                "Draft postings are not supported by the current backend. " +
                "The employer job API creates jobs as ACTIVE. " +
                "Choose 'Publish job' to continue.",
                "warning"
            );

            return;
        }


        // Validate salary values.

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


        // Validate required skills.

        if (selectedSkillIds.length === 0) {

            showEmployerMessage(
                "Select at least one required skill for the job.",
                "error"
            );

            return;
        }


        const applicationUrl = document.getElementById(
            "employerApplicationUrl"
        ).value.trim();


        if (
            applicationUrl &&
            !isValidHttpUrl(applicationUrl)
        ) {

            showEmployerMessage(
                "Enter a valid application URL beginning with http:// or https://.",
                "error"
            );

            return;
        }


        // Prepare JobCreate / JobUpdate payload.

        const payload = {

            title: document.getElementById(
                "employerJobTitle"
            ).value.trim(),

            location: toNullableString(
                document.getElementById(
                    "employerJobLocation"
                ).value
            ),

            employment_type: toNullableString(
                document.getElementById(
                    "employerEmploymentType"
                ).value
            ),

            salary_min: salaryMin,

            salary_max: salaryMax,

            currency: document.getElementById(
                "employerCurrency"
            ).value.trim().toUpperCase() || "BDT",

            experience_required: toNullableString(
                document.getElementById(
                    "employerExperience"
                ).value
            ),

            education_required: toNullableString(
                document.getElementById(
                    "employerEducation"
                ).value
            ),

            application_url: toNullableString(
                applicationUrl
            ),

            deadline: employerDateToIso(
                document.getElementById(
                    "employerJobDeadline"
                ).value
            ),

            description: toNullableString(
                document.getElementById(
                    "employerJobDescription"
                ).value
            )
        };


        // Validate title.

        if (payload.title.length < 2) {

            showEmployerMessage(
                "Job title must contain at least two characters.",
                "error"
            );

            return;
        }


        // Validate description.

        if (!payload.description) {

            showEmployerMessage(
                "Job description is required.",
                "error"
            );

            return;
        }


        const button = document.getElementById(
            "saveEmployerJobButton"
        );

        setButtonBusy(
            button,
            true,
            jobId ? "Updating..." : "Creating..."
        );


        try {

            let savedJob;


            // Update existing job.

            if (jobId) {

                savedJob = await employerApiRequest(
                    `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}`,
                    {
                        method: "PATCH",
                        body: JSON.stringify(payload)
                    }
                );

            } else {

                // Create a new job.

                savedJob = await employerApiRequest(
                    `${EMPLOYER_API}/jobs`,
                    {
                        method: "POST",
                        body: JSON.stringify(payload)
                    }
                );
            }


            const savedJobId = savedJob?.id || jobId;

            if (!savedJobId) {

                throw new Error(
                    "The job was saved, but the API did not return its ID. " +
                    "Required skills could not be attached."
                );
            }


            /*
             * The current JobCreate and JobUpdate schemas
             * do not accept required_skill_ids.
             *
             * Skills must be attached separately using
             * the JobSkill API endpoints.
             */

            try {

                await syncJobSkills(
                    savedJobId,
                    selectedSkillIds
                );

            } catch (skillError) {

                showEmployerMessage(
                    `The job was saved, but its required skills ` +
                    `could not be fully updated: ${skillError.message}`,
                    "warning"
                );

                resetEmployerJobForm();

                await loadAllEmployerData();

                return;
            }


            showEmployerMessage(
                jobId
                    ? "Job posting updated successfully."
                    : "Job posting created successfully.",
                "success"
            );


            resetEmployerJobForm();

            await loadAllEmployerData();


        } catch (error) {

            showEmployerMessage(
                error.message ||
                "Unable to save the job posting.",
                "error"
            );

        } finally {

            setButtonBusy(
                button,
                false,

                document.getElementById(
                    "employerJobId"
                )?.value
                    ? "Update Job Posting"
                    : "Create Job Posting"
            );
        }
    });


    // Cancel editing.

    document.getElementById(
        "cancelEmployerJobEditButton"
    )?.addEventListener(
        "click",
        resetEmployerJobForm
    );
}


/* =========================================
   RESET JOB FORM
   ========================================= */

function resetEmployerJobForm() {

    const form = document.getElementById(
        "employerJobForm"
    );

    if (form) {
        form.reset();
    }

    const hiddenId = document.getElementById(
        "employerJobId"
    );

    if (hiddenId) {
        hiddenId.value = "";
    }

    employerSetText(
        "jobEditorHeading",
        "Create a Job Posting"
    );

    employerSetText(
        "saveEmployerJobButton",
        "Create Job Posting"
    );


    const status = document.getElementById(
        "employerJobStatus"
    );

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


/* =========================================
   EDIT EMPLOYER JOB
   ========================================= */

function editEmployerJob(jobId) {

    const job = employerJobs.find(
        item => String(item.id) === String(jobId)
    );

    if (!job) {

        showEmployerMessage(
            "Could not find that job posting.",
            "error"
        );

        return;
    }


    employerSetText(
        "jobEditorHeading",
        "Edit Job Posting"
    );

    employerSetText(
        "saveEmployerJobButton",
        "Update Job Posting"
    );


    document.getElementById(
        "employerJobId"
    ).value = job.id;

    document.getElementById(
        "employerJobTitle"
    ).value = job.title || "";

    document.getElementById(
        "employerJobLocation"
    ).value = job.location || "";

    document.getElementById(
        "employerEmploymentType"
    ).value = job.employment_type || "Full-time";

    document.getElementById(
        "employerSalaryMin"
    ).value = job.salary_min ?? "";

    document.getElementById(
        "employerSalaryMax"
    ).value = job.salary_max ?? "";

    document.getElementById(
        "employerCurrency"
    ).value = job.currency || "BDT";

    document.getElementById(
        "employerExperience"
    ).value = job.experience_required || "";

    document.getElementById(
        "employerEducation"
    ).value = job.education_required || "";

    document.getElementById(
        "employerApplicationUrl"
    ).value = job.application_url || "";

    document.getElementById(
        "employerJobDescription"
    ).value = job.description || "";


    const deadlineInput = document.getElementById(
        "employerJobDeadline"
    );

    if (deadlineInput) {
        deadlineInput.value = formatForDateTimeLocal(
            job.deadline
        );
    }


    /*
     * JobResponse currently does not include status.
     * The current employer API creates jobs as ACTIVE.
     */

    const statusSelect = document.getElementById(
        "employerJobStatus"
    );

    if (statusSelect) {
        statusSelect.value = "ACTIVE";
    }


    const selectedIds = Array.isArray(
        job.required_skills
    )
        ? job.required_skills.map(skill =>
            typeof skill === "object"
                ? skill.skill_id ?? skill.id
                : skill
        )
        : [];

    populateEmployerSkillOptions(selectedIds);


    const cancelButton = document.getElementById(
        "cancelEmployerJobEditButton"
    );

    if (cancelButton) {
        cancelButton.hidden = false;
    }


    document.getElementById(
        "jobEditor"
    )?.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


/* =========================================
   RENDER EMPLOYER JOB TABLE
   ========================================= */

function renderEmployerJobs(jobs) {

    const tbody = document.getElementById(
        "employerJobsTableBody"
    );

    if (!tbody) {
        return;
    }

    tbody.replaceChildren();


    // Empty state.

    if (!jobs.length) {

        const row = document.createElement("tr");

        const cell = document.createElement("td");

        cell.colSpan = 6;

        cell.className = "employer-empty-state";

        cell.textContent = employerCompany
            ? "You have not created any job postings yet. Create your first job above."
            : "Create your company profile before adding job postings.";

        row.appendChild(cell);

        tbody.appendChild(row);

        return;
    }


    jobs.forEach(job => {

        const row = document.createElement("tr");


        // Job title.

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


        // Location.

        row.appendChild(
            createEmployerCell(
                job.location || "Not specified"
            )
        );


        // Salary.

        row.appendChild(
            createEmployerCell(
                formatEmployerSalary(job)
            )
        );


        /*
         * JobResponse currently omits status.
         * The Job model has ACTIVE as its default.
         */

        const statusCell = document.createElement("td");

        const badge = document.createElement("span");

        badge.className = "employer-status active";

        badge.textContent = "Active";

        statusCell.appendChild(badge);

        row.appendChild(statusCell);


        // Required skills.

        const skillsCell = document.createElement("td");

        const skillNames = Array.isArray(job.required_skills)
            ? job.required_skills.map(skill =>

                typeof skill === "string"
                    ? skill
                    : skill.name ||
                      `Skill #${skill.skill_id ?? skill.id}`

            )
            : [];

        skillsCell.textContent = skillNames.length
            ? skillNames.join(", ")
            : "No skills listed";

        row.appendChild(skillsCell);


        // Actions.

        const actionsCell = document.createElement("td");

        const actions = document.createElement("div");

        actions.className = "employer-table-actions";


        actions.appendChild(
            createJobActionButton(
                "Edit",
                "edit",
                job.id,
                "secondary"
            )
        );


        actions.appendChild(
            createJobActionButton(
                "Delete",
                "delete",
                job.id,
                "danger"
            )
        );


        actionsCell.appendChild(actions);

        row.appendChild(actionsCell);

        tbody.appendChild(row);
    });
}


/* =========================================
   CREATE TABLE CELL
   ========================================= */

function createEmployerCell(value) {

    const cell = document.createElement("td");

    cell.textContent = value;

    return cell;
}


/* =========================================
   FORMAT SALARY
   ========================================= */

function formatEmployerSalary(job) {

    const minimum = job.salary_min;

    const maximum = job.salary_max;

    const currency = job.currency || "BDT";


    if (
        minimum == null &&
        maximum == null
    ) {
        return "Not specified";
    }


    const formatter = value =>
        Number(value).toLocaleString(
            undefined,
            {
                maximumFractionDigits: 2
            }
        );


    if (
        minimum != null &&
        maximum != null
    ) {

        return (
            `${currency} ${formatter(minimum)} – ` +
            `${currency} ${formatter(maximum)}`
        );
    }


    if (minimum != null) {

        return (
            `From ${currency} ${formatter(minimum)}`
        );
    }


    return (
        `Up to ${currency} ${formatter(maximum)}`
    );
}


/* =========================================
   CREATE JOB ACTION BUTTON
   ========================================= */

function createJobActionButton(
    label,
    action,
    jobId,
    variant = "secondary"
) {

    const button = document.createElement("button");

    button.type = "button";

    button.className = `employer-button ${variant}`;

    button.textContent = label;

    button.dataset.action = action;

    button.dataset.jobId = String(jobId);

    return button;
}


/* =========================================
   JOB TABLE ACTIONS
   ========================================= */

function setupJobTableActions() {

    const tbody = document.getElementById(
        "employerJobsTableBody"
    );

    if (!tbody) {
        return;
    }


    tbody.addEventListener("click", async event => {

        const button = event.target.closest(
            "button[data-action]"
        );

        if (!button) {
            return;
        }

        const action = button.dataset.action;

        const jobId = button.dataset.jobId;


        // Edit job.

        if (action === "edit") {

            editEmployerJob(jobId);

            return;
        }


        // Delete job.

        if (action === "delete") {

            const confirmed = window.confirm(
                "Permanently delete this job posting? " +
                "This action cannot be undone."
            );

            if (!confirmed) {
                return;
            }

            button.disabled = true;

            try {

                await employerApiRequest(
                    `${EMPLOYER_API}/jobs/${encodeURIComponent(jobId)}`,
                    {
                        method: "DELETE"
                    }
                );


                // Reset editor if this job was being edited.

                if (
                    String(
                        document.getElementById(
                            "employerJobId"
                        )?.value
                    ) === String(jobId)
                ) {

                    resetEmployerJobForm();
                }


                showEmployerMessage(
                    "Job posting deleted successfully.",
                    "success"
                );


                await loadAllEmployerData();

            } catch (error) {

                showEmployerMessage(
                    error.message ||
                    "Unable to delete this job.",
                    "error"
                );

                button.disabled = false;
            }
        }
    });
}


/* =========================================
   REFRESH BUTTONS
   ========================================= */

function setupEmployerRefresh() {

    document.getElementById(
        "refreshEmployerButton"
    )?.addEventListener(
        "click",
        loadAllEmployerData
    );


    document.getElementById(
        "refreshEmployerJobsButton"
    )?.addEventListener(
        "click",
        loadAllEmployerData
    );
}