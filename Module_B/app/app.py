from flask import Flask, jsonify, request, render_template
import sqlite3
import jwt
import datetime
from functools import wraps
import logging
import os
from pathlib import Path

app = Flask(__name__)
SECRET_KEY = "super_secret_key_for_assignment_123"
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'app' / 'local_database.db'
LOG_DIR = BASE_DIR / 'logs'


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(filename=str(LOG_DIR / 'audit.log'), level=logging.INFO,
                    format='%(asctime)s - %(message)s')


def write_audit_log(actor, action, source='API', table_name=None, details=None, conn=None):
    logging.info(f"Actor: {actor} | Source: {source} | Action: {action} | Table: {table_name} | Details: {details}")
    owns_connection = conn is None
    if owns_connection:
        conn = get_db_connection()

    conn.execute(
        'INSERT INTO logs (actor, source, table_name, action, details) VALUES (?, ?, ?, ?, ?)',
        (actor, source, table_name, action, details)
    )

    if owns_connection:
        conn.commit()
        conn.close()


def set_audit_context(conn, actor, source='API'):
    conn.execute('UPDATE audit_context SET actor = ?, source = ? WHERE id = 1', (actor, source))


def reset_audit_context(conn):
    conn.execute("UPDATE audit_context SET actor = 'DIRECT_DB', source = 'DIRECT_DB' WHERE id = 1")


def fetch_member_profile(conn, user_id):
    return conn.execute(
        '''
        SELECT
            m.member_id,
            m.name,
            u.username,
            u.email,
            m.contact_number,
            u.role,
            r.role_name,
            h.hostel_name,
            m.hostel_room_no,
            l.location_name
        FROM member m
        JOIN users u ON m.user_id = u.id
        JOIN role r ON m.role_id = r.role_id
        LEFT JOIN hostel h ON m.hostel_id = h.hostel_id
        LEFT JOIN location l ON m.location_id = l.location_id
        WHERE m.user_id = ?
        ''',
        (user_id,)
    ).fetchone()


def serialize_member(row):
    if not row:
        return None

    location_parts = []
    if row['hostel_name']:
        location_parts.append(row['hostel_name'])
    if row['hostel_room_no']:
        location_parts.append(f"Room {row['hostel_room_no']}")
    if row['location_name']:
        location_parts.append(row['location_name'])

    return {
        "id": row["member_id"],
        "name": row["name"],
        "username": row["username"],
        "email": row["email"],
        "contact": row["contact_number"],
        "role": row["role"],
        "role_label": row["role_name"].capitalize(),
        "location": " | ".join(location_parts) if location_parts else "Not assigned"
    }


def fetch_complaint_query():
    return '''
        SELECT
            c.complaint_id,
            c.description,
            c.created_at,
            u.username,
            u.email,
            m.name AS member_name,
            s.status_name,
            h.hostel_name,
            c.hostel_room_no,
            l.location_name
        FROM complaint c
        JOIN member m ON c.member_id = m.member_id
        JOIN users u ON m.user_id = u.id
        JOIN status s ON c.status_id = s.status_id
        LEFT JOIN hostel h ON c.hostel_id = h.hostel_id
        LEFT JOIN location l ON c.location_id = l.location_id
    '''


def build_complaint_order_clause():
    return '''
        ORDER BY
            CASE lower(s.status_name)
                WHEN 'open' THEN 5
                WHEN 'assigned' THEN 4
                WHEN 'in progress' THEN 3
                WHEN 'resolved' THEN 2
                WHEN 'closed' THEN 1
                ELSE 0
            END DESC,
            c.created_at DESC,
            c.complaint_id DESC
    '''


def serialize_complaint(row):
    location_parts = []
    if row["hostel_name"]:
        location_parts.append(f"Hostel {row['hostel_name']}")
    if row["hostel_room_no"]:
        location_parts.append(f"Room {row['hostel_room_no']}")
    if row["location_name"]:
        location_parts.append(row["location_name"])

    return {
        "id": row["complaint_id"],
        "description": row["description"],
        "member": row["member_name"],
        "username": row["username"],
        "email": row["email"],
        "status": row["status_name"],
        "created_at": row["created_at"],
        "location": " | ".join(location_parts) if location_parts else "Not specified"
    }


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return jsonify({'error': 'No session found'}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Session expired'}), 401
        except Exception:
            return jsonify({'error': 'Invalid session token'}), 401

        return f(data, *args, **kwargs)

    return decorated


@app.route('/', methods=['GET'])
def welcome():
    return jsonify({"message": "Welcome to the FixIIT local API"}), 200


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('user') or not data.get('password'):
        return jsonify({"error": "Missing parameters"}), 401

    submitted_user = data['user'].strip()
    submitted_password = data['password']

    conn = get_db_connection()
    user = conn.execute(
        '''
        SELECT * FROM users
        WHERE (lower(trim(username)) = lower(?) OR lower(trim(email)) = lower(?))
          AND password = ?
        ''',
        (submitted_user, submitted_user, submitted_password)
    ).fetchone()
    conn.close()

    if user:
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        }, SECRET_KEY, algorithm="HS256")

        return jsonify({
            "message": "Login successful",
            "session_token": token
        }), 200

    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/isAuth', methods=['GET'])
