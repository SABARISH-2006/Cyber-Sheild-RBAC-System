import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Explicitly load root and backend .env files to gather Firebase configuration
load_dotenv()
backend_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'backend', '.env')
if os.path.exists(backend_env):
    load_dotenv(dotenv_path=backend_env)

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "cyber-shield-73e01")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "AIzaSyB3zxl-vXCx3_1Um3X2dJmw8-Rzj5NDsNY")

class FirestoreRESTClient:
    def __init__(self, project_id=FIREBASE_PROJECT_ID, api_key=FIREBASE_API_KEY):
        self.project_id = project_id
        self.api_key = api_key
        self.base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"

    def _get_url(self, path=""):
        url = f"{self.base_url}"
        if path:
            url += f"/{path}"
        if self.api_key:
            url += f"?key={self.api_key}"
        return url

    @staticmethod
    def to_firestore_value(val):
        if val is None:
            return {'nullValue': None}
        elif isinstance(val, bool):
            return {'booleanValue': val}
        elif isinstance(val, int):
            return {'integerValue': str(val)}
        elif isinstance(val, float):
            return {'doubleValue': val}
        elif isinstance(val, str):
            return {'stringValue': val}
        elif isinstance(val, datetime):
            return {'timestampValue': val.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'}
        elif isinstance(val, list):
            return {'arrayValue': {'values': [FirestoreRESTClient.to_firestore_value(x) for x in val]}}
        elif isinstance(val, dict):
            return {'mapValue': {'fields': {k: FirestoreRESTClient.to_firestore_value(v) for k, v in val.items()}}}
        else:
            return {'stringValue': str(val)}

    @staticmethod
    def from_firestore_value(f_val):
        if not isinstance(f_val, dict):
            return f_val
        for k, v in f_val.items():
            if k == 'nullValue':
                return None
            elif k == 'booleanValue':
                return v
            elif k == 'integerValue':
                return int(v)
            elif k == 'doubleValue':
                return float(v)
            elif k == 'stringValue':
                return v
            elif k == 'timestampValue':
                # Convert Firestore timestamp to datetime object
                dt_str = v.replace('Z', '')
                try:
                    # Strip fractional seconds precision beyond microseconds if present
                    if '.' in dt_str:
                        parts = dt_str.split('.')
                        dt_str = parts[0] + '.' + parts[1][:6]
                    return datetime.fromisoformat(dt_str)
                except Exception:
                    return v
            elif k == 'arrayValue':
                values = v.get('values', [])
                return [FirestoreRESTClient.from_firestore_value(x) for x in values]
            elif k == 'mapValue':
                fields = v.get('fields', {})
                return {mk: FirestoreRESTClient.from_firestore_value(mv) for mk, mv in fields.items()}
        return f_val

    @staticmethod
    def to_firestore_doc(data):
        return {'fields': {k: FirestoreRESTClient.to_firestore_value(v) for k, v in data.items()}}

    @staticmethod
    def from_firestore_doc(doc_json):
        fields = doc_json.get('fields', {})
        data = {k: FirestoreRESTClient.from_firestore_value(v) for k, v in fields.items()}
        name = doc_json.get('name', '')
        if name:
            data['id'] = name.split('/')[-1]
        return data

    def get_document(self, collection, doc_id):
        url = self._get_url(f"{collection}/{doc_id}")
        resp = requests.get(url)
        if resp.status_code == 200:
            return self.from_firestore_doc(resp.json())
        return None

    def create_document(self, collection, doc_id, data):
        # Remove "id" from dictionary if it exists to avoid redundancy in fields
        payload = {k: v for k, v in data.items() if k != 'id'}
        doc_payload = self.to_firestore_doc(payload)
        
        if doc_id:
            # PUT to create/overwrite a specific document ID
            url = self._get_url(f"{collection}/{doc_id}")
            resp = requests.patch(url, json=doc_payload)
        else:
            # POST to let Firestore auto-assign document ID
            url = self._get_url(collection)
            resp = requests.post(url, json=doc_payload)
            
        if resp.status_code in [200, 201]:
            return self.from_firestore_doc(resp.json())['id']
        raise Exception(f"Failed to save document to {collection}: {resp.text}")

    def update_document(self, collection, doc_id, data):
        # Merge update fields
        payload = {k: v for k, v in data.items() if k != 'id'}
        doc_payload = self.to_firestore_doc(payload)
        
        # Build updateMask query parameters for partial update
        update_mask_params = "&".join([f"updateMask.fieldPaths={k}" for k in payload.keys()])
        url = self._get_url(f"{collection}/{doc_id}")
        if update_mask_params:
            url += f"&{update_mask_params}"
            
        resp = requests.patch(url, json=doc_payload)
        if resp.status_code not in [200, 204]:
            raise Exception(f"Failed to update document in {collection}: {resp.text}")

    def delete_document(self, collection, doc_id):
        url = self._get_url(f"{collection}/{doc_id}")
        resp = requests.delete(url)
        if resp.status_code not in [200, 204, 404]:
            raise Exception(f"Failed to delete document from {collection}: {resp.text}")

    def list_documents(self, collection):
        url = self._get_url(collection)
        resp = requests.get(url)
        if resp.status_code == 200:
            docs = resp.json().get('documents', [])
            return [self.from_firestore_doc(d) for d in docs]
        return []

    def generate_firestore_id(self):
        import random
        import string
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(20))

    def batch_create_documents(self, collection, docs_list):
        writes = []
        for doc_id, data in docs_list:
            if not doc_id:
                doc_id = self.generate_firestore_id()
            payload = {k: v for k, v in data.items() if k != 'id'}
            doc_payload = self.to_firestore_doc(payload)
            doc_name = f"projects/{self.project_id}/databases/(default)/documents/{collection}/{doc_id}"
            
            writes.append({
                'update': {
                    'name': doc_name,
                    'fields': doc_payload['fields']
                }
            })
            
        chunk_size = 500
        for i in range(0, len(writes), chunk_size):
            chunk = writes[i:i+chunk_size]
            url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents:commit"
            if self.api_key:
                url += f"?key={self.api_key}"
            
            resp = requests.post(url, json={'writes': chunk}, timeout=15)
            if resp.status_code != 200:
                raise Exception(f"Batch write failed: {resp.text}")

# Singleton instance
firebase_client = FirestoreRESTClient()

