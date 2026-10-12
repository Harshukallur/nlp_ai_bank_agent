
/* =========================================================
   AUTHENTICATION
========================================================= */

const authScreen = document.getElementById("authScreen");
const appScreen = document.getElementById("appScreen");
const authForm = document.getElementById("authForm");
const authTitle = document.getElementById("authTitle");
const authDescription = document.getElementById("authDescription");
const authSubmit = document.getElementById("authSubmit");
const authSwitchText = document.getElementById("authSwitchText");
const authSwitchButton = document.getElementById("authSwitchButton");
const authMessage = document.getElementById("authMessage");
const authUsername = document.getElementById("authUsername");
const authPassword = document.getElementById("authPassword");
const currentUsername = document.getElementById("currentUsername");
const logoutButton = document.getElementById("logoutButton");

let authMode = "login";
let currentUser = null;


/* =========================================================
   DASHBOARD ELEMENTS
========================================================= */

const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const chatMessages = document.getElementById("chatMessages");

const homeNav = document.getElementById("homeNav");
const accountNav = document.getElementById("accountNav");
const activityNav = document.getElementById("activityNav");
const settingsNav = document.getElementById("settingsNav");

const homeSection = document.getElementById("homeSection");
const accountSection = document.getElementById("accountSection");
const activitySection = document.getElementById("activitySection");
const settingsSection = document.getElementById("settingsSection");


/* =========================================================
   AUTH MODE: LOGIN / REGISTER
========================================================= */

function setAuthMode(mode) {
    authMode = mode;
    authForm.reset();
    authMessage.textContent = "";
    authMessage.className = "";

    if (mode === "register") {
        authTitle.textContent = "Create your account";
        authDescription.textContent =
            "Register to create your own private banking workspace.";
        authSubmit.textContent = "Register";
        authSwitchText.textContent = "Already registered?";
        authSwitchButton.textContent = "Log in";
        authPassword.autocomplete = "new-password";
    } else {
        authTitle.textContent = "Welcome back";
        authDescription.textContent =
            "Log in to access your account.";
        authSubmit.textContent = "Log in";
        authSwitchText.textContent = "New here?";
        authSwitchButton.textContent = "Create an account";
        authPassword.autocomplete = "current-password";
    }
}

authSwitchButton.addEventListener("click", () => {
    setAuthMode(authMode === "login" ? "register" : "login");
});


/* =========================================================
   AUTHENTICATION REQUEST
========================================================= */

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = authUsername.value.trim();
    const password = authPassword.value;

    if (!username || !password) {
        showAuthMessage("Enter both username and password.", true);
        return;
    }

    if (authMode === "register" && password.length < 8) {
        showAuthMessage("Password must contain at least 8 characters.", true);
        return;
    }

    authSubmit.disabled = true;
    authSubmit.textContent =
        authMode === "register" ? "Registering..." : "Logging in...";

    try {
        const endpoint =
            authMode === "register" ? "/api/register" : "/api/login";

        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok || data.status !== "success") {
            showAuthMessage(
                data.message || "Authentication failed. Please try again.",
                true
            );
            return;
        }

        if (authMode === "register") {
            showAuthMessage(
                "Registration successful! You can now log in.",
                false
            );
            setAuthMode("login");
            authUsername.value = username;
            authPassword.focus();
        } else {
            await checkSession();
        }
    } catch (error) {
        console.error("Authentication error:", error);
        showAuthMessage(
            "Unable to connect to the server. Check that Flask is running.",
            true
        );
    } finally {
        authSubmit.disabled = false;
        authSubmit.textContent =
            authMode === "register" ? "Register" : "Log in";
    }
});

function showAuthMessage(message, isError) {
    authMessage.textContent = message;
    authMessage.className = isError ? "auth-error" : "auth-success";
}


/* =========================================================
   SESSION CHECK
========================================================= */

