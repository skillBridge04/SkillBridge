
"use strict";

/*
 * =========================================
 * SKILLBRIDGE AUTHENTICATION FRONTEND
 * =========================================
 *
 * API endpoints:
 *
 * POST /api/auth/register
 * POST /api/auth/register/employer
 * POST /api/auth/login
 * GET  /api/auth/me
 *
 * Login is performed using the user's email
 * and password.
 */


/* =========================================
   API ENDPOINTS
   ========================================= */

const REGISTER_URL = "/api/auth/register";

const EMPLOYER_REGISTER_URL =
    "/api/auth/register/employer";

const LOGIN_URL = "/api/auth/login";

const CURRENT_USER_URL = "/api/auth/me";


/* =========================================
   INITIALIZE PAGE
   ========================================= */

document.addEventListener("DOMContentLoaded", () => {
    updateCopyrightYear();

    displayRegistrationNotice();

    setupPasswordToggles();

    const loginForm = document.getElementById("loginForm");

    const registerForm = document.getElementById("registerForm");

    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }

    if (registerForm) {
        registerForm.addEventListener(
            "submit",
            handleRegistration
        );
    }
});


/* =========================================
   UPDATE COPYRIGHT YEAR
   ========================================= */

function updateCopyrightYear() {
    const yearElement = document.getElementById("currentYear");

    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }
}


/* =========================================
   DISPLAY SUCCESS / ERROR MESSAGE
   ========================================= */

function displayMessage(message, type) {
    const messageElement = document.getElementById("formMessage");

    if (!messageElement) {
        return;
    }

    messageElement.textContent = message;

    messageElement.className = `form-message ${type}`;

    messageElement.hidden = false;
}


/* =========================================
   LOADING BUTTON
   ========================================= */

function setLoading(isLoading, defaultText) {
    const button = document.getElementById("submitButton");

    if (!button) {
        return;
    }

    button.disabled = isLoading;

    button.textContent = isLoading
        ? "Please wait..."
        : defaultText;
}


/* =========================================
   READ API RESPONSE
   ========================================= */

async function readResponse(response) {
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


/* =========================================
   EXTRACT API ERROR MESSAGE
   ========================================= */

function getErrorMessage(data, fallbackMessage) {
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

    return fallbackMessage;
}


/* =========================================
   SHOW / HIDE PASSWORD
   ========================================= */

function setupPasswordToggles() {
    const toggleButtons = document.querySelectorAll(
        "[data-toggle-password]"
    );

    toggleButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const inputId = button.dataset.togglePassword;

            const passwordInput =
                document.getElementById(inputId);

            if (!passwordInput) {
                return;
            }

            const shouldShow =
                passwordInput.type === "password";

            passwordInput.type = shouldShow
                ? "text"
                : "password";

            button.textContent = shouldShow
                ? "Hide"
                : "Show";

            button.setAttribute(
                "aria-label",
                shouldShow
                    ? "Hide password"
                    : "Show password"
            );

            button.setAttribute(
                "aria-pressed",
                String(shouldShow)
            );
        });
    });
}


/* =========================================
   LOGIN
   ========================================= */

