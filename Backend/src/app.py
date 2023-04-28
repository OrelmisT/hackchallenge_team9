from db import db
from flask import Flask, request
import json
from db import User
import os
import user_auth
import datetime

app = Flask(__name__)
db_filename = "cms.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()


def success_response(data, code = 200):
    return json.dumps(data), code

def fail_response(message, code = 404):
    return json.dumps({"error": message}), code


def extract_token_from_header(request):
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return False, "Missing auth_header."
    bearer_token = auth_header.replace("Bearer", "").strip()
    if not bearer_token:
        return False, "Invalid auth header"
    return True, bearer_token
    




#ROUTES
#May have to edit response codes

@app.route("/register/", methods = ["POST"])
def register_user():
    body = json.loads(request.data)
    name = body.get("name")
    bio = body.get("bio")
    net_id = body.get("net_id")
    password = body.get("password")

    if net_id  is None or password is None or name is None:
        return fail_response("Invalid netID, password, or name.")
    
    created, user = user_auth.create_user(net_id,name, bio, password)

    if not created:
        return fail_response("User already exists.")
    
    return success_response({
        "session_token": user.session_token,
        "session_experiation": str(user.session_expiration),
        "update_token": user.update_token
    })

@app.route("/login/", methods = ["POST"])
def login():

    body = json.loads(request.data)
    
    net_id = body.get("net_id")
    password = body.get("password")
    if net_id is None or password is None:
        return fail_response("Invalid netID or passsword.")
    success, user = user_auth.verify_credentials(net_id, password)

    if not success:
        return fail_response("Incorrect username or password.")
    
    return success_response({
        "session_token": user.session_token,
        "session_expiration": str(user.session_expiration),
        "update_token": user.update_token 
    })

@app.route("/session/", methods = ["POST"])
def update_session():
    success, update_token = extract_token_from_header(request)

    if not success:
        return fail_response(update_token)
    
    user = user_auth.renew_session(update_token)

    if user is None:
        return fail_response("Invalid update token.")
    return success_response(
        {
        "session_token": user.session_token,
        "session_expiration": str(user.session_expiration),
        "update_token": user.update_token
        }
    )

@app.route("/logout/", methods = ["POST"])
def logout():
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return fail_response("Invalid sessopmn token.")
    user.session_expiration = datetime.datetime.now()
    db.session.commit()
    return success_response("Logged out successfully.")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)