from db import db
from flask import Flask, request
import json
from db import User
from db import Course
from db import Group
from db import Request
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

@app.route("/users/", methods = ["GET"])
def get_all_users():
    users = [u.serialize() for u in User.query.all()]
    return success_response({"users": users})

@app.route("/users/<string:net_id>/", methods = ["GET"])
def get_user(net_id):
    user = User.query.filter_by(net_id = net_id).first()
    return success_response(user.serialize())

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

    #Checking net_id and password

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

@app.route("/courses/", methods = ["POST"])
def create_course():
    body = json.loads(request.data)
    course_title = body.get("course_title")
    course_code = body.get("course_code")

    if course_title is None or course_code is None:
        return fail_response("Invalid course code or title.")
    
    optional_course = Course.query.filter_by(course_code = course_code).first()

    if not (optional_course is None):
        return fail_response("A course with this code already exists.")
    
    new_course = Course(course_title = course_title, course_code = course_code)
    db.session.add(new_course)
    db.session.commit()
    return success_response(new_course.serialize())

@app.route("/courses/", methods = ["GET"])
def get_courses():
    courses = [c.serialize() for c in Course.query.all()]
    return success_response({"courses": courses})

@app.route("/courses/<int:course_id>/", methods = ["GET"])
def get_course(course_id):
    course = Course.query.filter_by(id = course_id).first()
    return success_response(course.serialize())

@app.route("/groups/", methods = ["POST"])
def create_group():
    body = json.loads(request.data)
    course_code = body.get("course_code")

    if course_code is None:
        return fail_response("Invalid course code.")


    optional_course = Course.query.filter_by(course_code = course_code).first()

    if optional_course is None:
        return fail_response("There does not exist a course with this course code.")


    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    new_group = Group(admin_id = user.id, course_id = optional_course.id)
    new_group.users.append(user)
    db.session.add(new_group)
    db.session.commit()

    return success_response(new_group.serialize())

@app.route("/groups/", methods = ["GET"])
def get_groups():

    body = json.loads(request.data)
    course_code = body.get("course_code")

    #If no filtering by course code, get all groups.
    if course_code is None:
        groups = [g.serialize() for g in Group.query.all()]
        return success_response({"groups": groups})
    
    #Get groups by course code
    optional_course = Course.query.filter_by(course_code = course_code).first()

    if optional_course is None:
        return fail_response("A course with this code does not exist.")

    groups = [g.serialize() for g in Group.query.filter_by(course_id = optional_course.id).all()]

    return success_response({"groups": groups})
    


@app.route("/groups/<int:group_id>/", methods = ["GET"])
def get_group(group_id):
    group = Group.query.filter_by(id = group_id).first()
    if group is None:
        return fail_response("A group with this id does not exist.")
    return success_response(group.serialize())

@app.route("/groups/<int:group_id>/requests/", methods = ["POST"])
def create_request(group_id):

    optional_group = Group.query.filter_by(id = group_id).first()
    if optional_group is None:
        return fail_response("No group with this id exists.")

    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    #Checking if already member of group, or already created request.
    preexisting_request = Request.query.filter_by(group_id = group_id, user_id = user.id).first()
    is_admin = (user.id == optional_group.admin_id)

    if (not preexisting_request is None) or is_admin:
        return fail_response("User is already member of group or has already made request to join.")

    new_request = Request(group_id = group_id, user_id = user.id, status = None)

    db.session.add(new_request)
    db.session.commit()

    return success_response(new_request.serialize())    


        






if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)