async function checkSession() {
    try {
        const response = await fetch("/api/me", {
            credentials: "same-origin",
            cache: "no-store"
        });

        if (!response.ok) {
            showLoginScreen();
            return;
        }

        const data = await response.json();

        if (data.status === "success" && data.user) {
            currentUser = data.user;
            showDashboard();
        } else {
            showLoginScreen();
        }
    } catch (error) {
        console.error("Session check failed:", error);
        showLoginScreen();
        showAuthMessage("Unable to verify your session. Please log in.", true);
    }
}

function showLoginScreen() {
    currentUser = null;
    appScreen.hidden = true;
    authScreen.hidden = false;
}

async function showDashboard() {
    authScreen.hidden = true;
    appScreen.hidden = false;

    currentUsername.textContent = currentUser.username;

    // Clear messages from any previous session.
    chatMessages.innerHTML = "";
    addMessage(
        `Welcome, ${currentUser.username}! How can I help you with your account?`,
        "assistant"
    );

    showHome();

    // Load data only after the server confirms the session.
    await Promise.all([loadAccount(), loadActivity()]);
}


/* =========================================================
   LOGOUT
========================================================= */

logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;

    try {
        const response = await fetch("/api/logout", {
            method: "POST",
            credentials: "same-origin"
        });

        const data = await response.json();

        if (!response.ok || data.status !== "success") {
            alert(data.message || "Logout failed. Please try again.");
            return;
        }

        currentUser = null;
        input.value = "";
        showLoginScreen();
        setAuthMode("login");
        showAuthMessage("You have logged out successfully.", false);
    } catch (error) {
        console.error("Logout error:", error);
        alert("Unable to contact the server. Please try again.");
    } finally {
        logoutButton.disabled = false;
    }
});


/* =========================================================
   ADD CHAT MESSAGE
========================================================= */

function addMessage(message, type) {
    const wrapper = document.createElement("div");

    wrapper.className =
        type === "user" ? "user-message" : "assistant-message";

    wrapper.style.marginBottom = "18px";

    if (type === "user") {
        wrapper.style.display = "flex";
        wrapper.style.justifyContent = "flex-end";

        const bubble = document.createElement("div");
        bubble.className = "message";
        bubble.style.background = "#6366f1";
        bubble.style.color = "white";
        bubble.textContent = message;

        wrapper.appendChild(bubble);
    } else {
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = "AI";

        const bubble = document.createElement("div");
        bubble.className = "message";
        bubble.textContent = message;

        wrapper.append(avatar, bubble);
    }

    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}


/* =========================================================
   SEND CHAT MESSAGE
========================================================= */

async function sendMessage() {
    if (!currentUser) {
        showLoginScreen();
        return;
    }

    const message = input.value.trim();

    if (!message || sendButton.disabled) return;

    addMessage(message, "user");
    input.value = "";
    sendButton.disabled = true;
    sendButton.textContent = "Processing...";

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        if (response.status === 401) {
            showLoginScreen();
            showAuthMessage("Your session expired. Please log in again.", true);
            return;
        }

        if (data.status === "success") {
            addMessage(
                data.message || "Request completed successfully.",
                "assistant"
            );
            await Promise.all([loadAccount(), loadActivity()]);
        } else {
            addMessage(
                data.message || "The request could not be completed.",
                "assistant"
            );
        }
    } catch (error) {
        console.error("Chat error:", error);
        addMessage(
            "Unable to connect to the AI Account Assistant.",
            "assistant"
        );
    } finally {
        sendButton.disabled = false;
        sendButton.textContent = "Send";
    }
}


/* =========================================================
   LOAD CURRENT USER'S ACCOUNT
========================================================= */

