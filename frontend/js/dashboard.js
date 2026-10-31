"use strict";

/* =========================================
   SKILLBRIDGE DASHBOARD
   ========================================= */

const CURRENT_USER_URL = "/api/auth/me";
const RESUME_UPLOAD_URL = "/api/resume/upload";
const RECOMMENDED_JOBS_URL = "/api/jobs/recommended";

const COURSE_RECOMMENDATION_URL = (resumeId, jobId) =>
    `/api/courses/recommendations/resume/${encodeURIComponent(resumeId)}/job/${encodeURIComponent(jobId)}`;

let latestJobsRequest = 0;
let latestCoursesRequest = 0;


/* =========================================
   INITIALIZE DASHBOARD
   ========================================= */

document.addEventListener("DOMContentLoaded", () => {
    updateDashboardCopyright();
    setupLogout();
    setupResumeSelection();
    setupResumeSkillExtraction();
    setupCourseRecommendations();
    setupRecommendedJobs();
    loadCurrentUser();
});


/* =========================================
   COPYRIGHT YEAR
   ========================================= */

function updateDashboardCopyright() {
    setText("currentYear", String(new Date().getFullYear()));
}


/* =========================================
   DASHBOARD MESSAGE HELPERS
   ========================================= */

function setText(elementId, value) {
    const element = document.getElementById(elementId);

    if (element) {
        element.textContent = value ?? "";
    }
}


function showDashboardMessage(message, type = "info") {
    const element = document.getElementById("dashboardMessage");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `dashboard-message ${type}`;
    element.hidden = false;
}


function hideDashboardMessage() {
    const element = document.getElementById("dashboardMessage");

    if (element) {
        element.hidden = true;
    }
}


function showJobRecommendationsMessage(message, type = "info") {
    const element = document.getElementById(
        "jobRecommendationsMessage"
    );

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `dashboard-message ${type}`;
    element.hidden = false;
}


function showSkillGapsMessage(message, type = "info") {
    const element = document.getElementById("skillGapsMessage");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `dashboard-message ${type}`;
    element.hidden = false;
}


function showCourseMessage(message, type = "info") {
    const element = document.getElementById("coursesMessage");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `dashboard-message ${type}`;
    element.hidden = false;
}


/* =========================================
   API RESPONSE HELPERS
   ========================================= */

async function readApiResponse(response) {
    const responseText = await response.text();

    if (!responseText) {
        return {};
    }

    try {
        return JSON.parse(responseText);
    } catch {
        return {
            detail: responseText
        };
    }
}


function getApiErrorMessage(data, fallbackMessage) {
    const detail = data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                const field = Array.isArray(item.loc)
                    ? item.loc
                        .filter((part) => part !== "body")
                        .join(".")
                    : "";

                const message = item.msg || "Invalid value";

                return field
                    ? `${field}: ${message}`
                    : message;
            })
            .join("; ");
    }

    if (detail && typeof detail === "object") {
        return JSON.stringify(detail);
    }

    if (typeof data?.message === "string") {
        return data.message;
    }

    return fallbackMessage;
}


/* =========================================
   AUTHENTICATION HELPERS
   ========================================= */

function getAccessToken() {
    return sessionStorage.getItem("access_token");
}


function getAuthorizationHeader() {
    const token = getAccessToken();

    const tokenType =
        sessionStorage.getItem("token_type") || "bearer";

    if (!token) {
        return null;
    }

    return `${tokenType} ${token}`;
}


function clearSession() {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("token_type");
    sessionStorage.removeItem("resume_id");
    sessionStorage.removeItem("resume_file_name");
}


function redirectToLogin(message) {
    clearSession();

    if (message) {
        showDashboardMessage(message, "error");
    }

    window.setTimeout(() => {
        window.location.replace("/login");
    }, message ? 800 : 0);
}


/* =========================================
   LOAD CURRENT USER
   ========================================= */

async function loadCurrentUser() {
    const authorization = getAuthorizationHeader();

    if (!authorization) {
        window.location.replace("/login");
        return;
    }

    showDashboardMessage(
        "Checking your account...",
        "info"
    );

    try {
        const response = await fetch(CURRENT_USER_URL, {
            method: "GET",
            headers: {
                Authorization: authorization,
                Accept: "application/json"
            }
        });

        const result = await readApiResponse(response);

        if (response.status === 401) {
            redirectToLogin();
            return;
        }

        if (response.status === 403) {
            throw new Error(
                getApiErrorMessage(
                    result,
                    "You do not have permission to access this dashboard."
                )
            );
        }

        if (!response.ok) {
            throw new Error(
                getApiErrorMessage(
                    result,
                    "Unable to load your account information."
                )
            );
        }

        const user =
            result.user ||
            result.data ||
            result;

        displayUserInformation(user);
        hideDashboardMessage();

    } catch (error) {
        showDashboardMessage(
            error.message ||
            "Could not load your account. Check your FastAPI server.",
            "error"
        );
    }
}


/* =========================================
   DISPLAY USER INFORMATION
   ========================================= */

function displayUserInformation(user) {
    const email = user.email || "Email not provided";

    const fullName =
        user.name ||
        user.full_name ||
        user.username ||
        (user.email ? user.email.split("@")[0] : "") ||
        "User";

    const rawRole =
        user.role ||
        user.user_role ||
        "USER";

    const roleLabel = String(rawRole)
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, (character) => character.toUpperCase());

    const initials = fullName
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0].toUpperCase())
        .join("") || "U";

    setText("headerUserName", fullName);
    setText("headerAvatar", initials);
    setText(
        "welcomeName",
        fullName.trim().split(/\s+/)[0] || "there"
    );
    setText("accountRole", roleLabel);

    setText("profileName", fullName);
    setText("profileEmail", email);
    setText("profileRole", roleLabel);
}


/* =========================================
   LOGOUT
   ========================================= */

function setupLogout() {
    const logoutButton =
        document.getElementById("logoutButton");

    if (!logoutButton) {
        return;
    }

    logoutButton.addEventListener("click", () => {
        clearSession();
        window.location.replace("/login");
    });
}


/* =========================================
   RESUME SKILL RESULTS HELPERS
   ========================================= */

