from flask_login import UserMixin
from bson.objectid import ObjectId

class User(UserMixin):

    def __init__(self, user_data):

        self.id = str(user_data["_id"])

        self.name = user_data["name"]

        self.email = user_data["email"]

        self.role = user_data["role"]

    @staticmethod
    def get(users_collection, user_id):

        user_data = users_collection.find_one({
            "_id": ObjectId(user_id)
        })

        if user_data:

            return User(user_data)

        return None