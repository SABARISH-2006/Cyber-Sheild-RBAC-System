import sqlite3
import os
from datetime import datetime
from smart_rbac.utils.firebase_client import firebase_client

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cyber_shield.db')

def parse_datetime(dt_str):
    if not dt_str:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return dt_str

def migrate():
    print("==================================================")
    print("STARTING OPTIMIZED BATCH SQLITE TO FIREBASE MIGRATION...")
    print(f"SQLite DB Path: {DB_PATH}")
    print("==================================================")
    
    if not os.path.exists(DB_PATH):
        print(f"ERROR: SQLite database file not found at {DB_PATH}!")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Migrate Permissions
    print("\n1. Collecting Permissions...")
    cursor.execute("SELECT id, name, description FROM permissions")
    perms = cursor.fetchall()
    
    permissions_map = {} # sqlite_id -> name
    perm_batch = []
    for p in perms:
        name = p['name']
        description = p['description']
        
        resource = name
        action = "all"
        if "_" in name:
            parts = name.split("_")
            action = parts[0]
            resource = parts[1]
            
        perm_data = {
            'name': name,
            'resource': resource,
            'action': action,
            'description': description,
            'created_at': datetime.utcnow()
        }
        perm_batch.append((name, perm_data))
        permissions_map[p['id']] = name
        
    print(f"   Uploading {len(perm_batch)} permissions...")
    firebase_client.batch_create_documents('permissions', perm_batch)
    print("   Done.")
        
    # 2. Migrate Roles
    print("\n2. Collecting Roles...")
    cursor.execute("SELECT id, name, description FROM roles")
    roles = cursor.fetchall()
    
    role_batch = []
    for r in roles:
        role_id = r['id']
        name = r['name']
        description = r['description']
        
        cursor.execute("""
            SELECT permission_id FROM role_permissions WHERE role_id = ?
        """, (role_id,))
        rp_rows = cursor.fetchall()
        role_perms = [permissions_map[rp['permission_id']] for rp in rp_rows if rp['permission_id'] in permissions_map]
        
        role_data = {
            'name': name,
            'description': description,
            'permissions': role_perms,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        role_batch.append((name, role_data))
        
    print(f"   Uploading {len(role_batch)} roles...")
    firebase_client.batch_create_documents('roles', role_batch)
    print("   Done.")
        
    # 3. Migrate Users
    print("\n3. Collecting Users...")
    cursor.execute("""
        SELECT id, username, email, login_id, password_hash, role, status,
               failed_login_attempts, last_login_device, last_login_browser,
               profile_photo, created_at
        FROM users
    """)
    users = cursor.fetchall()
    
    user_id_map = {} # sqlite_id -> firestore_doc_id
    user_batch = []
    for u in users:
        sqlite_id = u['id']
        username = u['username']
        firestore_id = firebase_client.generate_firestore_id()
        user_id_map[sqlite_id] = firestore_id
        
        user_data = {
            'username': username,
            'email': u['email'],
            'login_id': u['login_id'],
            'password_hash': u['password_hash'],
            'role': u['role'],
            'status': u['status'],
            'failed_login_attempts': u['failed_login_attempts'] or 0,
            'last_login_device': u['last_login_device'],
            'last_login_browser': u['last_login_browser'],
            'profile_photo': u['profile_photo'] or 'avatar-default.png',
            'created_at': parse_datetime(u['created_at']) or datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        user_batch.append((firestore_id, user_data))
        
    print(f"   Uploading {len(user_batch)} users...")
    firebase_client.batch_create_documents('users', user_batch)
    print("   Done.")
        
    # 4. Migrate Access Requests
    print("\n4. Collecting Access Requests...")
    cursor.execute("""
        SELECT id, user_id, requested_permission, reason, status, approved_by, timestamp
        FROM access_requests
    """)
    reqs = cursor.fetchall()
    
    req_batch = []
    for r in reqs:
        sqlite_uid = r['user_id']
        if sqlite_uid not in user_id_map:
            continue
            
        req_data = {
            'user_id': user_id_map[sqlite_uid],
            'requested_permission': r['requested_permission'],
            'reason': r['reason'],
            'status': r['status'],
            'approved_by': r['approved_by'],
            'timestamp': parse_datetime(r['timestamp']) or datetime.utcnow()
        }
        req_batch.append((None, req_data))
        
    print(f"   Uploading {len(req_batch)} access requests...")
    if req_batch:
        firebase_client.batch_create_documents('access_requests', req_batch)
    print("   Done.")
        
    # 5. Migrate Audit Logs
    print("\n5. Collecting Audit Logs...")
    cursor.execute("SELECT id, username, action, ip_address, timestamp FROM audit_logs")
    logs = cursor.fetchall()
    
    log_batch = []
    for l in logs:
        log_data = {
            'username': l['username'],
            'action': l['action'],
            'ip_address': l['ip_address'],
            'timestamp': parse_datetime(l['timestamp']) or datetime.utcnow()
        }
        log_batch.append((None, log_data))
        
    print(f"   Uploading {len(log_batch)} audit logs...")
    if log_batch:
        firebase_client.batch_create_documents('audit_logs', log_batch)
    print("   Done.")
    
    # 6. Migrate OTPs
    print("\n6. Collecting OTPs...")
    cursor.execute("SELECT id, user_id, otp_code_hash, expires_at, is_used, created_at FROM otps")
    otps = cursor.fetchall()
    
    otp_batch = []
    for o in otps:
        sqlite_uid = o['user_id']
        if sqlite_uid not in user_id_map:
            continue
            
        otp_data = {
            'user_id': user_id_map[sqlite_uid],
            'otp_code_hash': o['otp_code_hash'],
            'expires_at': parse_datetime(o['expires_at']),
            'is_used': bool(o['is_used']),
            'created_at': parse_datetime(o['created_at']) or datetime.utcnow()
        }
        otp_batch.append((None, otp_data))
        
    print(f"   Uploading {len(otp_batch)} OTP records...")
    if otp_batch:
        firebase_client.batch_create_documents('otps', otp_batch)
    print("   Done.")
    
    # 7. Migrate Risk Scores
    print("\n7. Collecting Risk Scores...")
    cursor.execute("SELECT id, user_id, score, risk_level, factors, calculated_at FROM risk_scores")
    scores = cursor.fetchall()
    
    score_batch = []
    for s in scores:
        sqlite_uid = s['user_id']
        if sqlite_uid not in user_id_map:
            continue
            
        score_data = {
            'user_id': user_id_map[sqlite_uid],
            'score': float(s['score']),
            'risk_level': s['risk_level'],
            'factors': s['factors'],
            'calculated_at': parse_datetime(s['calculated_at']) or datetime.utcnow()
        }
        score_batch.append((None, score_data))
        
    print(f"   Uploading {len(score_batch)} risk scores...")
    if score_batch:
        firebase_client.batch_create_documents('risk_scores', score_batch)
    print("   Done.")
        
    # 8. Migrate Behavior Alerts
    print("\n8. Collecting Behavior Alerts...")
    cursor.execute("SELECT id, user_id, alert_type, description, status, triggered_at FROM behavior_alerts")
    alerts = cursor.fetchall()
    
    alert_batch = []
    for a in alerts:
        sqlite_uid = a['user_id']
        if sqlite_uid not in user_id_map:
            continue
            
        alert_data = {
            'user_id': user_id_map[sqlite_uid],
            'alert_type': a['alert_type'],
            'description': a['description'],
            'status': a['status'],
            'triggered_at': parse_datetime(a['triggered_at']) or datetime.utcnow()
        }
        alert_batch.append((None, alert_data))
        
    print(f"   Uploading {len(alert_batch)} behavior alerts...")
    if alert_batch:
        firebase_client.batch_create_documents('behavior_alerts', alert_batch)
    print("   Done.")
        
    # 9. Migrate Registration Requests
    print("\n9. Collecting Registration Requests...")
    cursor.execute("""
        SELECT id, user_id, username, email, role, login_id, status, approval_notes, approved_by, created_at, approved_at
        FROM registration_requests
    """)
    reg_reqs = cursor.fetchall()
    
    rr_batch = []
    for rr in reg_reqs:
        sqlite_uid = rr['user_id']
        if sqlite_uid not in user_id_map:
            continue
            
        rr_data = {
            'user_id': user_id_map[sqlite_uid],
            'username': rr['username'],
            'email': rr['email'],
            'role': rr['role'],
            'login_id': rr['login_id'],
            'status': rr['status'],
            'approval_notes': rr['approval_notes'],
            'approved_by': rr['approved_by'],
            'created_at': parse_datetime(rr['created_at']) or datetime.utcnow(),
            'approved_at': parse_datetime(rr['approved_at'])
        }
        rr_batch.append((None, rr_data))
        
    print(f"   Uploading {len(rr_batch)} registration requests...")
    if rr_batch:
        firebase_client.batch_create_documents('registration_requests', rr_batch)
    print("   Done.")
        
    conn.close()
    print("\n==================================================")
    print("SUCCESS: DATABASE MIGRATION COMPLETED!")
    print("==================================================")
    return True

if __name__ == '__main__':
    migrate()