function clearResumeSkillResults(hidePanel = true) {
    const skillsPanel =
        document.getElementById("resumeSkillsPanel");

    const skillsList =
        document.getElementById("resumeSkillsList");

    const skillsSummary =
        document.getElementById("resumeSkillsSummary");

    const skillsEmpty =
        document.getElementById("resumeSkillsEmpty");

    if (skillsList) {
        skillsList.replaceChildren();
    }

    if (skillsSummary) {
        skillsSummary.textContent = "";
        skillsSummary.hidden = true;
    }

    if (skillsEmpty) {
        skillsEmpty.hidden = true;
    }

    if (skillsPanel && hidePanel) {
        skillsPanel.hidden = true;
    }
}


/* =========================================
   GET SKILLS FROM API RESPONSE
   ========================================= */

function getSkillsFromResponse(result) {
    if (Array.isArray(result)) {
        return result;
    }

    if (!result || typeof result !== "object") {
        return null;
    }

    const possibleLists = [
        result.skills,
        result.resume_skills,
        result.extracted_skills,
        result.items,
        result.data?.skills,
        result.data?.resume_skills,
        result.data?.extracted_skills
    ];

    for (const list of possibleLists) {
        if (Array.isArray(list)) {
            return list;
        }
    }

    return null;
}


/* =========================================
   GET SKILL NAME
   ========================================= */

function getSkillName(skill) {
    if (typeof skill === "string") {
        return skill.trim();
    }

    if (!skill || typeof skill !== "object") {
        return "";
    }

    const possibleNames = [
        skill.skill_name,
        skill.name,
        skill.title,
        typeof skill.skill === "string"
            ? skill.skill
            : null,
        skill.skill?.skill_name,
        skill.skill?.name
    ];

    for (const name of possibleNames) {
        if (typeof name === "string" && name.trim()) {
            return name.trim();
        }
    }

    return "";
}


/* =========================================
   SKILL CONFIDENCE AND SOURCE
   ========================================= */

function getSkillConfidence(skill) {
    if (!skill || typeof skill !== "object") {
        return "";
    }

    const confidence =
        skill.confidence ??
        skill.confidence_score ??
        skill.score;

    if (
        confidence === undefined ||
        confidence === null ||
        confidence === ""
    ) {
        return "";
    }

    const numericConfidence = Number(confidence);

    if (
        Number.isFinite(numericConfidence) &&
        numericConfidence >= 0 &&
        numericConfidence <= 1
    ) {
        return `Confidence: ${Math.round(
            numericConfidence * 100
        )}%`;
    }

    return `Confidence: ${String(confidence)}`;
}


function getSkillSource(skill) {
    if (!skill || typeof skill !== "object") {
        return "";
    }

    const source =
        skill.source ||
        skill.skill_source;

    if (
        typeof source === "string" &&
        source.trim()
    ) {
        return `Source: ${source.trim()}`;
    }

    return "";
}


/* =========================================
   DISPLAY EXTRACTED SKILLS
   ========================================= */

function displayExtractedSkills(skills) {
    const skillsPanel =
        document.getElementById("resumeSkillsPanel");

    const skillsList =
        document.getElementById("resumeSkillsList");

    const skillsSummary =
        document.getElementById("resumeSkillsSummary");

    const skillsEmpty =
        document.getElementById("resumeSkillsEmpty");

    if (
        !skillsPanel ||
        !skillsList ||
        !skillsSummary ||
        !skillsEmpty
    ) {
        throw new Error(
            "The resume skills section is missing from dashboard.html."
        );
    }

    skillsList.replaceChildren();

    const normalizedSkills = skills
        .map((skill) => ({
            original: skill,
            name: getSkillName(skill)
        }))
        .filter((skill) => skill.name.length > 0);

    skillsPanel.hidden = false;

    if (normalizedSkills.length === 0) {
        skillsSummary.textContent =
            "Analysis completed, but no recognizable skill names were returned.";

        skillsSummary.hidden = false;
        skillsEmpty.hidden = false;

        return;
    }

    normalizedSkills.forEach(({ original, name }) => {
        const listItem = document.createElement("li");

        listItem.className = "resume-skill-item";

        const skillName = document.createElement("strong");

        skillName.className = "resume-skill-name";
        skillName.textContent = name;

        listItem.appendChild(skillName);

        const confidenceText = getSkillConfidence(original);

        if (confidenceText) {
            listItem.appendChild(
                createTextElement(
                    "span",
                    "resume-skill-meta",
                    confidenceText
                )
            );
        }

        const sourceText = getSkillSource(original);

        if (sourceText) {
            listItem.appendChild(
                createTextElement(
                    "span",
                    "resume-skill-meta",
                    sourceText
                )
            );
        }

        skillsList.appendChild(listItem);
    });

    skillsSummary.textContent =
        `Analysis completed. Found ${normalizedSkills.length} skill(s) in your resume.`;

    skillsSummary.hidden = false;
    skillsEmpty.hidden = true;
}


/* =========================================
   CREATE SAFE TEXT ELEMENTS
   ========================================= */

function createTextElement(tagName, className, value) {
    const element = document.createElement(tagName);

    if (className) {
        element.className = className;
    }

    element.textContent = value ?? "";

    return element;
}


/* =========================================
   CLEAR SKILL GAP ANALYSIS
   ========================================= */

function clearSkillGapAnalysis() {
    const gapList =
        document.getElementById("skillGapsList");

    const gapSummary =
        document.getElementById("skillGapsSummary");

    const gapMessage =
        document.getElementById("skillGapsMessage");

    const gapEmpty =
        document.getElementById("skillGapsEmpty");

    if (gapList) {
        gapList.replaceChildren();
    }

    if (gapSummary) {
        gapSummary.textContent = "";
        gapSummary.hidden = true;
    }

    if (gapMessage) {
        gapMessage.textContent = "";
        gapMessage.hidden = true;
    }

    if (gapEmpty) {
        gapEmpty.hidden = false;

        const paragraph = gapEmpty.querySelector("p");

        if (paragraph) {
            paragraph.textContent =
                "Upload your resume and analyze your skills to see the skills required by recommended jobs that are missing from your resume.";
        }
    }

    setText("skillGapsStat", "—");
}


/* =========================================
   NORMALIZE SKILL NAME
   ========================================= */

function normalizeSkillName(skillName) {
    return String(skillName || "")
        .trim()
        .replace(/\s+/g, " ")
        .toLocaleLowerCase();
}


/* =========================================
   GET MISSING SKILLS FROM JOBS
   ========================================= */

