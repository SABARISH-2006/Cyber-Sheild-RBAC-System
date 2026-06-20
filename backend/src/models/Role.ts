import db from '../config/db.js';
import { collection, getDocs, doc, setDoc, getDoc, deleteDoc, updateDoc } from 'firebase/firestore';

export interface Role {
  id?: string;
  name: string;
  description: string;
  permissions: string[]; // Denormalized list of permission names
  created_at?: any;
  updated_at?: any;
}

const getRolesCollection = () => collection(db, 'roles');

export class RoleModel {
  static async getAll(): Promise<Role[]> {
    const snapshot = await getDocs(getRolesCollection());
    return snapshot.docs.map(d => ({
      id: d.id,
      ...d.data()
    })) as Role[];
  }

  static async findByName(name: string): Promise<Role | null> {
    const docRef = doc(db, 'roles', name);
    const docSnap = await getDoc(docRef);
    if (!docSnap.exists()) return null;
    return { id: docSnap.id, ...docSnap.data() } as Role;
  }

  static async create(name: string, description: string, permissions: string[]): Promise<void> {
    const docRef = doc(db, 'roles', name);
    await setDoc(docRef, {
      name,
      description,
      permissions,
      created_at: new Date(),
      updated_at: new Date()
    });
  }

  static async update(name: string, description: string, permissions: string[]): Promise<void> {
    const docRef = doc(db, 'roles', name);
    await updateDoc(docRef, {
      description,
      permissions,
      updated_at: new Date()
    });
  }

  static async delete(name: string): Promise<void> {
    const docRef = doc(db, 'roles', name);
    await deleteDoc(docRef);
  }
}
