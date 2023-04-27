from db import db
from flask import Flask, request
import json
from db import User
import os
import user_auth

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






if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)