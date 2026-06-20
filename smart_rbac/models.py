import time
from datetime import datetime
from smart_rbac.utils.firebase_client import firebase_client

_collection_cache = {}
CACHE_TTL = 5.0  # 5 seconds cache lifetime

def get_cached_collection(collection_name):
    now = time.time()
    if collection_name in _collection_cache:
        expire_time, cached_docs = _collection_cache[collection_name]
        if now < expire_time:
            return cached_docs
    return None

def set_cached_collection(collection_name, docs):
    now = time.time()
    _collection_cache[collection_name] = (now + CACHE_TTL, docs)

def invalidate_cache(collection_name):
    _collection_cache.pop(collection_name, None)

class FirestoreModel:
    collection_name = None

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        for k, v in kwargs.items():
            if isinstance(getattr(self.__class__, k, None), property):
                continue
            setattr(self, k, v)

    @classmethod
    def get(cls, doc_id):
        if not doc_id:
            return None
        cached_docs = get_cached_collection(cls.collection_name)
        if cached_docs is not None:
            for doc_data in cached_docs:
                if doc_data.get('id') == doc_id:
                    return cls(**doc_data)
        data = firebase_client.get_document(cls.collection_name, doc_id)
        if data:
            return cls(**data)
        return None

    @classmethod
    def get_all(cls):
        cached_docs = get_cached_collection(cls.collection_name)
        if cached_docs is not None:
            return [cls(**d) for d in cached_docs]
        docs = firebase_client.list_documents(cls.collection_name)
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
        payload = self.to_dict()
        if self.id:
            firebase_client.create_document(self.collection_name, self.id, payload)
        else:
            doc_id = firebase_client.create_document(self.collection_name, None, payload)
            self.id = doc_id
        invalidate_cache(self.collection_name)
        return self

    def delete(self):
        if self.id:
            firebase_client.delete_document(self.collection_name, self.id)
            invalidate_cache(self.collection_name)


class User(FirestoreModel):
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


class Role(FirestoreModel):
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


class Permission(FirestoreModel):
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


class AccessRequest(FirestoreModel):
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


class AuditLog(FirestoreModel):
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


class OTP(FirestoreModel):
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


class RiskScore(FirestoreModel):
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


class BehaviorAlert(FirestoreModel):
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


class RegistrationRequest(FirestoreModel):
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
