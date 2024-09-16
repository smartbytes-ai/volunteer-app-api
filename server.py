from bson.objectid import ObjectId
from flask import Flask, request, jsonify, make_response, render_template, send_from_directory
from flask.templating import render_template
from werkzeug.utils import secure_filename
import jwt  # Library for encoding/decoding JSON Web Tokens (JWT)
import datetime  # Handles date and time-related tasks
import json  # JSON parsing
import os  # Interacting with the operating system
from flask_cors import CORS, cross_origin  # Handling Cross-Origin Resource Sharing (CORS)
import db  # Custom database module (assumed to handle DB operations)
import misc  # Custom module for miscellaneous operations

app = Flask(__name__)

# Root route: simple "Hello, World!" response to verify that the server is running
@app.route("/")
def hello():
    return "Hello, World!"

# Login route
@app.route("/api/login", methods=["POST"])
def login():
    # Get the posted JSON data
    data = request.get_json()

    # Check if email and password are provided in the request
    if not data or "email" not in data or "password" not in data:
        return jsonify({"message": "Missing email or password"}), 401

    email = data["email"]
    password = data["password"]

    # Validate login credentials by checking the database
    if not db.login_successful(email, password):
        return jsonify({"message": "Invalid email or password"}), 401

    # Retrieve user ID from the database using the email
    user_id = db.find_user_by_email(email)["_id"]
    
    # Create a JWT token with user information and an expiration time
    data = {
        "email": email,
        "user_id": str(user_id),
        "expiration": str(datetime.datetime.now() + datetime.timedelta(hours=24))
    }
    token = jwt.encode(data, str(app.config["SECRET_KEY"]), algorithm="HS256")

    # Set the expiration time for the token
    expiration_time = datetime.datetime.now() + datetime.timedelta(days=1)
    expires_formatted = expiration_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # Return the token and expiration details to the client
    return {
        "token": token,
        "expires": expires_formatted
    }

# Signup route to create a new user
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    
    # Validate the incoming data
    if not data or 'email' not in data or 'password' not in data or len(data['email']) == 0 or len(data["password"]) == 0:
        return jsonify({"message": "Missing email or password"}), 400

    email = data["email"]
    password = data["password"]
    name = data["name"]

    # Check if the email is already registered
    if db.find_user_by_email(email):
        return jsonify({"message": "email already used"}), 401

    # Create a new user in the database
    db.add_document("users", {"email": email, "password": password, "name": name, "total_hours" : 0, "organization_member":{}, "organization_owner":[]})
    return jsonify({"message": "Account created successfully"}), 201

# Create an organization
@app.route("/api/createOrganization", methods=["POST"])
def createOrganization():
    data = request.get_json()
    
    # Ensure all required fields are present
    if not data or 'name' not in data or 'token' not in data or 'location' not in data or "phone" not in data or "description" not in data or "url" not in data:
        return jsonify({"message": "Missing 1 or more parameters"}), 400

    # Decode JWT token to extract the owner information
    try:
        data_from_token = jwt.decode(data["token"], str(app.config["SECRET_KEY"]), algorithms=["HS256"])
    except:
        return {"message": "Invalid token"}
    
    org_name = data["name"]

    # Check if the organization name already exists
    if db.find_organization_by_name(org_name):
        return jsonify({"message": "Organization already exists"}), 401

    # Create a unique organization code and add the organization to the database
    owner_id = ObjectId(data_from_token["user_id"])
    description = data["description"]
    url = data["url"]
    code = misc.create_code(7)  # Generate a random 7-character code

    # Ensure the generated code is unique
    while db.find_organization_by_code(code):
        code = misc.create_code(7)

    db.create_organization(org_name, code, owner_id, data["location"], data["phone"], description, url)
    return jsonify({"message": "Organization created successfully"}), 201

# Join an existing organization using a join code
@app.route("/api/joinOrganization", methods=["POST"])
def joinOrganization():
    data = request.get_json()

    # Validate that both the join code and token are provided
    if not data or 'code' not in data or 'token' not in data:
        return jsonify({"message": "Missing org code or token"}), 400

    # Decode the JWT token
    try:
        data_from_token = jwt.decode(data["token"], str(app.config["SECRET_KEY"]), algorithms=["HS256"])
    except:
        return {"message": "Invalid token"}

    org_code = data["code"]
    db_data = db.find_organization_by_code(org_code)

    # Check if the organization exists
    if not db_data:
        return jsonify({"message": "Organization does not exist"}), 401

    user_id = ObjectId(data_from_token["user_id"])

    # Prevent the user from joining their own organization
    if user_id == db_data["owner"]:
        return jsonify({"message": "You cannot join your own organization"}), 401

    # Add the user to the organization's member list
    db.add_member(user_id, db_data["_id"])
    return jsonify({"message": "You have joined the organization successfully"}), 201

# Add hours for a user in an organization
@app.route("/api/addHours", methods=["POST"])
def addHours():
    data = request.get_json()

    # Validate the required fields
    if not data or 'token' not in data or 'hours' not in data or "user_id" not in data or 'org_id' not in data:
        return jsonify({"message": "Missing token or hours or user_id or org_id"}), 400

    # Decode the JWT token
    try:
        data_from_token = jwt.decode(data["token"], str(app.config["SECRET_KEY"]), algorithms=["HS256"])
    except:
        return {"message": "Invalid token"}

    owner_id = ObjectId(data_from_token["user_id"])
    hours = data["hours"]
    org_id = data["org_id"]
    user_id = data["user_id"]
    
    # Check if the organization exists
    db_data = db.find_organization_by_id(ObjectId(org_id))
    if not db_data:
        return jsonify({"message": "Organization does not exist"}), 401

    # Ensure the user making the request is the owner of the organization
    if db_data["owner"] != owner_id:
        return jsonify({"message": "You are not the owner of this organization"}), 401

    # Ensure the target user is a member of the organization
    if user_id not in db_data["members"]:
        return jsonify({"message": "Target user is not a member of this organization"}), 401

    # Add the hours to the user's profile
    db.add_hours(ObjectId(user_id), ObjectId(org_id), hours)
    return jsonify({"message": "Hours added successfully"}), 201

# Get user profile by user ID
@app.route("/api/getUserProfile", methods=["GET"])
def getUserProfile():
    data = request.get_json()

    # Validate the user ID is present
    if not data or 'user_id' not in data:
        return jsonify({"message": "Missing user id"}), 400

    user_id = data["user_id"]

    # Fetch the user details from the database
    db_data = db.find_user_by_id(user_id)
    if not db_data:
        return jsonify({"message": "User does not exist"}), 401

    # Remove sensitive information from the response
    db_data.pop("email")
    db_data.pop("password")
    return json.loads(str(db_data).replace("ObjectId(", "").replace(")", "").replace("'",'"')), 200

# Get organization data by organization ID
@app.route("/api/getOrganizationData", methods=["GET"])
def getOrganizationData():
    data = request.get_json()

    # Validate the organization ID is present
    if not data or 'org_id' not in data:
        return jsonify({"message": "Missing org id"}), 400

    org_id = data["org_id"]

    # Fetch the organization details from the database
    db_data = db.find_organization_by_id(org_id)
    if not db_data:
        return jsonify({"message": "Organization does not exist"}), 401

    return json.loads(str(db_data).replace("ObjectId(", "").replace(")", "").replace("'",'"')), 200

# Run the Flask app on the specified host and port
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