async function loadAccount() {
    try {
        const response = await fetch("/api/account", {
            credentials: "same-origin",
            cache: "no-store"
        });

        if (response.status === 401) {
            showLoginScreen();
            return;
        }

        const data = await response.json();

        const accountId = document.getElementById("accountId");
        const accountType = document.getElementById("accountType");
        const accountBalance = document.getElementById("accountBalance");
        const accountCurrency = document.getElementById("accountCurrency");

        if (data.status === "success" && data.account) {
            const account = data.account;

            accountId.textContent = account.account_id || "No account";
            accountType.textContent = account.account_type
                ? account.account_type.charAt(0).toUpperCase() +
                  account.account_type.slice(1)
                : "—";

            const balance = Number(account.balance);
            accountBalance.textContent =
                `${account.currency === "INR" ? "₹" : ""}` +
                (Number.isFinite(balance) ? balance.toLocaleString("en-IN") : "0");

            accountCurrency.textContent = account.currency || "INR";
        } else {
            accountId.textContent = "No account";
            accountType.textContent = "—";
            accountBalance.textContent = "₹0";
            accountCurrency.textContent = "INR";
        }
    } catch (error) {
        console.error("Unable to load account:", error);
    }
}


/* =========================================================
   LOAD CURRENT USER'S ACTIVITY
========================================================= */

async function loadActivity() {
    const activityList = document.getElementById("activityList");

    try {
        const response = await fetch("/api/activity", {
            credentials: "same-origin",
            cache: "no-store"
        });

        if (response.status === 401) {
            showLoginScreen();
            return;
        }

        const data = await response.json();
        activityList.replaceChildren();

        if (
            !response.ok ||
            !Array.isArray(data.activity) ||
            data.activity.length === 0
        ) {
            const empty = document.createElement("div");
            empty.className = "activity-empty";
            empty.textContent = "No activity yet.";
            activityList.appendChild(empty);
            return;
        }

        data.activity.slice().reverse().forEach((activity) => {
            const item = document.createElement("div");
            item.className = "activity-item";

            const check = document.createElement("div");
            check.className = "activity-check";
            check.textContent = "✓";

            const details = document.createElement("div");
            const title = document.createElement("strong");
            const description = document.createElement("span");

            title.textContent = activity.action || "Account activity";
            description.textContent =
                activity.description || "Account operation completed.";

            details.append(title, description);
            item.append(check, details);
            activityList.appendChild(item);
        });
    } catch (error) {
        console.error("Unable to load activity:", error);
        activityList.textContent = "Unable to load activity.";
    }
}


/* =========================================================
   NAVIGATION
========================================================= */

function setActiveNav(activeNav) {
    [homeNav, accountNav, activityNav, settingsNav].forEach((item) => {
        if (item) item.classList.remove("active");
    });

    if (activeNav) activeNav.classList.add("active");
}

function showHome() {
    homeSection.hidden = false;
    accountSection.hidden = false;
    activitySection.hidden = true;
    settingsSection.hidden = true;

    setActiveNav(homeNav);
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function showAccount() {
    homeSection.hidden = false;
    accountSection.hidden = false;
    activitySection.hidden = true;
    settingsSection.hidden = true;

    setActiveNav(accountNav);
    loadAccount();
    accountSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function showActivity() {
    homeSection.hidden = false;
    accountSection.hidden = false;
    activitySection.hidden = false;
    settingsSection.hidden = true;

    setActiveNav(activityNav);
    await loadActivity();
    activitySection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showSettings() {
    homeSection.hidden = false;
    accountSection.hidden = false;
    activitySection.hidden = true;
    settingsSection.hidden = false;

    setActiveNav(settingsNav);
    settingsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}


/* =========================================================
   EVENT LISTENERS
========================================================= */

homeNav.addEventListener("click", (event) => {
    event.preventDefault();
    showHome();
});

accountNav.addEventListener("click", (event) => {
    event.preventDefault();
    showAccount();
});

activityNav.addEventListener("click", (event) => {
    event.preventDefault();
    showActivity();
});

settingsNav.addEventListener("click", (event) => {
    event.preventDefault();
    showSettings();
});

sendButton.addEventListener("click", sendMessage);

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
});


/* =========================================================
   INITIAL PAGE LOAD
========================================================= */

setAuthMode("login");
checkSession();
