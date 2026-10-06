/* =========================================================
   ELEMENTS
========================================================= */

const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const chatMessages = document.getElementById("chatMessages");


/* Navigation */

const homeNav = document.getElementById("homeNav");
const accountNav = document.getElementById("accountNav");
const activityNav = document.getElementById("activityNav");
const settingsNav = document.getElementById("settingsNav");


/* Sections */

const homeSection = document.getElementById("homeSection");
const accountSection = document.getElementById("accountSection");
const activitySection = document.getElementById("activitySection");
const settingsSection = document.getElementById("settingsSection");



/* =========================================================
   ADD CHAT MESSAGE
========================================================= */

function addMessage(message, type) {

    const wrapper = document.createElement("div");

    wrapper.className =
        type === "user"
            ? "user-message"
            : "assistant-message";

    wrapper.style.marginBottom = "18px";


    /* User message */

    if (type === "user") {

        wrapper.style.display = "flex";
        wrapper.style.justifyContent = "flex-end";


        const bubble = document.createElement("div");

        bubble.className = "message";

        bubble.style.background = "#6366f1";
        bubble.style.color = "white";

        bubble.textContent = message;

        wrapper.appendChild(bubble);

    }


    /* Assistant message */

    else {

        wrapper.innerHTML = `
            <div class="avatar">AI</div>
            <div class="message"></div>
        `;


        wrapper
            .querySelector(".message")
            .textContent = message;

    }


    chatMessages.appendChild(wrapper);


    /* Scroll to latest message */

    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}



/* =========================================================
   SEND MESSAGE
========================================================= */

async function sendMessage() {

    const message = input.value.trim();


    if (!message) {
        return;
    }


    /* Show user message */

    addMessage(
        message,
        "user"
    );


    /* Clear input */

    input.value = "";


    /* Disable button */

    sendButton.disabled = true;

    sendButton.textContent =
        "Processing...";


    try {

        const response = await fetch(
            "/api/chat",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: message
                })
            }
        );


        const data = await response.json();


        /* Successful request */

        if (data.status === "success") {

            addMessage(
                data.message,
                "assistant"
            );


            /* Refresh account */

            await loadAccount();


            /* Refresh activity */

            await loadActivity();

        }


        /* Failed request */

        else {

            addMessage(
                data.message ||
                "The request could not be completed.",
                "assistant"
            );

        }


    }


    catch (error) {

        console.error(
            "Chat error:",
            error
        );


        addMessage(
            "Unable to connect to the AI Account Assistant.",
            "assistant"
        );

    }


    /* Re-enable button */

    sendButton.disabled = false;

    sendButton.textContent =
        "Send";
}



/* =========================================================
   LOAD ACCOUNT
========================================================= */

async function loadAccount() {

    try {

        const response =
            await fetch("/api/account");


        const data =
            await response.json();


        if (
            data.status === "success" &&
            data.account
        ) {

            const account =
                data.account;


            /* Account ID */

            document.getElementById(
                "accountId"
            ).textContent =
                account.account_id;


            /* Account type */

            document.getElementById(
                "accountType"
            ).textContent =
                account.account_type
                    .charAt(0)
                    .toUpperCase() +
                account.account_type.slice(1);


            /* Balance */

            document.getElementById(
                "accountBalance"
            ).textContent =
                `₹${account.balance}`;


            /* Currency */

            document.getElementById(
                "accountCurrency"
            ).textContent =
                account.currency;

        }

    }


    catch (error) {

        console.error(
            "Unable to load account:",
            error
        );

    }
}



/* =========================================================
   LOAD ACTIVITY
========================================================= */