function collectDistinctSkillGaps(jobs) {
    const skillGapsByName = new Map();

    jobs.forEach((job) => {
        const missingSkills = Array.isArray(job.missing_skills)
            ? job.missing_skills
            : [];

        missingSkills.forEach((skillValue) => {
            const skillName = getSkillName(skillValue);

            if (!skillName) {
                return;
            }

            const normalizedName =
                normalizeSkillName(skillName);

            if (!normalizedName) {
                return;
            }

            if (!skillGapsByName.has(normalizedName)) {
                skillGapsByName.set(normalizedName, {
                    name: skillName,
                    jobs: []
                });
            }

            const gap = skillGapsByName.get(normalizedName);

            const jobId = job.job_id ?? job.id ?? job.title;

            const alreadyAdded = gap.jobs.some(
                (existingJob) =>
                    String(existingJob.job_id) ===
                    String(jobId)
            );

            if (!alreadyAdded) {
                gap.jobs.push({
                    job_id: jobId,
                    title: job.title || "Untitled job",
                    company_name:
                        job.company_name ||
                        job.company?.name ||
                        "Company not specified"
                });
            }
        });
    });

    return Array.from(skillGapsByName.values())
        .sort((first, second) =>
            first.name.localeCompare(second.name)
        );
}


/* =========================================
   DISPLAY SKILL GAP ANALYSIS
   ========================================= */

function displaySkillGapAnalysis(jobs) {
    const gapList =
        document.getElementById("skillGapsList");

    const gapSummary =
        document.getElementById("skillGapsSummary");

    const gapEmpty =
        document.getElementById("skillGapsEmpty");

    if (!gapList || !gapEmpty) {
        return;
    }

    gapList.replaceChildren();

    const gaps = collectDistinctSkillGaps(jobs);

    setText("skillGapsStat", String(gaps.length));

    if (gaps.length === 0) {
        gapEmpty.hidden = false;

        const paragraph = gapEmpty.querySelector("p");

        if (paragraph) {
            paragraph.textContent = jobs.length > 0
                ? "No missing required skills were found across these recommended jobs."
                : "No matching jobs are available to analyze yet. Add jobs and link their required skills to see skill gaps.";
        }

        if (gapSummary) {
            gapSummary.textContent = jobs.length > 0
                ? "Your resume covers all the required skills listed for the recommended jobs."
                : "Skill-gap analysis will become available when matching jobs are found.";

            gapSummary.hidden = false;
        }

        showSkillGapsMessage(
            jobs.length > 0
                ? "No skill gaps were found in the current job matches."
                : "There are no matching jobs to analyze yet.",
            "info"
        );

        return;
    }

    gapEmpty.hidden = true;

    if (gapSummary) {
        gapSummary.textContent =
            `Found ${gaps.length} distinct skill(s) to improve across ${jobs.length} recommended job(s). A skill required by multiple jobs is counted only once.`;

        gapSummary.hidden = false;
    }

    gaps.forEach((gap) => {
        const card = document.createElement("article");

        card.className = "skill-gap-card";

        const header = document.createElement("div");

        header.className = "skill-gap-card-header";

        header.appendChild(
            createTextElement(
                "h3",
                "skill-gap-name",
                gap.name
            )
        );

        header.appendChild(
            createTextElement(
                "span",
                "skill-gap-count",
                `Required by ${gap.jobs.length} ${gap.jobs.length === 1 ? "job" : "jobs"}`
            )
        );

        card.appendChild(header);

        card.appendChild(
            createTextElement(
                "p",
                "skill-gap-description",
                "This skill is required by a recommended job but was not detected in your resume."
            )
        );

        card.appendChild(
            createTextElement(
                "strong",
                "skill-gap-required-heading",
                "Required for:"
            )
        );

        const jobsList = document.createElement("ul");

        jobsList.className = "skill-gap-jobs";

        gap.jobs.forEach((job) => {
            const listItem = document.createElement("li");

            listItem.appendChild(
                createTextElement(
                    "span",
                    "skill-gap-job-title",
                    job.title
                )
            );

            listItem.appendChild(
                createTextElement(
                    "span",
                    "skill-gap-company",
                    job.company_name
                )
            );

            jobsList.appendChild(listItem);
        });

        card.appendChild(jobsList);

        gapList.appendChild(card);
    });

    showSkillGapsMessage(
        `Skill-gap analysis completed. You can focus on these ${gaps.length} distinct skill(s) to improve your matches.`,
        "success"
    );
}


/* =========================================
   COURSE EMPTY STATE HELPERS
   ========================================= */

function clearRecommendedCourses(
    message = "Recommended courses will appear here after skill-gap analysis.",
    count = "—"
) {
    // Invalidate any older course request.
    latestCoursesRequest++;

    const coursesList =
        document.getElementById("recommendedCoursesList");

    const coursesEmpty =
        document.getElementById("coursesEmpty");

    const coursesMessage =
        document.getElementById("coursesMessage");

    if (coursesList) {
        coursesList.replaceChildren();
    }

    if (coursesEmpty) {
        coursesEmpty.hidden = false;

        const paragraph = coursesEmpty.querySelector("p");

        if (paragraph) {
            paragraph.textContent = message;
        }
    }

    if (coursesMessage) {
        coursesMessage.textContent = "";
        coursesMessage.hidden = true;
    }

    setText("coursesStat", String(count));
}


/* =========================================
   CLEAR JOB RECOMMENDATIONS
   ========================================= */

function clearJobRecommendations() {
    const jobsList =
        document.getElementById("recommendedJobsList");

    const jobsEmpty =
        document.getElementById("recommendedJobsEmpty");

    const jobsMessage =
        document.getElementById("jobRecommendationsMessage");

    if (jobsList) {
        jobsList.replaceChildren();
    }

    if (jobsEmpty) {
        jobsEmpty.hidden = false;

        const heading = jobsEmpty.querySelector("h3");
        const paragraph = jobsEmpty.querySelector("p");

        if (heading) {
            heading.textContent =
                "Your job matches will appear here";
        }

        if (paragraph) {
            paragraph.textContent =
                "Upload your resume and analyze your skills to discover suitable job opportunities.";
        }
    }

    if (jobsMessage) {
        jobsMessage.textContent = "";
        jobsMessage.hidden = true;
    }

    setText("jobMatchesStat", "—");

    clearSkillGapAnalysis();
    clearRecommendedCourses();
}


/* =========================================
   RESET RESUME DISPLAY
   ========================================= */

