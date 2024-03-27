import db as database
db = database.connect_db()
from flask import Flask, request, jsonify, Blueprint
import hashlib
import jwt

auth_bp = Blueprint('auth', __name__)

# Initialize Flask app and limiter
app = Flask(__name__)

@auth_bp.route('/login', methods=['POST'])
def handle_login():
    try:
        # Get email and password from request data
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        db.ping(reconnect=True)
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM author WHERE email = %s", (email,))
            user = cursor.fetchone() 

        if user and user['password'] == hashlib.sha256(password.encode()).hexdigest():
            payload = {'email': email} 
            token = jwt.encode(payload, 'qcuj', algorithm='HS256')

            return jsonify({"message": "Login successful", "token": token, "userId":user['author_id']}), 200
        else:
            return jsonify({"message": "Invalid email or password"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/<string:author_id>', methods=['GET'])
def getUser(author_id):
    db.ping(reconnect=True)
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM author WHERE author_id = %s", (author_id))
        user = cursor.fetchone()

    # Check if user exists
    if user:
        return jsonify(user), 200
    else:
        return jsonify({"error": "User not found"}), 404
