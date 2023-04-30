from flask_sqlalchemy import SQLAlchemy
import datetime
import hashlib
import bcrypt
import os



db = SQLAlchemy()


user_group_association_table = db.Table("user_group_assoc", 
  db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
  db.Column("group_id", db.Integer, db.ForeignKey("group.id"))
)

#MODELS

class User(db.Model):
   __tablename__ = "user"

   id = db.Column(db.Integer, primary_key = True, autoincrement = True)
   net_id = db.Column(db.String, unique = True, nullable = False)
   name = db.Column(db.String, nullable = False)
   bio = db.Column(db.String, nullable = True )
   groups = db.relationship("Group", secondary= user_group_association_table,
                             back_populates="users")
   password_digest =  db.Column(db.String, nullable=False)

   # Session information
   session_token = db.Column(db.String, nullable=False, unique=True)
   session_expiration = db.Column(db.DateTime, nullable=False)
   update_token = db.Column(db.String, nullable=False, unique=True)

   def __init__(self, **kwargs):
      self.net_id = kwargs.get("net_id")
      self.name = kwargs.get("name")
      self.bio = kwargs.get("bio")
      self.password_digest =  bcrypt.hashpw(kwargs.get("password").encode("utf8")
                                            , bcrypt.gensalt(rounds=13))
      self.renew_session()


      #authentication 
  
   def _urlsafe_base_64(self):
        """
        Randomly generates hashed tokens (used for session/update tokens)
        """
        return hashlib.sha1(os.urandom(64)).hexdigest()

   def renew_session(self):
        """
        Renews the sessions, i.e.
        1. Creates a new session token
        2. Sets the expiration time of the session to be a day from now
        3. Creates a new update token
        """
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

   def verify_password(self, password):
        """
        Verifies the password of a user
        """
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

   def verify_session_token(self, session_token):
        """
        Verifies the session token of a user
        """
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

   def verify_update_token(self, update_token):
        """
        Verifies the update token of a user
        """
        return update_token == self.update_token
   
   #Serialization
   
   def serialize(self):
       return{
           "id": self.id,
           "net_id": self.net_id,
           "name": self.name,
           "bio": self.bio,
           "groups": [g.serialize_simple for g in self.groups]

       }
   def serialize_simple(self):
       return{
           "id": self.id,
           "net_id": self.net_id,
           "name": self.name
       }
       
   

class Course(db.Model):
   __tablename__ = "course"
   id = db.Column(db.Integer, primary_key = True, autoincrement = True)
   course_title = db.Column(db.String, nullable = False)
   course_code = db.Column(db.String, nullable = False, unique = True)
   groups = db.relationship("Group", cascade = "delete")
   
   def __init__(self, **kwargs):
       self.course_title = kwargs.get("course_title")
       self.course_code = kwargs.get("course_code")

   #Serialization

   def serialize(self):
       return {
           "id": self.id,
           "course_title": self.course_title,
           "groups": [g.serialize_simple() for g in self.groups]
       }
   
   def serialize_simple(self):
       return{
           "id": self.id,
           "course_title": self.course_title
       }

    
    


#implementation not complete (we need to add in events and requests, and serialization funcs)
class Group(db.Model):
    __tablename__ = "group"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    users = db.relationship("User", secondary= user_group_association_table,
                             back_populates="groups")
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable = False)
    accepting_members = db.Column(db.Boolean, nullable = False)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable = False)
    events = db.relationship("Event", cascade = "delete")
    requests = db.relationship("Request", cascade = "delete")
    
    def __init__(self, **kwargs):
      self.course_id = kwargs.get("course_id")
      self.accepting_members = True
      self.admin_id = kwargs.get("admin_id")

    def serialize(self):
        return {
            "id": self.id,
            "course_id" : self.course_id,
            "admin_id" : self.admin_id,
            "users": [u.serialize_simple() for u in self.users],
            "events": [e.serialize_simple() for e in self.events],
            "requests": [r.serialize_simple() for r in self.requests],
            "accepting_members": self.accepting_members
        }
    
    def serialize(self):
        return{
            "id": self.id,
            "course_id": self.course_id,
            "admin_id": self.admin_id,
            "accepting_members": self.accepting_members
        }
   
        
    
# class Event(db.Model):
class Event(db.Model):
    """
    Event object.
    """    
    __tablename__ = "events"    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable = False)    
    description = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=False)        
    time = db.Column(db.Integer, nullable=False)    
    attendee = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize an Event object.
        """
        self.description = kwargs.get("description", "")
        self.location = kwargs.get("location", "")
        self.time = kwargs.get("time", "")
        self.attendee = kwargs.get("attendee")

    def serialize(self):
        """
        Serialize an Event object.
        """
        attendees = [a.serialize_wo() for a in self.user_id]
        return {
            "id": self.id,
            "description": self.description,
            "location": self.location,
            "time": self.time,
            "attendee": attendees.serialize()
        }

#class Request(db.Model)
class Request(db.Model):
    """
    Request object.
    """    
    __tablename__ = "request"    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable = False)    
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.Boolean, nullable=False)        


    def __init__(self, **kwargs):
        """
        Initialize an Request object.
        """
        self.description = kwargs.get("description", "")
        self.user_id = kwargs.get("user_id", "")
        self.status = kwargs.get("status")

    def serialize(self):
        """
        Serialize an Request object.
        """
        user = User.query.filter_by(id=self.user_id).first()
        return {
            "id": self.id,
            "user": user.serialize(),
            "status": self.status
        }