function resetResumeDisplay() {
    const fileInput =
        document.getElementById("resumeFile");

    const fileNameElement =
        document.getElementById("selectedFileName");

    const clearButton =
        document.getElementById("clearResumeButton");

    const deleteButton =
        document.getElementById("deleteResumeButton");

    const analyzeButton =
        document.getElementById("analyzeResumeButton");

    const uploadButton =
        document.getElementById("prepareResumeButton");

    if (fileInput) {
        fileInput.value = "";
    }

    if (fileNameElement) {
        fileNameElement.textContent = "";
        fileNameElement.hidden = true;
    }

    if (clearButton) {
        clearButton.hidden = true;
        clearButton.disabled = false;
    }

    if (deleteButton) {
        deleteButton.hidden = true;
        deleteButton.disabled = false;
        deleteButton.textContent = "Delete Uploaded Resume";
    }

    if (analyzeButton) {
        analyzeButton.hidden = true;
        analyzeButton.disabled = false;
        analyzeButton.textContent = "Analyze Resume";
    }

    if (uploadButton) {
        uploadButton.disabled = false;
        uploadButton.textContent = "Upload Resume";
    }

    setText("resumeStat", "Not started");

    clearResumeSkillResults();
    clearJobRecommendations();
}


/* =========================================
   RESTORE UPLOADED RESUME DISPLAY
   ========================================= */

function restoreUploadedResumeDisplay() {
    const resumeId =
        sessionStorage.getItem("resume_id");

    const savedFileName =
        sessionStorage.getItem("resume_file_name");

    const fileInput =
        document.getElementById("resumeFile");

    const fileNameElement =
        document.getElementById("selectedFileName");

    const clearButton =
        document.getElementById("clearResumeButton");

    const deleteButton =
        document.getElementById("deleteResumeButton");

    const analyzeButton =
        document.getElementById("analyzeResumeButton");

    if (!resumeId) {
        if (deleteButton) {
            deleteButton.hidden = true;
        }

        if (analyzeButton) {
            analyzeButton.hidden = true;
        }

        clearResumeSkillResults();

        return;
    }

    setText("resumeStat", "Uploaded");

    if (deleteButton) {
        deleteButton.hidden = false;
        deleteButton.disabled = false;
        deleteButton.textContent = "Delete Uploaded Resume";
    }

    if (analyzeButton) {
        analyzeButton.hidden = false;
        analyzeButton.disabled = false;
        analyzeButton.textContent = "Analyze Resume";
    }

    if (fileInput && !fileInput.files?.length) {
        if (fileNameElement) {
            fileNameElement.textContent =
                `Uploaded resume: ${savedFileName || "Saved resume"}`;

            fileNameElement.hidden = false;
        }

        if (clearButton) {
            clearButton.hidden = true;
        }
    }
}


/* =========================================
   RESUME SELECTION, UPLOAD AND DELETE
   ========================================= */

