from flask_sqlalchemy import SQLAlchemy
import datetime
import hashlib
import bcrypt
import os



db = SQLAlchemy()


user_group_association_table = db.Table("user_group_assoc", 
  db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
  db.Column("group_id", db.Integer, db.ForeignKey("user.id"))
)

#MODELS

class User(db.model):
   __tablename__ = "user"

   id = db.Column(db.Integer, primary_key = True)
   net_id = db.Column(db.String, unique = True, nullable = False)
   name = db.Column(db.String, nuble = False)
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
       
   



# class Course(db.model):


#implementation not complete
class Group(db.model):
    __tablename__ = "group"
    id = db.Column(db.Integer, primary_key = True)
    users = db.relationship("User", secondary= user_group_association_table,
                             back_populates="groups")
    
    def __init__(self, **kwargs):
      self.id = kwargs.get("id")
      self.users = [u.serialize_simple for u in self.users]
        
    
# class Event(db.model):
