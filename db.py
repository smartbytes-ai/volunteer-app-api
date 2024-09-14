
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
import os

uri = os.environ['MONGO_DB_URL']
database_name = "volunteer-data"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


client = MongoClient(uri, server_api=ServerApi('1'))
database = client[database_name]


def add_document(collection_name, document):
    collection = database[collection_name]
    collection.insert_one(document)

def get_document(collection_name, query):
    collection = database[collection_name]
    return collection.find_one(query)

def get_documents(collection_name, query):
    collection = database[collection_name]
    return collection.find(query)

def find_user_by_email(email):
    return get_document("users", {"email": email})

def find_user_by_id(user_id):
    return get_document("users", {"_id": ObjectId(user_id)})

def login_successful(email, password):
    return get_document("users", {"email": email, "password": password}) is not None

def find_organization_by_name(name):
    return get_document("organizations", {"name": name})

def find_organization_by_code(code):
    return get_document("organizations", {"code": code})

def find_organization_by_id(organization_id):
    return get_document("organizations", {"_id": ObjectId(organization_id)})

def create_organization(name, code, owner, location, phone, description, url):
    organization = {
        "name": name,
        "members": {},
        "code": code,
        "owner": owner,
        'location': location,
        "phone": phone,
        "description": description,
        "url": url
    }
    add_document("organizations", organization)
    org_id = find_organization_by_name(name)["_id"]
    database["users"].update_one({"_id": ObjectId(owner)}, {"$push": {"organization_owner": org_id}})

def add_member(_id, organization_id):
    organization_coll = database["organizations"]
    organization_coll.update_one({"_id": ObjectId(organization_id)}, {"$inc": {f"members.{_id}": 0}})
    database["users"].update_one({"_id": ObjectId(_id)}, {"$inc": {f"organization_member.{organization_id}": 0}})

def add_hours(_id, organization_id, hours):
    organization_coll = database["organizations"]
    organization_coll.update_one({"_id": ObjectId(organization_id)}, {"$inc": {f"members.{_id}": hours}})
    users_coll = database["users"]
    users_coll.update_one({"_id": ObjectId(_id)}, {"$inc": {"total_hours": hours}})
    users_coll.update_one({"_id": ObjectId(_id)}, {"$inc": {f"organization_member.{organization_id}": hours}})