function setupResumeSelection() {
    const form =
        document.getElementById("resumeSelectionForm");

    const fileInput =
        document.getElementById("resumeFile");

    const fileNameElement =
        document.getElementById("selectedFileName");

    const clearButton =
        document.getElementById("clearResumeButton");

    const uploadButton =
        document.getElementById("prepareResumeButton");

    const deleteButton =
        document.getElementById("deleteResumeButton");

    const analyzeButton =
        document.getElementById("analyzeResumeButton");

    if (
        !form ||
        !fileInput ||
        !fileNameElement ||
        !clearButton ||
        !uploadButton
    ) {
        return;
    }

    const allowedExtensions = [".pdf", ".docx"];

    function isSupportedFile(file) {
        if (!file || !file.name) {
            return false;
        }

        return allowedExtensions.some((extension) =>
            file.name.toLowerCase().endsWith(extension)
        );
    }

    function clearFileSelection() {
        fileInput.value = "";

        clearButton.hidden = true;
        clearButton.disabled = false;

        const savedResumeId =
            sessionStorage.getItem("resume_id");

        const savedFileName =
            sessionStorage.getItem("resume_file_name");

        if (savedResumeId) {
            fileNameElement.textContent =
                `Uploaded resume: ${savedFileName || "Saved resume"}`;

            fileNameElement.hidden = false;
        } else {
            fileNameElement.textContent = "";
            fileNameElement.hidden = true;
        }

        showDashboardMessage(
            savedResumeId
                ? "Local file selection cleared. Your uploaded resume is still stored. Use Delete Uploaded Resume to remove it."
                : "File selection cleared. You can choose another resume.",
            "info"
        );
    }

    restoreUploadedResumeDisplay();

    fileInput.addEventListener("change", () => {
        const file = fileInput.files?.[0];

        if (!file) {
            clearFileSelection();
            return;
        }

        if (!isSupportedFile(file)) {
            fileInput.value = "";
            clearFileSelection();

            showDashboardMessage(
                "Unsupported file type. Please select a PDF or DOCX file.",
                "error"
            );

            return;
        }

        fileNameElement.textContent =
            `Selected file: ${file.name}`;

        fileNameElement.hidden = false;
        clearButton.hidden = false;
        clearButton.disabled = false;

        showDashboardMessage(
            `Selected ${file.name}. Click Upload Resume when you are ready.`,
            "info"
        );
    });

    clearButton.addEventListener("click", () => {
        clearFileSelection();
    });


    /* -------------------------------------
       UPLOAD RESUME
       ------------------------------------- */

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const file = fileInput.files?.[0];

        if (!file) {
            showDashboardMessage(
                "Please select a resume before uploading.",
                "error"
            );

            return;
        }

        if (!isSupportedFile(file)) {
            showDashboardMessage(
                "Only PDF and DOCX files are supported.",
                "error"
            );

            return;
        }

        if (sessionStorage.getItem("resume_id")) {
            showDashboardMessage(
                "You already have an uploaded resume. Delete it first if you want to upload a replacement.",
                "info"
            );

            return;
        }

        const authorization = getAuthorizationHeader();

        if (!authorization) {
            redirectToLogin();
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        uploadButton.disabled = true;
        uploadButton.textContent = "Uploading...";
        clearButton.disabled = true;

        if (deleteButton) {
            deleteButton.disabled = true;
        }

        if (analyzeButton) {
            analyzeButton.disabled = true;
        }

        showDashboardMessage(
            "Uploading your resume. Please wait...",
            "info"
        );

        try {
            const response = await fetch(RESUME_UPLOAD_URL, {
                method: "POST",
                headers: {
                    Authorization: authorization
                },
                body: formData
            });

            const result = await readApiResponse(response);

            if (response.status === 401) {
                redirectToLogin(
                    "Your session has expired. Please log in again."
                );

                return;
            }

            if (!response.ok) {
                throw new Error(
                    getApiErrorMessage(
                        result,
                        "Resume upload failed. Please try again."
                    )
                );
            }

            const resumeId =
                result.resume_id ??
                result.id ??
                result.resume?.resume_id ??
                result.resume?.id;

            if (resumeId === undefined || resumeId === null) {
                throw new Error(
                    "The server did not return a resume ID after upload."
                );
            }

            const uploadedName =
                result.file_name ||
                result.filename ||
                result.resume?.file_name ||
                file.name;

            sessionStorage.setItem("resume_id", String(resumeId));
            sessionStorage.setItem(
                "resume_file_name",
                String(uploadedName)
            );

            setText("resumeStat", "Uploaded");

            fileNameElement.textContent =
                `Uploaded successfully: ${uploadedName}`;

            fileNameElement.hidden = false;
            clearButton.hidden = true;

            if (deleteButton) {
                deleteButton.hidden = false;
                deleteButton.disabled = false;
            }

            if (analyzeButton) {
                analyzeButton.hidden = false;
                analyzeButton.disabled = false;
                analyzeButton.textContent = "Analyze Resume";
            }

            clearResumeSkillResults();
            clearJobRecommendations();

            showDashboardMessage(
                result.message ||
                `Resume uploaded successfully: ${uploadedName}. Click Analyze Resume to extract skills and find matching jobs.`,
                "success"
            );

        } catch (error) {
            showDashboardMessage(
                error.message ||
                "Could not connect to the server. Please try again.",
                "error"
            );

        } finally {
            uploadButton.disabled = false;
            uploadButton.textContent = "Upload Resume";
            clearButton.disabled = false;

            if (deleteButton) {
                deleteButton.disabled = false;
            }

            if (analyzeButton) {
                analyzeButton.disabled = false;
            }
        }
    });


    /* -------------------------------------
       DELETE UPLOADED RESUME
       ------------------------------------- */

    if (deleteButton) {
        deleteButton.addEventListener("click", async () => {
            const resumeId =
                sessionStorage.getItem("resume_id");

            if (!resumeId) {
                deleteButton.hidden = true;

                if (analyzeButton) {
                    analyzeButton.hidden = true;
                }

                showDashboardMessage(
                    "No uploaded resume was found in this session.",
                    "error"
                );

                return;
            }

            const confirmed = window.confirm(
                "Are you sure you want to permanently delete your uploaded resume? " +
                "The database record and associated extracted skill records will be removed. " +
                "This action cannot be undone."
            );

            if (!confirmed) {
                return;
            }

            const authorization = getAuthorizationHeader();

            if (!authorization) {
                redirectToLogin();
                return;
            }

            deleteButton.disabled = true;
            deleteButton.textContent = "Deleting...";

            uploadButton.disabled = true;
            clearButton.disabled = true;

            if (analyzeButton) {
                analyzeButton.disabled = true;
            }

            showDashboardMessage(
                "Deleting your uploaded resume. Please wait...",
                "info"
            );

            try {
                const response = await fetch(
                    `/api/resume/${encodeURIComponent(resumeId)}`,
                    {
                        method: "DELETE",
                        headers: {
                            Authorization: authorization,
                            Accept: "application/json"
                        }
                    }
                );

                const result = await readApiResponse(response);

                if (response.status === 401) {
                    redirectToLogin(
                        "Your session has expired. Please log in again."
                    );

                    return;
                }

                if (response.status === 404) {
                    sessionStorage.removeItem("resume_id");
                    sessionStorage.removeItem("resume_file_name");

                    resetResumeDisplay();

                    throw new Error(
                        "The resume was not found for your account. The local resume reference has been cleared."
                    );
                }

                if (!response.ok) {
                    throw new Error(
                        getApiErrorMessage(
                            result,
                            "Failed to delete the uploaded resume."
                        )
                    );
                }

                sessionStorage.removeItem("resume_id");
                sessionStorage.removeItem("resume_file_name");

                resetResumeDisplay();

                showDashboardMessage(
                    result.message || "Resume deleted successfully.",
                    result.file_deleted === false ? "info" : "success"
                );

            } catch (error) {
                showDashboardMessage(
                    error.message ||
                    "Could not delete the resume. Please try again.",
                    "error"
                );

            } finally {
                uploadButton.disabled = false;
                uploadButton.textContent = "Upload Resume";

                clearButton.disabled = false;

                deleteButton.disabled = false;
                deleteButton.textContent = "Delete Uploaded Resume";

                if (!sessionStorage.getItem("resume_id")) {
                    deleteButton.hidden = true;
                }

                if (analyzeButton) {
                    analyzeButton.disabled = false;
                    analyzeButton.textContent = "Analyze Resume";

                    analyzeButton.hidden =
                        !sessionStorage.getItem("resume_id");
                }
            }
        });
    }
}


/* =========================================
   ANALYZE RESUME AND EXTRACT SKILLS
   ========================================= */

