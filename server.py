from bson.objectid import ObjectId
from flask import Flask,request, jsonify, make_response, render_template, send_from_directory
from flask.templating import render_template
from werkzeug.utils import secure_filename
import jwt
import datetime
import json
import os
from flask_cors import CORS, cross_origin
import db
import misc

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello, World!"

# login [X]
# signup [X]
# create organization [X]
# create code [X]
# join organization [X]
# add hours [X]
# get all organizations a member is apart of [X] (no token needed)
# get all organization that a user owns [X] (no token needed)
# get all members of an organization (with hours) [X] (no token needed)


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or "email" not in data or "password" not in data:
        return jsonify({"message": "Missing email or password"}), 401

    email = data["email"]
    password = data["password"]
    

    if not data or not db.login_successful(email, password):
        return jsonify({"message": "Invalid email or password"}), 401

    user_id = db.find_user_by_email(email)["_id"]
    
    data = {
        "email": email,
        "user_id": str(user_id),
        "expiration": str(datetime.datetime.now() + datetime.timedelta(hours=24))
    }
    token = jwt.encode(data, str(app.config["SECRET_KEY"]), algorithm="HS256")

    # Set the JWT token as a cookie
    expiration_time = datetime.datetime.now() + datetime.timedelta(days=1)
    expires_formatted = expiration_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    return {
        "token": token,
        "expires": expires_formatted
    }


@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data or len(data['email']) == 0 or len(data["password"]) == 0:
        return jsonify({"message": "Missing email or password"}), 400
    print(len(data["email"]))
    email = data["email"]
    password = data["password"]
    name = data["name"]

    if db.find_user_by_email(email):
        return jsonify({"message": "email already used"}), 401

    db.add_document("users", {"email": email, "password": password, "name": name, "total_hours" : 0, "organization_member":{}, "organization_owner":[]})
    return jsonify({"message": "Account created successfully"}), 201

@app.route("/api/createOrganization", methods=["POST"])
def createOrganization():
    data = request.get_json()
    if not data or 'name' not in data or 'token' not in data or 'location' not in data or "phone" not in data or "description" not in data or "url" not in data:
        return jsonify({"message": "Missing 1 or more parameters"}), 400
    try:
        data_from_token = jwt.decode(data["token"], str(app.config["SECRET_KEY"]), algorithms=["HS256"])
    except:
        return {"message": "Invalid token"}
    
    org_name = data["name"]
    if db.find_organization_by_name(org_name):
        return jsonify({"message": "Organization already exists"}), 401
    owner_id = ObjectId(data_from_token["user_id"])
    description = data["description"]
    url = data["url"]
    code = misc.create_code(7)
    while db.find_organization_by_code(code):
        code = misc.create_code(7)
    db.create_organization(org_name, code, owner_id, data["location"], data["phone"], description, url)
    return jsonify({"message": "Organization created successfully"}), 201

@app.route("/api/joinOrganization", methods=["POST"])
def joinOrganization():
    data = request.get_json()
    if not data or 'code' not in data or 'token' not in data:
        return jsonify({"message": "Missing org code or token"}), 400
    try:
        data_from_token = jwt.decode(data["token"], str(app.config["SECRET_KEY"]), algorithms=["HS256"])
    except:
            return {"message": "Invalid token"}
    org_code = data["code"]
    db_data = db.find_organization_by_code(org_code)
    if not db_data:
        return jsonify({"message": "Organization does not exist"}), 401
    user_id = ObjectId(data_from_token["user_id"])
    if user_id == db_data["owner"]:
        return jsonify({"message": "You cannot join your own organization"}), 401
    db.add_member(user_id, db_data["_id"])
    return jsonify({"message": "You have joined the organization successfully"}), 201

@app.route("/api/addHours", methods=["POST"])
def addHours():
    data = request.get_json()
    if not data or 'token' not in data or 'hours' not in data or "user_id" not in data or 'org_id' not in data:
        return jsonify({"message": "Missing token or hours or user_id or org_id"}), 400
    try:
        data_from_token = jwt.decode(data["token"], str(app.config["SECRET_KEY"]), algorithms=["HS256"])
    except:
        return {"message": "Invalid token"}
    owner_id = ObjectId(data_from_token["user_id"])
    hours = data["hours"]
    org_id = data["org_id"]
    user_id = data["user_id"]
    db_data = db.find_organization_by_id(ObjectId(org_id))
    if not db_data:
        return jsonify({"message": "Organization does not exist"}), 401
    if db_data["owner"] != owner_id:
        return jsonify({"message": "You are not the owner of this organization"}), 401
    if user_id not in db_data["members"]:
        return jsonify({"message": "Target user is not a member of this organization"}), 401

    db.add_hours(ObjectId(user_id), ObjectId(org_id), hours)
    return jsonify({"message": "Hours added successfully"}), 201

@app.route("/api/getUserProfile", methods=["GET"])
def getUserProfile():
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({"message": "Missing user id"}), 400
    
    user_id = data["user_id"]
    db_data = db.find_user_by_id(user_id)
    if not db_data:
        return jsonify({"message": "User does not exist"}), 401
    db_data.pop("email")
    db_data.pop("password")
    return json.loads(str(db_data).replace("ObjectId(", "").replace(")", "").replace("'",'"')), 200

@app.route("/api/getOrganizationData", methods=["GET"])
def getOrganizationData():
    data = request.get_json()
    if not data or 'org_id' not in data:
        return jsonify({"message": "Missing org id"}), 400

    org_id = data["org_id"]
    db_data = db.find_organization_by_id(org_id)
    if not db_data:
        return jsonify({"message": "Organization does not exist"}), 401
    return json.loads(str(db_data).replace("ObjectId(", "").replace(")", "").replace("'",'"')), 200

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=8080))