from db import db
from flask import Flask, request
import json
from db import User
from db import Course
from db import Group
from db import Request
from db import Event
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
    
    if not optional_group.accepting_members:
        return fail_response("This group is not accepting requests at this time.")

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


    
@app.route("/requests/<int:request_id>/", methods = ["POST"])
def accept_deny_request(request_id):

    body = json.loads(request.data)
    response = body.get("response")
    if response is None:
        return fail_response("Invalid response.")

    join_request = Request.query.filter_by(id = request_id).first()

    if join_request is None:
        return fail_response("No request with this id exists.")
    
    group = Group.query.filter_by(id = join_request.group_id ).first()


    if group is None:
        return fail_response("The group this request was made for no longer exists.")
    
    if not (join_request.status is None):
        return fail_response("Request has already been accepted or denied.")
    
    request_maker = User.query.filter_by(id = join_request.user_id).first()
    if request_maker is None:
        return fail_response("Request maker no longer exists.")
    
    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    is_admin = (user.id == group.admin_id)

    if not is_admin:
        return fail_response("Group admin permission required.")
    
    if (response == False):
        join_request.status = False
        db.session.commit()
        return success_response(join_request.serialize()) 
    
    join_request.status = True
    group.users.append(request_maker)
    db.session.commit()
    return success_response (join_request.serialize())


@app.route("/groups/<int:group_id>/accepting/", methods = ["POST"])
def close_open_group(group_id):

    body = json.loads(request.data)
    accepting_members = body.get("accepting_members")

    if accepting_members is None:
        return fail_response("Invalid member acceptance status.")

    group = Group.query.filter_by(id = group_id).first()

    if group is None:
        return fail_response("Group with this id does not exist.")

    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    is_admin = (user.id == group.admin_id)
    
    if not is_admin:
        return fail_response("This requires admin permission.")
    
    group.accepting_members = accepting_members
    db.session.commit()

    return success_response(group.serialize())

#Requires membership in group to view requests to group
@app.route("/groups/<int:group_id>/requests/", methods = ["GET"])
def view_requests(group_id):

    group = Group.query.filter_by(id = group_id).first()

    if group is None:
        return fail_response("Group with this id does not exist.")
    

    
    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    #Checking if is member of group
    preexisting_request = Request.query.filter_by(group_id = group_id, user_id = user.id, status = True).first()
    is_admin = (user.id == group.admin_id)

    if preexisting_request is None and (not is_admin):
        return fail_response("User is not a member of this group")

    requests = [r.serialize() for r in  Request.query.filter_by(group_id = group_id).all()]

    return success_response({"requests": requests})

@app.route("/requests/<int:request_id>/", methods = ["GET"])
def get_request(request_id):

    the_request = Request.query.filter_by(id=request_id).first()

    if the_request is None:
        return fail_response("Request does not exist.")
    
    group_id = the_request.group_id

    group = Group.query.filter_by(id=group_id).first()

    if group is None:
        return fail_response("The group for which this request was made no longer exists.")
    

    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    #Checking if is member of group
    preexisting_request = Request.query.filter_by(group_id = group_id, user_id = user.id, status = True).first()
    is_admin = (user.id == group.admin_id)

    if preexisting_request is None and (not is_admin):
        return fail_response("User is not a member of this group")
    
    return success_response(the_request.serialize())

@app.route("/groups/<int:group_id>/events/", methods = ["POST"])
def create_event(group_id):

    group = Group.query.filter_by(id = group_id).first()
    if group is None:
        return fail_response("No group with this id exists.")
    
    body = json.loads(request.data)
    description = body.get("description")
    location = body.get("location")
    year = body.get("year")
    month = body.get("month")
    day = body.get("day")
    hour = body.get("hour")
    minute = body.get("minute")

    if year is None or month is None or day is None or hour is None or minute is None or location is None or description is None:
        return fail_response("Missing location, time, or description")
        

    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    #Checking if is member of group
    preexisting_request = Request.query.filter_by(group_id = group_id, user_id = user.id, status = True).first()
    is_admin = (user.id == group.admin_id)

    if preexisting_request is None and (not is_admin):
        return fail_response("User is not a member of this group")
    
    new_event = Event(group_id = group_id, description = description, 
                      location = location, year = year, month = month, day = day,
                      hour = hour, minute = minute)

    new_event.attendees.append(user)

    db.session.add(new_event)
    db.session.commit()

    return success_response(new_event.serialize())


@app.route("/groups/<int:group_id>/events/", methods = ["GET"])
def get_events(group_id):

    group = Group.query.filter_by(id = group_id).first()
    if group is None:
        return fail_response("No group with this id exists.")

    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    #Checking if is member of group
    preexisting_request = Request.query.filter_by(group_id = group_id, user_id = user.id, status = True).first()
    is_admin = (user.id == group.admin_id)

    if preexisting_request is None and (not is_admin):
        return fail_response("User is not a member of this group")
    
    events = [e.serialize() for e in group.events]

    return success_response({"events": events})

@app.route("/events/<int:event_id>/", methods = ["GET"])
def get_event(event_id):

    event = Event.query.filter_by(id = event_id).first()
    
    if event is None:
        return fail_response("No event with this id exists")
    
    group = Group.query.filter_by(id = event.group_id).first()
    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    #Checking if is member of group
    preexisting_request = Request.query.filter_by(group_id = group.id, user_id = user.id, status = True).first()
    is_admin = (user.id == group.admin_id)

    if preexisting_request is None and (not is_admin):
        return fail_response("User is not a member of this group")
    
    return success_response(event.serialize())

@app.route("/events/<int:event_id>/join/", methods = ["POST"])
def join_event(event_id):
    event = Event.query.filter_by(id = event_id).first()
    if event_id is None:
        return fail_response("No event with this id exists.")
    
    group = Group.query.filter_by(id = event.group_id).first()

    #Verifying session 
    success, session_token = extract_token_from_header(request)
    if not success:
        return fail_response(session_token)
    user = user_auth.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return fail_response("Invalid session token")
    
    #Checking if is member of group
    preexisting_request = Request.query.filter_by(group_id = group.id, user_id = user.id, status = True).first()
    is_admin = (user.id == group.admin_id)

    if preexisting_request is None and (not is_admin):
        return fail_response("User is not a member of this group")
    
    event.attendees.append(user)
    db.session.commit()
    return success_response(event.serialize())

    

    

    
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)