@token_required
def is_auth(current_user):
    return jsonify({
        "message": "User is authenticated",
        "username": current_user['username'],
        "email": current_user['email'],
        "role": current_user['role']
    }), 200


@app.route('/change_password', methods=['PUT'])
@token_required
def change_password(current_user):
    data = request.get_json()
    new_password = (data or {}).get('new_password', '').strip()

    if not new_password:
        return jsonify({"error": "Password cannot be empty"}), 400

    conn = get_db_connection()
    try:
        set_audit_context(conn, current_user['username'])
        conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, current_user['user_id']))
        conn.commit()
        reset_audit_context(conn)
        conn.commit()
    finally:
        conn.close()

    return jsonify({"message": "Password updated successfully!"}), 200


@app.route('/portfolio', methods=['GET', 'POST'])
@token_required
def manage_portfolio(current_user):
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            if current_user['role'] not in ['Admin', 'admin']:
                write_audit_log(
                    current_user['username'],
                    'UNAUTHORIZED_MEMBER_CREATE_ATTEMPT',
                    source='API',
                    table_name='member',
                    details='Only admins can create members.',
                    conn=conn
                )
                conn.commit()
                return jsonify({"error": "Unauthorized. Admins only."}), 403

            data = request.get_json() or {}
            required_fields = ['name', 'username', 'email', 'contact', 'role_id']
            missing = [field for field in required_fields if not str(data.get(field, '')).strip()]
            if missing:
                return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

            role_id = int(data['role_id'])
            auth_role = 'Regular User'
            if role_id == 3:
                auth_role = 'Admin'
            elif role_id == 2:
                auth_role = 'Staff'

            default_password = "fixiit_password123"
            set_audit_context(conn, current_user['username'])
            try:
                cursor = conn.execute(
                    '''
                    INSERT INTO users (username, email, password, role)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (data['username'].strip(), data['email'].strip(), default_password, auth_role)
                )
                user_id = cursor.lastrowid

                conn.execute(
                    '''
                    INSERT INTO member (user_id, name, contact_number, role_id, location_id)
                    VALUES (?, ?, ?, ?, 1)
                    ''',
                    (user_id, data['name'].strip(), data['contact'].strip(), role_id)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                return jsonify({"error": "Username or email already exists, or the data is invalid."}), 400
            finally:
                set_audit_context(conn, 'DIRECT_DB', 'DIRECT_DB')
                conn.commit()

            return jsonify({"message": f"Member added successfully. Temporary password: {default_password}"}), 201

        if current_user['role'] in ['Admin', 'admin']:
            rows = conn.execute(
                '''
                SELECT
                    m.member_id,
                    m.name,
                    u.username,
                    u.email,
                    m.contact_number,
                    u.role,
                    r.role_name,
                    h.hostel_name,
                    m.hostel_room_no,
                    l.location_name
                FROM member m
                JOIN users u ON m.user_id = u.id
                JOIN role r ON m.role_id = r.role_id
                LEFT JOIN hostel h ON m.hostel_id = h.hostel_id
                LEFT JOIN location l ON m.location_id = l.location_id
                ORDER BY m.member_id DESC
                '''
            ).fetchall()
        else:
            own_profile = fetch_member_profile(conn, current_user['user_id'])
            rows = [own_profile] if own_profile else []

        return jsonify({"portfolio": [serialize_member(row) for row in rows if row]}), 200
    finally:
        conn.close()


@app.route('/portfolio/<int:member_id>', methods=['DELETE'])
@token_required
def delete_member(current_user, member_id):
    if current_user['role'] not in ['Admin', 'admin']:
        write_audit_log(
            current_user['username'],
            'UNAUTHORIZED_MEMBER_DELETE_ATTEMPT',
            source='API',
            table_name='member',
            details=f'member_id={member_id}'
        )
        return jsonify({"error": "Unauthorized. Admins only."}), 403

    conn = get_db_connection()
    try:
        member = conn.execute(
            '''
            SELECT m.member_id, m.user_id, u.username
            FROM member m
            JOIN users u ON m.user_id = u.id
            WHERE m.member_id = ?
            ''',
            (member_id,)
        ).fetchone()

        if not member:
            return jsonify({"error": "Member not found."}), 404

        set_audit_context(conn, current_user['username'])
        try:
            conn.execute('DELETE FROM member WHERE member_id = ?', (member_id,))
            conn.execute('DELETE FROM users WHERE id = ?', (member['user_id'],))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return jsonify({"error": "Cannot delete member. They may still be referenced by active records."}), 400
        finally:
            reset_audit_context(conn)
            conn.commit()

        return jsonify({"message": "Member deleted successfully!"}), 200
    finally:
        conn.close()


@app.route('/complaints', methods=['GET', 'POST'])
@token_required
def manage_complaints(current_user):
    conn = get_db_connection()
    try:
        member = conn.execute('SELECT member_id FROM member WHERE user_id = ?', (current_user['user_id'],)).fetchone()

        if request.method == 'POST':
            if not member:
                write_audit_log(
                    current_user['username'],
                    'COMPLAINT_CREATE_FAILED',
                    source='API',
                    table_name='complaint',
                    details='Member profile not found.',
                    conn=conn
                )
                conn.commit()
                return jsonify({"error": "Member profile not found."}), 404

            data = request.get_json() or {}
            description = str(data.get('description', '')).strip()
            location_type = str(data.get('location_type', '')).strip().lower()
            location_id = data.get('location_id')
            room_number = str(data.get('room_number', '')).strip()
            if not description:
                return jsonify({"error": "Complaint description cannot be empty."}), 400
            if location_type not in ['hostel', 'location']:
                return jsonify({"error": "Please choose a valid complaint location type."}), 400
            if location_id in [None, '']:
                return jsonify({"error": "Please choose a valid location option."}), 400

            try:
                location_id = int(location_id)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid location selection."}), 400

            hostel_id = None
            campus_location_id = None
            if location_type == 'hostel':
                hostel = conn.execute(
                    'SELECT hostel_id FROM hostel WHERE hostel_id = ?',
                    (location_id,)
                ).fetchone()
                if not hostel:
                    return jsonify({"error": "Selected hostel was not found."}), 404
                if not room_number:
                    return jsonify({"error": "Room number is required when reporting a hostel complaint."}), 400
                hostel_id = location_id
            else:
                location = conn.execute(
                    'SELECT location_id FROM location WHERE location_id = ?',
                    (location_id,)
                ).fetchone()
                if not location:
                    return jsonify({"error": "Selected location was not found."}), 404
                campus_location_id = location_id

            set_audit_context(conn, current_user['username'])
            conn.execute(
                '''
                INSERT INTO complaint (
                    member_id,
                    issue_type_id,
                    priority_id,
                    status_id,
                    description,
                    created_at,
                    hostel_id,
                    hostel_room_no,
                    location_id
                )
                VALUES (?, 1, 2, 1, ?, datetime('now'), ?, ?, ?)
                ''',
                (member['member_id'], description, hostel_id, room_number or None, campus_location_id)
            )
            conn.commit()
            reset_audit_context(conn)
            conn.commit()
            return jsonify({"message": "Complaint raised successfully!"}), 201

        base_query = fetch_complaint_query()
        status_filter = str(request.args.get('status', '')).strip().lower()
        order_clause = build_complaint_order_clause()
        if current_user['role'] in ['Admin', 'admin', 'Staff', 'staff']:
            params = []
            query = base_query
            if status_filter and status_filter != 'all':
                query += ' WHERE lower(s.status_name) = ?'
                params.append(status_filter)
            complaints_data = conn.execute(query + ' ' + order_clause, params).fetchall()
        else:
            if not member:
                return jsonify({"complaints": []}), 200

            params = [member['member_id']]
            query = base_query + ' WHERE c.member_id = ?'
            if status_filter and status_filter != 'all':
                query += ' AND lower(s.status_name) = ?'
                params.append(status_filter)
            complaints_data = conn.execute(
                query + ' ' + order_clause,
                params
            ).fetchall()

        complaints_list = [serialize_complaint(row) for row in complaints_data]

        return jsonify({"complaints": complaints_list}), 200
    finally:
        conn.close()


@app.route('/complaint_metadata', methods=['GET'])
@token_required
def complaint_metadata(current_user):
    conn = get_db_connection()
    try:
        hostels = conn.execute(
            'SELECT hostel_id, hostel_name FROM hostel ORDER BY hostel_name'
        ).fetchall()
        locations = conn.execute(
            'SELECT location_id, location_name FROM location ORDER BY location_name'
        ).fetchall()
        statuses = conn.execute(
            'SELECT status_id, status_name FROM status ORDER BY status_id'
        ).fetchall()

        return jsonify({
            "hostels": [{"id": row["hostel_id"], "name": row["hostel_name"]} for row in hostels],
            "locations": [{"id": row["location_id"], "name": row["location_name"]} for row in locations],
            "statuses": [{"id": row["status_id"], "name": row["status_name"]} for row in statuses]
        }), 200
    finally:
        conn.close()


@app.route('/complaints/<int:complaint_id>', methods=['PATCH'])
@token_required
def update_complaint_status(current_user, complaint_id):
    allowed_roles = ['Admin', 'Staff', 'admin', 'staff']
    if current_user['role'] not in allowed_roles:
        write_audit_log(
            current_user['username'],
            'UNAUTHORIZED_COMPLAINT_UPDATE_ATTEMPT',
            source='API',
            table_name='complaint',
            details=f'complaint_id={complaint_id}'
        )
        return jsonify({"error": "Unauthorized. Only Staff and Admins can update statuses."}), 403

    data = request.get_json() or {}
    status_id = data.get('status_id')
    if status_id is None:
        return jsonify({"error": "status_id is required."}), 400

    conn = get_db_connection()
    try:
        complaint = conn.execute('SELECT complaint_id FROM complaint WHERE complaint_id = ?', (complaint_id,)).fetchone()
        if not complaint:
            return jsonify({"error": "Complaint not found."}), 404

        set_audit_context(conn, current_user['username'])
        conn.execute('UPDATE complaint SET status_id = ? WHERE complaint_id = ?', (int(status_id), complaint_id))
        conn.commit()
        reset_audit_context(conn)
        conn.commit()
        return jsonify({"message": "Status updated successfully!"}), 200
    finally:
        conn.close()


@app.route('/complaints/<int:complaint_id>', methods=['DELETE'])
@token_required
def delete_complaint(current_user, complaint_id):
    conn = get_db_connection()
    try:
        complaint = conn.execute(
            '''
            SELECT c.complaint_id, m.user_id
            FROM complaint c
            JOIN member m ON c.member_id = m.member_id
            WHERE c.complaint_id = ?
            ''',
            (complaint_id,)
        ).fetchone()

        if not complaint:
            return jsonify({"error": "Complaint not found."}), 404

        is_admin = current_user['role'] in ['Admin', 'admin']
        is_owner = current_user['user_id'] == complaint['user_id']
        if not (is_admin or is_owner):
            write_audit_log(
                current_user['username'],
                'UNAUTHORIZED_COMPLAINT_DELETE_ATTEMPT',
                source='API',
                table_name='complaint',
                details=f'complaint_id={complaint_id}',
                conn=conn
            )
            conn.commit()
            return jsonify({"error": "Unauthorized. You can only delete your own complaints."}), 403

        set_audit_context(conn, current_user['username'])
        conn.execute('DELETE FROM complaint WHERE complaint_id = ?', (complaint_id,))
        conn.commit()
        reset_audit_context(conn)
        conn.commit()
        return jsonify({"message": "Complaint deleted successfully!"}), 200
    finally:
        conn.close()


@app.route('/audit_logs', methods=['GET'])
@token_required
def audit_logs(current_user):
    if current_user['role'] not in ['Admin', 'admin']:
        return jsonify({"error": "Unauthorized. Admins only."}), 403

    conn = get_db_connection()
    try:
        rows = conn.execute(
            '''
            SELECT actor, source, table_name, action, details, timestamp
            FROM logs
            ORDER BY timestamp DESC, id DESC
            LIMIT 200
            '''
        ).fetchall()
        entries = [{
            "actor": row["actor"],
            "source": row["source"],
            "table": row["table_name"],
            "action": row["action"],
            "details": row["details"],
            "timestamp": row["timestamp"]
        } for row in rows]
        return jsonify({"logs": entries}), 200
    finally:
        conn.close()


@app.route('/login_page', methods=['GET'])
def login_page():
    return render_template('login.html')


@app.route('/portfolio_page', methods=['GET'])
def portfolio_page():
    return render_template('portfolio.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