function setupResumeSkillExtraction() {
    const analyzeButton =
        document.getElementById("analyzeResumeButton");

    if (!analyzeButton) {
        return;
    }

    analyzeButton.addEventListener("click", async () => {
        const resumeId =
            sessionStorage.getItem("resume_id");

        if (!resumeId) {
            showDashboardMessage(
                "Please upload a resume before analyzing it.",
                "error"
            );

            analyzeButton.hidden = true;
            return;
        }

        const authorization = getAuthorizationHeader();

        if (!authorization) {
            redirectToLogin();
            return;
        }

        analyzeButton.disabled = true;
        analyzeButton.textContent = "Analyzing...";

        clearResumeSkillResults();
        clearJobRecommendations();

        showDashboardMessage(
            "Analyzing your resume and extracting skills. Please wait...",
            "info"
        );

        try {
            const response = await fetch(
                `/api/resume/${encodeURIComponent(resumeId)}/extract-skills`,
                {
                    method: "POST",
                    headers: {
                        Authorization: authorization,
                        Accept: "application/json"
                    }
                }
            );

            const result = await readApiResponse(response);

            if (response.status === 401) {
                redirectToLogin(
                    "Your session has expired. Please log in again."
                );

                return;
            }

            if (response.status === 404) {
                sessionStorage.removeItem("resume_id");
                sessionStorage.removeItem("resume_file_name");

                resetResumeDisplay();

                throw new Error(
                    getApiErrorMessage(
                        result,
                        "The uploaded resume was not found. Please upload it again."
                    )
                );
            }

            if (!response.ok) {
                throw new Error(
                    getApiErrorMessage(
                        result,
                        "Resume analysis failed. Please try again."
                    )
                );
            }

            const skills = getSkillsFromResponse(result);

            if (skills === null) {
                throw new Error(
                    "The analysis response did not contain a recognizable skills list."
                );
            }

            displayExtractedSkills(skills);
            setText("resumeStat", "Analyzed");

            const recognizedCount = skills.filter(
                (skill) => getSkillName(skill).length > 0
            ).length;

            if (recognizedCount > 0) {
                await loadRecommendedJobs();

                showDashboardMessage(
                    `Resume analysis completed. Found ${recognizedCount} skill(s).`,
                    "success"
                );

            } else {
                clearJobRecommendations();

                showDashboardMessage(
                    "Resume analysis completed, but no recognizable skills were returned.",
                    "info"
                );
            }

        } catch (error) {
            showDashboardMessage(
                error.message ||
                "Could not analyze your resume. Please try again.",
                "error"
            );

        } finally {
            analyzeButton.disabled = false;
            analyzeButton.textContent = "Analyze Resume";

            analyzeButton.hidden =
                !sessionStorage.getItem("resume_id");
        }
    });
}


/* =========================================
   RECOMMENDED JOBS INITIALIZATION
   ========================================= */

function setupRecommendedJobs() {
    if (sessionStorage.getItem("resume_id")) {
        loadRecommendedJobs();
    }
}


/* =========================================
   FORMAT JOB SALARY
   ========================================= */

function formatJobSalary(job) {
    const minimum = job.salary_min;
    const maximum = job.salary_max;

    const currency = job.currency
        ? `${job.currency} `
        : "";

    if (minimum == null && maximum == null) {
        return "Salary not specified";
    }

    if (minimum != null && maximum != null) {
        return `${currency}${minimum} – ${currency}${maximum}`;
    }

    if (minimum != null) {
        return `From ${currency}${minimum}`;
    }

    return `Up to ${currency}${maximum}`;
}


/* =========================================
   RENDER ONE RECOMMENDED JOB CARD
   ========================================= */

function createRecommendedJobCard(job) {
    const card = document.createElement("article");

    card.className = "job-match-card";

    const top = document.createElement("div");
    top.className = "job-match-card-top";

    const titleArea = document.createElement("div");

    titleArea.appendChild(
        createTextElement(
            "h3",
            "job-match-title",
            job.title || "Untitled job"
        )
    );

    titleArea.appendChild(
        createTextElement(
            "p",
            "job-match-company",
            job.company_name || "Company not specified"
        )
    );

    const numericScore = Number(job.match_score);

    const scoreText = Number.isFinite(numericScore)
        ? `${numericScore}% match`
        : "Match score unavailable";

    top.appendChild(titleArea);

    top.appendChild(
        createTextElement(
            "span",
            "job-match-score",
            scoreText
        )
    );

    card.appendChild(top);

    const information = document.createElement("div");

    information.className = "job-match-information";

    information.textContent = [
        job.location,
        job.employment_type,
        formatJobSalary(job)
    ].filter(Boolean).join("  •  ");

    card.appendChild(information);

    if (job.description) {
        card.appendChild(
            createTextElement(
                "p",
                "job-match-description",
                job.description
            )
        );
    }

    appendJobSkillTags(
        card,
        "Skills you have",
        job.matched_skills,
        "matched",
        "No matching skills listed"
    );

    appendJobSkillTags(
        card,
        "Skills to improve",
        job.missing_skills,
        "missing",
        "All listed job skills match your resume"
    );

    return card;
}


/* =========================================
   JOB SKILL TAGS
   ========================================= */

function appendJobSkillTags(
    card,
    heading,
    skillValues,
    tagType,
    emptyText
) {
    const skills = Array.isArray(skillValues)
        ? skillValues
        : [];

    const section = document.createElement("div");
    section.className = "job-match-skill-section";

    section.appendChild(
        createTextElement(
            "strong",
            "job-match-skill-heading",
            `${heading} (${skills.length})`
        )
    );

    const tags = document.createElement("div");
    tags.className = "job-match-skill-tags";

    if (skills.length > 0) {
        skills.forEach((skill) => {
            const name = getSkillName(skill);

            if (!name) {
                return;
            }

            tags.appendChild(
                createTextElement(
                    "span",
                    `job-skill-tag ${tagType}`,
                    name
                )
            );
        });

        if (!tags.children.length) {
            tags.appendChild(
                createTextElement(
                    "span",
                    "job-match-muted",
                    emptyText
                )
            );
        }

    } else {
        tags.appendChild(
            createTextElement(
                "span",
                "job-match-muted",
                emptyText
            )
        );
    }

    section.appendChild(tags);
    card.appendChild(section);
}


/* =========================================
   LOAD RECOMMENDED JOBS FROM FASTAPI
   ========================================= */