async function loadActivity() {

    const activityList =
        document.getElementById(
            "activityList"
        );


    try {

        const response =
            await fetch("/api/activity");


        const data =
            await response.json();


        /* Clear current activity */

        activityList.innerHTML = "";


        /* No activity */

        if (
            !data.activity ||
            data.activity.length === 0
        ) {

            activityList.innerHTML = `
                <div class="activity-empty">
                    No activity yet.
                </div>
            `;

            return;
        }


        /* Display activities */

        data.activity
            .slice()
            .reverse()
            .forEach(activity => {

                const item =
                    document.createElement("div");

                item.className =
                    "activity-item";


                item.innerHTML = `
                    <div class="activity-check">
                        ✓
                    </div>

                    <div>
                        <strong></strong>
                        <span></span>
                    </div>
                `;


                item.querySelector(
                    "strong"
                ).textContent =
                    activity.action ||
                    "Account activity";


                item.querySelector(
                    "span"
                ).textContent =
                    activity.description ||
                    "Account operation completed.";


                activityList.appendChild(
                    item
                );

            });

    }


    catch (error) {

        console.error(
            "Unable to load activity:",
            error
        );


        activityList.innerHTML = `
            <div class="activity-empty">
                Unable to load activity.
            </div>
        `;

    }
}



/* =========================================================
   NAVIGATION HELPER
========================================================= */

function setActiveNav(activeNav) {

    const navItems = [
        homeNav,
        accountNav,
        activityNav,
        settingsNav
    ];


    navItems.forEach(
        item => {

            if (item) {

                item.classList.remove(
                    "active"
                );

            }

        }
    );


    if (activeNav) {

        activeNav.classList.add(
            "active"
        );

    }
}



/* =========================================================
   SHOW HOME
========================================================= */

function showHome() {

    /* Show main home content */

    homeSection.style.display =
        "block";

    accountSection.style.display =
        "block";


    /* Hide other sections */

    activitySection.style.display =
        "none";

    settingsSection.style.display =
        "none";


    /* Activate Home */

    setActiveNav(
        homeNav
    );


    /* Scroll to top */

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}



/* =========================================================
   SHOW ACCOUNT
========================================================= */

function showAccount() {

    /* Show account */

    homeSection.style.display =
        "block";

    accountSection.style.display =
        "block";


    /* Hide other sections */

    activitySection.style.display =
        "none";

    settingsSection.style.display =
        "none";


    /* Activate Account */

    setActiveNav(
        accountNav
    );


    /* Refresh account */

    loadAccount();


    /* Scroll to account */

    accountSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}



/* =========================================================
   SHOW ACTIVITY
========================================================= */

async function showActivity() {

    /* Show activity */

    activitySection.style.display =
        "block";


    /* Keep home and account visible */

    homeSection.style.display =
        "block";

    accountSection.style.display =
        "block";


    /* Hide settings */

    settingsSection.style.display =
        "none";


    /* Activate Activity */

    setActiveNav(
        activityNav
    );


    /* Load latest activity */

    await loadActivity();


    /* Scroll to activity */

    activitySection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}



/* =========================================================
   SHOW SETTINGS
========================================================= */

function showSettings() {

    /* Hide activity */

    activitySection.style.display =
        "none";


    /* Keep home/account visible */

    homeSection.style.display =
        "block";

    accountSection.style.display =
        "block";


    /* Show settings */

    settingsSection.style.display =
        "block";


    /* Activate Settings */

    setActiveNav(
        settingsNav
    );


    /* Scroll to settings */

    settingsSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}



/* =========================================================
   NAVIGATION EVENTS
========================================================= */

homeNav.addEventListener(
    "click",
    function(event) {

        event.preventDefault();

        showHome();

    }
);


accountNav.addEventListener(
    "click",
    function(event) {

        event.preventDefault();

        showAccount();

    }
);


activityNav.addEventListener(
    "click",
    function(event) {

        event.preventDefault();

        showActivity();

    }
);


settingsNav.addEventListener(
    "click",
    function(event) {

        event.preventDefault();

        showSettings();

    }
);



/* =========================================================
   SEND BUTTON
========================================================= */

sendButton.addEventListener(
    "click",
    sendMessage
);



/* =========================================================
   ENTER KEY
========================================================= */

input.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            sendMessage();

        }

    }
);



/* =========================================================
   INITIAL PAGE LOAD
========================================================= */

loadAccount();

loadActivity();