async function handleLogin(event) {
    event.preventDefault();

    const form = event.currentTarget;

    const email = form.elements.email.value.trim();

    const password = form.elements.password.value;

    setLoading(true, "Log In");

    // Remove any previous login session.
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("token_type");

    try {

        /*
         * STEP 1:
         * Send email and password to the backend.
         *
         * OAuth2PasswordRequestForm expects:
         * username
         * password
         *
         * We send the email as username.
         */

        const formData = new URLSearchParams();

        formData.set("username", email);

        formData.set("password", password);

        const response = await fetch(LOGIN_URL, {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/x-www-form-urlencoded"
            },

            body: formData.toString()
        });

        const result = await readResponse(response);

        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    result,
                    "Login failed. Please check your email and password."
                )
            );
        }


        /*
         * STEP 2:
         * Extract the access token.
         */

        const accessToken =
            result.access_token || result.token;

        if (!accessToken) {
            throw new Error(
                "The login response did not contain an access token."
            );
        }


        /*
         * STEP 3:
         * Get the currently logged-in user's information.
         *
         * The backend /api/auth/me endpoint
         * returns the user's role.
         */

        const userResponse = await fetch(CURRENT_USER_URL, {
            method: "GET",

            headers: {
                "Authorization": `Bearer ${accessToken}`
            }
        });

        const user = await readResponse(userResponse);

        if (!userResponse.ok) {
            throw new Error(
                getErrorMessage(
                    user,
                    "Could not retrieve your account information."
                )
            );
        }


        /*
         * STEP 4:
         * Read and normalize the user's role.
         */

        const role = String(user.role || "")
            .trim()
            .toUpperCase()
            .replace(/[\s-]+/g, "_");


        /*
         * STEP 5:
         * Select the correct dashboard.
         */

        let dashboardURL;

        switch (role) {

            case "JOB_SEEKER":
                dashboardURL = "/dashboard";
                break;

            case "EMPLOYER":
                dashboardURL = "/employer-dashboard";
                break;

            case "ADMIN":
                dashboardURL = "/admin";
                break;

            default:
                throw new Error(
                    "Your account role is missing or not recognized. " +
                    "Please contact the administrator."
                );
        }


        /*
         * STEP 6:
         * Save the authenticated session.
         */

        sessionStorage.setItem(
            "access_token",
            accessToken
        );

        sessionStorage.setItem(
            "token_type",
            result.token_type || "bearer"
        );


        /*
         * STEP 7:
         * Display success message and redirect.
         */

        displayMessage(
            "Login successful! Opening your dashboard...",
            "success"
        );

        form.reset();

        window.setTimeout(() => {
            window.location.href = dashboardURL;
        }, 800);


    } catch (error) {

        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("token_type");

        displayMessage(
            error.message ||
            "Could not connect to SkillBridge. Please try again.",
            "error"
        );

    } finally {
        setLoading(false, "Log In");
    }
}


/* =========================================
   REGISTRATION
   ========================================= */

async function handleRegistration(event) {
    event.preventDefault();

    const form = event.currentTarget;

    const fullName =
        form.elements.full_name.value.trim();

    const email =
        form.elements.email.value.trim();

    const password =
        form.elements.password.value;

    const confirmPassword =
        form.elements.confirm_password.value;

    const role =
        form.elements.role.value;


    // Validate password confirmation.

    if (password !== confirmPassword) {
        displayMessage(
            "Your passwords do not match. Please try again.",
            "error"
        );

        return;
    }


    // Validate password length.

    if (password.length < 8) {
        displayMessage(
            "Your password must contain at least 8 characters.",
            "error"
        );

        return;
    }


    // Choose the correct registration endpoint.

    const registrationURL =
        role === "EMPLOYER"
            ? EMPLOYER_REGISTER_URL
            : REGISTER_URL;

    setLoading(true, "Create Account");

    try {

        const payload = {
            name: fullName,
            email: email,
            password: password
        };

        const response = await fetch(registrationURL, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(payload)
        });

        const result = await readResponse(response);

        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    result,
                    "Registration failed. Please check your information."
                )
            );
        }


        // Registration succeeded.

        form.reset();

        if (role === "EMPLOYER") {

            displayMessage(
                "Employer registration submitted successfully. " +
                "Your account requires Admin approval before you can use employer features.",
                "success"
            );

        } else {

            displayMessage(
                "Your account was created successfully. Redirecting to login...",
                "success"
            );

            window.setTimeout(() => {
                window.location.href =
                    "/login?registered=1";
            }, 1500);
        }

    } catch (error) {

        displayMessage(
            error.message ||
            "Could not connect to SkillBridge. Please try again.",
            "error"
        );

    } finally {
        setLoading(false, "Create Account");
    }
}


/* =========================================
   REGISTRATION SUCCESS NOTICE
   ========================================= */

function displayRegistrationNotice() {
    if (window.location.pathname !== "/login") {
        return;
    }

    const parameters = new URLSearchParams(
        window.location.search
    );

    if (parameters.get("registered") === "1") {
        displayMessage(
            "Your registration was successful. Please log in with your new account.",
            "success"
        );
    }
}

