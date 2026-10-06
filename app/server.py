from flask import Flask, request, jsonify, render_template
import os

from .service import AccountService


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(
    __name__,
    template_folder=os.path.join(
        BASE_DIR,
        "templates"
    ),
    static_folder=os.path.join(
        BASE_DIR,
        "static"
    )
)


# =========================================================
# INITIALIZE AI ACCOUNT SERVICE
# =========================================================

print("Starting AI Account Assistant...")

service = AccountService()

print("AI Account Assistant ready.")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return render_template(
        "dashboard.html"
    )


# =========================================================
# CHAT API
# =========================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json(
            silent=True
        )

        # --------------------------------------------------
        # Validate request
        # --------------------------------------------------

        if not data or "message" not in data:

            return jsonify({
                "status": "failed",
                "message": (
                    "Request must contain "
                    "a 'message' field."
                )
            }), 400


        user_message = data["message"]


        # --------------------------------------------------
        # Validate message
        # --------------------------------------------------

        if not isinstance(
            user_message,
            str
        ):

            return jsonify({
                "status": "failed",
                "message": (
                    "Message must be a string."
                )
            }), 400


        user_message = user_message.strip()


        if not user_message:

            return jsonify({
                "status": "failed",
                "message": (
                    "Message cannot be empty."
                )
            }), 400


        # --------------------------------------------------
        # Process request
        # --------------------------------------------------

        result = service.process_request(
            user_message
        )


        return jsonify(result)


    except Exception as error:

        print(
            f"Chat API error: {error}"
        )

        return jsonify({
            "status": "failed",
            "message": (
                "The request could not be processed "
                "at this time."
            )
        }), 500


# =========================================================
# ACCOUNT API
# =========================================================

@app.route("/api/account", methods=["GET"])
def account():

    try:

        account = (
            service.api_client.get_account()
        )


        return jsonify({
            "status": "success",
            "account": account
        })


    except Exception as error:

        print(
            f"Account API error: {error}"
        )

        return jsonify({
            "status": "failed",
            "message": (
                "Unable to retrieve account information."
            )
        }), 500


# =========================================================
# ACTIVITY API
# =========================================================

@app.route("/api/activity", methods=["GET"])
def activity():

    try:

        activities = (
            service.api_client.get_activity()
        )


        return jsonify({
            "status": "success",
            "activity": activities
        })


    except Exception as error:

        print(
            f"Activity API error: {error}"
        )

        return jsonify({
            "status": "failed",
            "message": (
                "Unable to retrieve account activity."
            )
        }), 500


# =========================================================
# START FLASK SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=False
    )