async function loadRecommendedJobs() {
    const requestId = ++latestJobsRequest;

    const jobsList =
        document.getElementById("recommendedJobsList");

    const jobsEmpty =
        document.getElementById("recommendedJobsEmpty");

    if (!jobsList || !jobsEmpty) {
        return;
    }

    const resumeId =
        sessionStorage.getItem("resume_id");

    if (!resumeId) {
        clearJobRecommendations();
        return;
    }

    const authorization = getAuthorizationHeader();

    if (!authorization) {
        redirectToLogin();
        return;
    }

    jobsList.replaceChildren();
    jobsEmpty.hidden = true;

    clearSkillGapAnalysis();
    clearRecommendedCourses();

    showJobRecommendationsMessage(
        "Finding jobs that match your resume skills...",
        "info"
    );

    try {
        const response = await fetch(
            RECOMMENDED_JOBS_URL,
            {
                method: "GET",
                headers: {
                    Authorization: authorization,
                    Accept: "application/json"
                }
            }
        );

        const result = await readApiResponse(response);

        if (requestId !== latestJobsRequest) {
            return;
        }

        if (response.status === 401) {
            redirectToLogin(
                "Your session has expired. Please log in again."
            );

            return;
        }

        if (!response.ok) {
            throw new Error(
                getApiErrorMessage(
                    result,
                    "Could not load recommended jobs."
                )
            );
        }

        const jobs = Array.isArray(result.jobs)
            ? result.jobs
            : [];

        if (jobs.length === 0) {
            jobsEmpty.hidden = false;

            const heading = jobsEmpty.querySelector("h3");
            const paragraph = jobsEmpty.querySelector("p");

            if (heading) {
                heading.textContent =
                    "No matching jobs found yet";
            }

            if (paragraph) {
                paragraph.textContent =
                    "No active jobs with matching skills were found. Add jobs and link their required skills in SkillBridge to receive recommendations.";
            }

            setText("jobMatchesStat", "0");

            displaySkillGapAnalysis([]);

            clearRecommendedCourses(
                "No matching jobs were found, so job-based course recommendations are not available yet.",
                0
            );

            showJobRecommendationsMessage(
                "There are no matching job records to display yet.",
                "info"
            );

            return;
        }

        jobs.forEach((job) => {
            jobsList.appendChild(
                createRecommendedJobCard(job)
            );
        });

        jobsEmpty.hidden = true;

        setText("jobMatchesStat", String(jobs.length));

        displaySkillGapAnalysis(jobs);

        showJobRecommendationsMessage(
            `Found ${jobs.length} matching job(s), ranked by skill match.`,
            "success"
        );

        // Request course suggestions for missing skills in each matching job.
        await loadRecommendedCourses(jobs);

    } catch (error) {
        if (requestId !== latestJobsRequest) {
            return;
        }

        jobsList.replaceChildren();
        jobsEmpty.hidden = false;

        const heading = jobsEmpty.querySelector("h3");
        const paragraph = jobsEmpty.querySelector("p");

        if (heading) {
            heading.textContent = "Unable to load job matches";
        }

        if (paragraph) {
            paragraph.textContent =
                "Check your connection and backend API, then analyze your resume again.";
        }

        clearSkillGapAnalysis();

        clearRecommendedCourses(
            "Course recommendations are unavailable until job matching succeeds.",
            "—"
        );

        showJobRecommendationsMessage(
            error.message ||
            "Could not load recommended jobs. Please try again.",
            "error"
        );
    }
}


/* =========================================
   COURSE RECOMMENDATIONS INITIALIZATION
   ========================================= */

function setupCourseRecommendations() {
    clearRecommendedCourses();
}


/* =========================================
   SAFE COURSE URL
   ========================================= */

function getSafeCourseUrl(rawUrl) {
    if (
        typeof rawUrl !== "string" ||
        !rawUrl.trim()
    ) {
        return "";
    }

    try {
        const parsedUrl = new URL(rawUrl.trim());

        if (
            parsedUrl.protocol !== "https:" &&
            parsedUrl.protocol !== "http:"
        ) {
            return "";
        }

        return parsedUrl.href;

    } catch {
        return "";
    }
}


/* =========================================
   LOAD COURSES FOR ONE JOB
   ========================================= */

async function fetchCoursesForJob(
    resumeId,
    jobId,
    authorization
) {
    const response = await fetch(
        COURSE_RECOMMENDATION_URL(resumeId, jobId),
        {
            method: "GET",
            headers: {
                Authorization: authorization,
                Accept: "application/json"
            }
        }
    );

    const result = await readApiResponse(response);

    if (response.status === 401) {
        const error = new Error(
            "Your session has expired. Please log in again."
        );

        error.status = 401;
        throw error;
    }

    if (!response.ok) {
        const error = new Error(
            getApiErrorMessage(
                result,
                `Could not load courses for job ${jobId}.`
            )
        );

        error.status = response.status;
        throw error;
    }

    return result;
}


/* =========================================
   COURSE CARD
   ========================================= */

function createRecommendedCourseCard(course) {
    const card = document.createElement("article");

    card.className = "job-match-card course-card";

    const top = document.createElement("div");
    top.className = "job-match-card-top";

    const titleArea = document.createElement("div");

    titleArea.appendChild(
        createTextElement(
            "h3",
            "job-match-title",
            course.title || "Untitled course"
        )
    );

    titleArea.appendChild(
        createTextElement(
            "p",
            "job-match-company",
            course.provider || "Learning provider not specified"
        )
    );

    top.appendChild(titleArea);

    top.appendChild(
        createTextElement(
            "span",
            "job-match-score",
            course.is_free ? "Free course" : "Paid course"
        )
    );

    card.appendChild(top);

    if (course.description) {
        card.appendChild(
            createTextElement(
                "p",
                "job-match-description",
                course.description
            )
        );
    }

    const details = [
        course.level,
        course.duration
    ].filter(
        (value) =>
            value !== undefined &&
            value !== null &&
            String(value).trim() !== ""
    );

    if (details.length > 0) {
        card.appendChild(
            createTextElement(
                "p",
                "job-match-information",
                details.join(" • ")
            )
        );
    }

    /*
     * A course may be recommended for multiple missing skills.
     * Display each related skill only once.
     */

    const relatedSkills = Array.from(
        course.relatedSkills || []
    ).sort((first, second) => first.localeCompare(second));

    if (relatedSkills.length > 0) {
        const skillSection = document.createElement("div");

        skillSection.className = "job-match-skill-section";

        skillSection.appendChild(
            createTextElement(
                "strong",
                "job-match-skill-heading",
                "Recommended for missing skills"
            )
        );

        const tags = document.createElement("div");

        tags.className = "job-match-skill-tags";

        relatedSkills.forEach((skillName) => {
            tags.appendChild(
                createTextElement(
                    "span",
                    "job-skill-tag missing",
                    skillName
                )
            );
        });

        skillSection.appendChild(tags);
        card.appendChild(skillSection);
    }

    /*
     * Show job titles that recommended this course.
     */

    const relatedJobs = Array.from(
        course.recommendedForJobs || []
    ).filter(Boolean);

    if (relatedJobs.length > 0) {
        card.appendChild(
            createTextElement(
                "p",
                "job-match-information",
                `Relevant jobs: ${relatedJobs.join(", ")}`
            )
        );
    }

    const courseUrl = getSafeCourseUrl(course.url);

    if (courseUrl) {
        const link = document.createElement("a");

        link.className = "button course-link";
        link.href = courseUrl;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "View Course";

        card.appendChild(link);

    } else {
        card.appendChild(
            createTextElement(
                "p",
                "job-match-muted",
                "Course link is not available."
            )
        );
    }

    return card;
}


