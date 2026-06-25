import time
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'cyber_shield.db')

_collection_cache = {}
CACHE_TTL = 300.0  # 5 minutes cache lifetime

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

_columns_cache = {}

def get_columns(table_name):
    if table_name not in _columns_cache:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        _columns_cache[table_name] = [row[1] for row in cursor.fetchall()]
        conn.close()
    return _columns_cache[table_name]

def parse_datetime(dt_str):
    if not dt_str:
        return None
    if isinstance(dt_str, datetime):
        return dt_str
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return dt_str

def get_cached_collection(collection_name):
    return None

def set_cached_collection(collection_name, docs):
    pass

def invalidate_cache(collection_name):
    pass

class BaseModel:
    collection_name = None

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        for k, v in kwargs.items():
            if isinstance(getattr(self.__class__, k, None), property):
                continue
            setattr(self, k, v)

    @classmethod
    def _get_role_permissions(cls, role_name):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name 
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN roles r ON r.id = rp.role_id
            WHERE r.name = ?
        """, (role_name,))
        perms = [row[0] for row in cursor.fetchall()]
        conn.close()
        return perms

    @classmethod
    def get(cls, doc_id):
        if not doc_id:
            return None
        cached_docs = get_cached_collection(cls.collection_name)
        if cached_docs is not None:
            for doc_data in cached_docs:
                if str(doc_data.get('id')) == str(doc_id):
                    return cls(**doc_data)
        
        table_name = cls.collection_name
        columns = get_columns(table_name)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if table_name in ('roles', 'permissions'):
            cursor.execute(f"SELECT * FROM {table_name} WHERE name = ?", (doc_id,))
        else:
            try:
                db_id = int(doc_id)
                cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (db_id,))
            except ValueError:
                conn.close()
                return None
                
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data = dict(row)
            if table_name == 'roles':
                role_name = data.get('name')
                data['permissions'] = cls._get_role_permissions(role_name)
                data['id'] = role_name
            elif table_name == 'permissions':
                data['id'] = data.get('name')
                
            for col in columns:
                if col == 'id' and table_name in ('roles', 'permissions'):
                    continue
                val = data[col]
                if val and col in ('created_at', 'updated_at', 'timestamp', 'expires_at', 'triggered_at', 'approved_at', 'calculated_at'):
                    data[col] = parse_datetime(val)
                if col in ('is_used',):
                    data[col] = bool(val)
                if col in ('factors', 'details') and isinstance(val, str):
                    try:
                        data[col] = json.loads(val)
                    except Exception:
                        pass
            return cls(**data)
        return None

    @classmethod
    def get_all(cls):
        cached_docs = get_cached_collection(cls.collection_name)
        if cached_docs is not None:
            return [cls(**d) for d in cached_docs]
            
        table_name = cls.collection_name
        columns = get_columns(table_name)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        conn.close()
        
        docs = []
        for row in rows:
            data = dict(row)
            if table_name == 'roles':
                role_name = data.get('name')
                data['permissions'] = cls._get_role_permissions(role_name)
                data['id'] = role_name
            elif table_name == 'permissions':
                data['id'] = data.get('name')
                
            for col in columns:
                if col == 'id' and table_name in ('roles', 'permissions'):
                    continue
                val = data[col]
                if val and col in ('created_at', 'updated_at', 'timestamp', 'expires_at', 'triggered_at', 'approved_at', 'calculated_at'):
                    data[col] = parse_datetime(val)
                if col in ('is_used',):
                    data[col] = bool(val)
                if col in ('factors', 'details') and isinstance(val, str):
                    try:
                        data[col] = json.loads(val)
                    except Exception:
                        pass
            docs.append(data)
            
        set_cached_collection(cls.collection_name, docs)
        return [cls(**d) for d in docs]

    @classmethod
    def find_by_field(cls, field, value):
        all_docs = cls.get_all()
        return [d for d in all_docs if getattr(d, field, None) == value]

    @classmethod
    def find_one_by_field(cls, field, value):
        all_docs = cls.get_all()
        for d in all_docs:
            if getattr(d, field, None) == value:
                return d
        return None

    def save(self):
        table_name = self.collection_name
        columns = get_columns(table_name)
        payload = self.to_dict()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if table_name in ('roles', 'permissions'):
            name = payload.get('name')
            cursor.execute(f"SELECT id FROM {table_name} WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            if row:
                update_fields = [col for col in columns if col not in ('id', 'name', 'created_at')]
                set_clause = ", ".join([f"{col} = ?" for col in update_fields])
                values = [payload.get(col) for col in update_fields]
                if 'updated_at' in columns:
                    set_clause += ", updated_at = ?"
                    values.append(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))
                values.append(name)
                cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE name = ?", tuple(values))
                db_id = row[0]
            else:
                insert_fields = [col for col in columns if col != 'id']
                placeholders = ", ".join(["?"] * len(insert_fields))
                values = []
                for col in insert_fields:
                    val = payload.get(col)
                    if val is None and col == 'created_at':
                        val = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                    elif val is None and col == 'updated_at':
                        val = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                    elif isinstance(val, datetime):
                        val = val.strftime('%Y-%m-%d %H:%M:%S.%f')
                    values.append(val)
                cursor.execute(f"INSERT INTO {table_name} ({', '.join(insert_fields)}) VALUES ({placeholders})", tuple(values))
                db_id = cursor.lastrowid
                
            if table_name == 'roles':
                cursor.execute("DELETE FROM role_permissions WHERE role_id = ?", (db_id,))
                for perm_name in self._permissions_list:
                    cursor.execute("SELECT id FROM permissions WHERE name = ?", (perm_name,))
                    perm_row = cursor.fetchone()
                    if perm_row:
                        cursor.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)", (db_id, perm_row[0]))
            self.id = name
        else:
            existing_id = None
            if self.id is not None:
                try:
                    existing_id = int(self.id)
                except ValueError:
                    pass
            
            db_payload = {}
            for col in columns:
                if col == 'id':
                    continue
                val = payload.get(col)
                if col in ('factors', 'details') and (isinstance(val, list) or isinstance(val, dict)):
                    val = json.dumps(val)
                if isinstance(val, bool):
                    val = 1 if val else 0
                if isinstance(val, datetime):
                    val = val.strftime('%Y-%m-%d %H:%M:%S.%f')
                db_payload[col] = val
                
            if existing_id is not None:
                update_fields = list(db_payload.keys())
                if 'created_at' in update_fields:
                    update_fields.remove('created_at')
                set_clause = ", ".join([f"{col} = ?" for col in update_fields])
                values = [db_payload[col] for col in update_fields]
                if 'updated_at' in columns:
                    set_clause += ", updated_at = ?"
                    values.append(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))
                values.append(existing_id)
                cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE id = ?", tuple(values))
            else:
                insert_fields = list(db_payload.keys())
                placeholders = ", ".join(["?"] * len(insert_fields))
                values = [db_payload[col] for col in insert_fields]
                cursor.execute(f"INSERT INTO {table_name} ({', '.join(insert_fields)}) VALUES ({placeholders})", tuple(values))
                self.id = cursor.lastrowid
                
        conn.commit()
        conn.close()
        invalidate_cache(table_name)
        return self

    def delete(self):
        if not self.id:
            return
        table_name = self.collection_name
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if table_name in ('roles', 'permissions'):
            if table_name == 'roles':
                cursor.execute("SELECT id FROM roles WHERE name = ?", (self.id,))
                role_row = cursor.fetchone()
                if role_row:
                    cursor.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_row[0],))
            cursor.execute(f"DELETE FROM {table_name} WHERE name = ?", (self.id,))
        else:
            try:
                db_id = int(self.id)
                cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (db_id,))
            except ValueError:
                pass
                
        conn.commit()
        conn.close()
        invalidate_cache(table_name)

# Alias to keep compatibility with any code referencing FirestoreModel
FirestoreModel = BaseModel

class User(BaseModel):
    collection_name = 'users'

    def __init__(self, **kwargs):
        self.username = None
        self.email = None
        self.login_id = None
        self.password_hash = None
        self.role = 'Employee'
        self.status = 'active'
        self.failed_login_attempts = 0
        self.last_login_device = None
        self.last_login_browser = None
        self.profile_photo = 'avatar-default.png'
        self.created_at = datetime.utcnow()
        super().__init__(**kwargs)

    def generate_login_id(self):
        if self.login_id:
            return self.login_id
        
        role_prefixes = {
            'Employee': 'EMP',
            'Manager': 'MGR',
            'Admin': 'ADMIN',
            'Auditor': 'AUDIT'
        }
        prefix = role_prefixes.get(self.role, 'USER')
        
        existing_users = User.get_all()
        count = sum(1 for u in existing_users if u.login_id and u.login_id.startswith(prefix)) + 1
        self.login_id = f"{prefix}{count:03d}"
        return self.login_id

    @classmethod
    def find_by_login_id(cls, login_id):
        return cls.find_one_by_field('login_id', login_id)

    @classmethod
    def find_by_username(cls, username):
        return cls.find_one_by_field('username', username)

    @classmethod
    def find_by_email(cls, email):
        return cls.find_one_by_field('email', email)

    @property
    def access_requests(self):
        return AccessRequest.find_by_field('user_id', self.id)

    @property
    def otps(self):
        return OTP.find_by_field('user_id', self.id)

    @property
    def risk_scores(self):
        return RiskScore.find_by_field('user_id', self.id)

    @property
    def behavior_alerts(self):
        return BehaviorAlert.find_by_field('user_id', self.id)

    def to_dict(self):
        return {
            'username': self.username,
            'email': self.email,
            'login_id': self.login_id,
            'password_hash': self.password_hash,
            'role': self.role,
            'status': self.status,
            'failed_login_attempts': int(self.failed_login_attempts or 0),
            'last_login_device': self.last_login_device,
            'last_login_browser': self.last_login_browser,
            'profile_photo': self.profile_photo or 'avatar-default.png',
            'created_at': self.created_at
        }


class PermissionListProxy(list):
    def __init__(self, role_obj, initial_list):
        self.role_obj = role_obj
        super().__init__(initial_list)

    def append(self, perm):
        super().append(perm)
        if perm.name not in self.role_obj._permissions_list:
            self.role_obj._permissions_list.append(perm.name)

    def clear(self):
        super().clear()
        self.role_obj._permissions_list.clear()

    def remove(self, perm):
        super().remove(perm)
        if perm.name in self.role_obj._permissions_list:
            self.role_obj._permissions_list.remove(perm.name)


class Role(BaseModel):
    collection_name = 'roles'

    def __init__(self, **kwargs):
        self.name = None
        self.description = None
        self._permissions_list = []
        super().__init__(**kwargs)
        if 'permissions' in kwargs:
            self._permissions_list = kwargs['permissions']

    @classmethod
    def find_by_name(cls, name):
        return cls.get(name)

    @property
    def permissions(self):
        perms_objects = []
        for p_name in self._permissions_list:
            p = Permission.find_by_name(p_name)
            if p:
                perms_objects.append(p)
        return PermissionListProxy(self, perms_objects)

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'permissions': self._permissions_list
        }


class Permission(BaseModel):
    collection_name = 'permissions'

    def __init__(self, **kwargs):
        self.name = None
        self.description = None
        self.resource = None
        self.action = None
        super().__init__(**kwargs)

    @classmethod
    def find_by_name(cls, name):
        return cls.get(name)

    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'resource': self.resource or self.name,
            'action': self.action or 'all'
        }


class AccessRequest(BaseModel):
    collection_name = 'access_requests'

    def __init__(self, **kwargs):
        self.user_id = None
        self.requested_permission = None
        self.reason = None
        self.status = 'pending_manager'
        self.approved_by = None
        self.timestamp = datetime.utcnow()
        super().__init__(**kwargs)

    @property
    def user(self):
        return User.get(self.user_id)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'requested_permission': self.requested_permission,
            'reason': self.reason,
            'status': self.status,
            'approved_by': self.approved_by,
            'timestamp': self.timestamp
        }


class AuditLog(BaseModel):
    collection_name = 'audit_logs'

    def __init__(self, **kwargs):
        self.username = None
        self.action = None
        self.ip_address = None
        self.timestamp = datetime.utcnow()
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'username': self.username,
            'action': self.action,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp
        }


class OTP(BaseModel):
    collection_name = 'otps'

    def __init__(self, **kwargs):
        self.user_id = None
        self.otp_code_hash = None
        self.expires_at = None
        self.is_used = False
        self.created_at = datetime.utcnow()
        super().__init__(**kwargs)

    @property
    def user(self):
        return User.get(self.user_id)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'otp_code_hash': self.otp_code_hash,
            'expires_at': self.expires_at,
            'is_used': bool(self.is_used),
            'created_at': self.created_at
        }


class RiskScore(BaseModel):
    collection_name = 'risk_scores'

    def __init__(self, **kwargs):
        self.user_id = None
        self.score = 0.0
        self.risk_level = 'Low'
        self.factors = None
        self.calculated_at = datetime.utcnow()
        super().__init__(**kwargs)

    @property
    def user(self):
        return User.get(self.user_id)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'score': float(self.score or 0.0),
            'risk_level': self.risk_level,
            'factors': self.factors,
            'calculated_at': self.calculated_at
        }


class BehaviorAlert(BaseModel):
    collection_name = 'behavior_alerts'

    def __init__(self, **kwargs):
        self.user_id = None
        self.alert_type = None
        self.description = None
        self.status = 'open'
        self.triggered_at = datetime.utcnow()
        super().__init__(**kwargs)

    @property
    def user(self):
        return User.get(self.user_id)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'alert_type': self.alert_type,
            'description': self.description,
            'status': self.status,
            'triggered_at': self.triggered_at
        }


class RegistrationRequest(BaseModel):
    collection_name = 'registration_requests'

    def __init__(self, **kwargs):
        self.user_id = None
        self.username = None
        self.email = None
        self.role = None
        self.login_id = None
        self.status = 'pending'
        self.approval_notes = None
        self.approved_by = None
        self.created_at = datetime.utcnow()
        self.approved_at = None
        super().__init__(**kwargs)

    @property
    def user(self):
        return User.get(self.user_id)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'login_id': self.login_id,
            'status': self.status,
            'approval_notes': self.approval_notes,
            'approved_by': self.approved_by,
            'created_at': self.created_at,
            'approved_at': self.approved_at
        }


class DbCompat:
    def __init__(self):
        pass
    def init_app(self, app):
        pass
    def drop_all(self):
        pass
    def create_all(self):
        pass

db = DbCompat()
