import db from '../config/db.js';
import { collection, getDocs, doc, setDoc, query, orderBy, getDoc } from 'firebase/firestore';

export interface Permission {
  id?: string;
  name: string;
  resource: string;
  action: string;
  description: string;
  created_at?: any;
}

const getPermissionsCollection = () => collection(db, 'permissions');

export class PermissionModel {
  static async getAll(): Promise<Permission[]> {
    const q = query(getPermissionsCollection(), orderBy('name'));
    const snapshot = await getDocs(q);
    return snapshot.docs.map(d => ({
      id: d.id,
      ...d.data()
    })) as Permission[];
  }

  static async findByName(name: string): Promise<Permission | null> {
    const docRef = doc(db, 'permissions', name);
    const docSnap = await getDoc(docRef);
    if (!docSnap.exists()) return null;
    return { id: docSnap.id, ...docSnap.data() } as Permission;
  }

  static async create(permission: Permission): Promise<void> {
    const docRef = doc(db, 'permissions', permission.name);
    await setDoc(docRef, {
      name: permission.name,
      resource: permission.resource,
      action: permission.action,
      description: permission.description,
      created_at: new Date()
    });
  }
}