/* =========================================
   LOAD RECOMMENDED COURSES
   ========================================= */

async function loadRecommendedCourses(jobs) {
    const requestId = ++latestCoursesRequest;

    const coursesList =
        document.getElementById("recommendedCoursesList");

    const coursesEmpty =
        document.getElementById("coursesEmpty");

    if (!coursesList || !coursesEmpty) {
        return;
    }

    const resumeId =
        sessionStorage.getItem("resume_id");

    if (!resumeId) {
        clearRecommendedCourses(
            "Upload and analyze your resume to receive course recommendations."
        );

        return;
    }

    /*
     * The jobs API returns missing_skills as a list of names.
     * Course recommendations need a job ID for each matching job.
     */

    const jobsWithGaps = (Array.isArray(jobs) ? jobs : [])
        .filter((job) =>
            Array.isArray(job.missing_skills) &&
            job.missing_skills.length > 0 &&
            job.job_id !== undefined &&
            job.job_id !== null
        );

    if (jobsWithGaps.length === 0) {
        clearRecommendedCourses(
            "No missing job skills were found. Courses will appear here when a recommended job has skills to improve.",
            0
        );

        showCourseMessage(
            "No course recommendations are needed for the current job matches.",
            "info"
        );

        return;
    }

    const authorization = getAuthorizationHeader();

    if (!authorization) {
        redirectToLogin();
        return;
    }

    coursesList.replaceChildren();
    coursesEmpty.hidden = true;

    setText("coursesStat", "…");

    showCourseMessage(
        "Finding courses for your missing skills...",
        "info"
    );

    try {
        /*
         * The backend requires one request per job:
         * GET /api/courses/recommendations/resume/{resume_id}/job/{job_id}
         *
         * Run those requests concurrently.
         */

        const responses = await Promise.allSettled(
            jobsWithGaps.map((job) =>
                fetchCoursesForJob(
                    resumeId,
                    job.job_id,
                    authorization
                ).then((result) => ({
                    job,
                    result
                }))
            )
        );

        // Ignore responses from a previous analysis.
        if (requestId !== latestCoursesRequest) {
            return;
        }

        /*
         * Authentication expiry should not be treated as an ordinary
         * course recommendation failure.
         */

        const authenticationFailure = responses.find(
            (item) =>
                item.status === "rejected" &&
                item.reason?.status === 401
        );

        if (authenticationFailure) {
            redirectToLogin(
                "Your session has expired. Please log in again."
            );

            return;
        }

        const courseMap = new Map();

        const errors = [];

        let successfulResponses = 0;

        responses.forEach((entry) => {
            if (entry.status === "rejected") {
                errors.push(
                    entry.reason?.message ||
                    "A course recommendation request failed."
                );

                return;
            }

            successfulResponses++;

            const { job, result } = entry.value;

            const groups = Array.isArray(result.recommendations)
                ? result.recommendations
                : [];

            groups.forEach((group) => {
                const skillName = group.skill_name || "";

                const courses = Array.isArray(group.courses)
                    ? group.courses
                    : [];

                courses.forEach((course) => {
                    if (!course || typeof course !== "object") {
                        return;
                    }

                    const url = getSafeCourseUrl(course.url);

                    /*
                     * Prefer the database course ID for deduplication.
                     * Fall back to the course URL or title/provider.
                     */

                    const key = course.id != null
                        ? `id:${course.id}`
                        : (
                            url
                                ? `url:${url.toLowerCase()}`
                                : `name:${String(course.title || "").toLowerCase()}|${String(course.provider || "").toLowerCase()}`
                        );

                    if (!courseMap.has(key)) {
                        courseMap.set(key, {
                            ...course,
                            url,
                            relatedSkills: new Set(),
                            recommendedForJobs: new Set()
                        });
                    }

                    const savedCourse = courseMap.get(key);

                    const relatedSkill =
                        skillName || course.skill_name;

                    if (
                        typeof relatedSkill === "string" &&
                        relatedSkill.trim()
                    ) {
                        savedCourse.relatedSkills.add(
                            relatedSkill.trim()
                        );
                    }

                    const jobTitle =
                        job.title ||
                        job.job_title ||
                        result.job_title;

                    if (
                        typeof jobTitle === "string" &&
                        jobTitle.trim()
                    ) {
                        savedCourse.recommendedForJobs.add(
                            jobTitle.trim()
                        );
                    }
                });
            });
        });

        /*
         * Show free courses first, followed by course titles.
         */

        const courses = Array.from(courseMap.values()).sort(
            (first, second) => {
                if (
                    Boolean(first.is_free) !==
                    Boolean(second.is_free)
                ) {
                    return first.is_free ? -1 : 1;
                }

                return String(first.title || "").localeCompare(
                    String(second.title || "")
                );
            }
        );

        courses.forEach((course) => {
            coursesList.appendChild(
                createRecommendedCourseCard(course)
            );
        });

        const displayedCount = coursesList.children.length;

        setText("coursesStat", String(displayedCount));

        coursesEmpty.hidden = displayedCount > 0;

        if (displayedCount === 0) {
            const paragraph = coursesEmpty.querySelector("p");

            if (paragraph) {
                paragraph.textContent =
                    "No active courses are linked to the missing skills in your job matches yet. Add active courses linked to those skills in the database.";
            }

            if (
                errors.length > 0 &&
                successfulResponses === 0
            ) {
                showCourseMessage(
                    `Course recommendations could not be loaded: ${errors[0]}`,
                    "error"
                );

            } else {
                showCourseMessage(
                    "No active courses were found for your missing skills.",
                    "info"
                );
            }

            return;
        }

        if (errors.length > 0) {
            showCourseMessage(
                `Loaded ${displayedCount} unique course(s). Some job-specific course requests could not be completed.`,
                "info"
            );

        } else {
            showCourseMessage(
                `Found ${displayedCount} unique course(s) for your missing skills. Duplicate courses are displayed only once.`,
                "success"
            );
        }

    } catch (error) {
        if (requestId !== latestCoursesRequest) {
            return;
        }

        clearRecommendedCourses(
            "Course recommendations could not be loaded. Check the backend and try again.",
            "—"
        );

        showCourseMessage(
            error.message ||
            "Could not load recommended courses.",
            "error"
        );

        console.error(
            "Course recommendation error:",
            error
        );
    }
}