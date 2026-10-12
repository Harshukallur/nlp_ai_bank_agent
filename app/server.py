
import os
from functools import wraps

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    session,
)

from .service import AccountService


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# Set SESSION_SECRET in your environment before running.
# Do not use the fallback for a deployed application.
app.secret_key = os.environ.get("SESSION_SECRET")

if not app.secret_key:
    raise RuntimeError(
        "SESSION_SECRET is not configured. "
        "Set it in your terminal before starting Flask."
    )

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Enable this when running behind HTTPS.
    SESSION_COOKIE_SECURE=False,
)


# =========================================================
# INITIALIZE AI ACCOUNT SERVICE
# =========================================================

print("Starting AI Account Assistant...")

service = AccountService()

# Use the same database client as the service.
api_client = service.api_client

print("AI Account Assistant ready.")


# =========================================================
# AUTHENTICATION HELPER
# =========================================================

def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        if user_id is None:
            return jsonify({
                "status": "failed",
                "message": "Please sign in to continue.",
            }), 401

        # Ensure the session still refers to an existing user.
        user = api_client.get_user(user_id)

        if user is None:
            session.clear()
            return jsonify({
                "status": "failed",
                "message": "Your session is invalid. Please sign in again.",
            }), 401

        return route_function(*args, **kwargs)

    return wrapper


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/", methods=["GET"])
def home():
    # The frontend login screen will be added in a later step.
    if "user_id" not in session:
        return render_template("dashboard.html")

    return render_template("dashboard.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "failed",
            "message": "Please provide JSON registration details.",
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "status": "failed",
            "message": "Username and password are required.",
        }), 400

    username = username.strip()

    if not username or not password:
        return jsonify({
            "status": "failed",
            "message": "Username and password cannot be empty.",
        }), 400

    if len(username) > 80:
        return jsonify({
            "status": "failed",
            "message": "Username must be 80 characters or fewer.",
        }), 400

    result = api_client.register_user(username, password)

    if result["status"] != "success":
        return jsonify(result), 409

    return jsonify({
        "status": "success",
        "message": "Registration successful. Please sign in.",
    }), 201


# =========================================================
# LOGIN
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "failed",
            "message": "Please provide your username and password.",
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "status": "failed",
            "message": "Username and password are required.",
        }), 400

    user = api_client.authenticate_user(username, password)

    if user is None:
        return jsonify({
            "status": "failed",
            "message": "Invalid username or password.",
        }), 401

    # Prevent a previous session from being reused.
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]

    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "username": user["username"],
        },
    })


# =========================================================
# CURRENT USER
# =========================================================

@app.route("/api/me", methods=["GET"])
@login_required
def current_user():
    return jsonify({
        "status": "success",
        "user": {
            "id": session["user_id"],
            "username": session["username"],
        },
    })


# =========================================================
# LOGOUT
# =========================================================

@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    session.clear()

    return jsonify({
        "status": "success",
        "message": "Logged out successfully.",
    })


# =========================================================
# CHAT API
# =========================================================

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict) or "message" not in data:
            return jsonify({
                "status": "failed",
                "message": "Request must contain a 'message' field.",
            }), 400

        user_message = data["message"]

        if not isinstance(user_message, str):
            return jsonify({
                "status": "failed",
                "message": "Message must be a string.",
            }), 400

        user_message = user_message.strip()

        if not user_message:
            return jsonify({
                "status": "failed",
                "message": "Message cannot be empty.",
            }), 400

        # The service will be updated in the next step to scope
        # all database operations to this authenticated user.
        result = service.process_request(
            user_message,
            user_id=session["user_id"],
        )

        return jsonify(result)

    except Exception as error:
        app.logger.exception("Chat API error: %s", error)

        return jsonify({
            "status": "failed",
            "message": "The request could not be processed at this time.",
        }), 500


# =========================================================
# ACCOUNT API
# =========================================================

@app.route("/api/account", methods=["GET"])
@login_required
def account():
    try:
        user_id = session["user_id"]
        user_account = api_client.get_account(user_id)

        return jsonify({
            "status": "success",
            "account": user_account,
        })

    except Exception as error:
        app.logger.exception("Account API error: %s", error)

        return jsonify({
            "status": "failed",
            "message": "Unable to retrieve account information.",
        }), 500


# =========================================================
# ACTIVITY API
# =========================================================

@app.route("/api/activity", methods=["GET"])
@login_required
def activity():
    try:
        activities = api_client.get_activity(session["user_id"])

        return jsonify({
            "status": "success",
            "activity": activities,
        })

    except Exception as error:
        app.logger.exception("Activity API error: %s", error)

        return jsonify({
            "status": "failed",
            "message": "Unable to retrieve account activity.",
        }), 500


# =========================================================
# START FLASK SERVER
# =========================================================

if __name__ == "__main__":
    app.run(debug=False)
