import db from '../config/db.js';
import { 
  collection, 
  query, 
  where, 
  getDocs, 
  doc, 
  getDoc, 
  addDoc, 
  updateDoc, 
  deleteDoc,
  serverTimestamp
} from 'firebase/firestore';
import { RoleModel } from './Role.js';

export interface User {
  id?: string;
  loginId?: string;
  username: string;
  email: string;
  password_hash: string;
  status: 'active' | 'suspended' | 'inactive';
  roles: string[]; // Denormalized list of role names (e.g. ["SuperAdmin"])
  created_at?: any;
  updated_at?: any;
}

const getUsersCollection = () => collection(db, 'users');

const getRolePrefix = (roleName: string) => {
  const mapping: Record<string, string> = {
    SuperAdmin: 'ADM',
    SecurityAdmin: 'EMP',
    Analyst: 'MAN',
    Auditor: 'AUD'
  };
  return mapping[roleName] || 'USR';
};

export class UserModel {
  static async generateLoginId(roleName: string): Promise<string> {
    const prefix = getRolePrefix(roleName);
    const q = query(getUsersCollection(), where('roles', 'array-contains', roleName));
    const snapshot = await getDocs(q);

    let maxNumber = 100;
    snapshot.docs.forEach(docSnap => {
      const existingLoginId = docSnap.data().loginId as string | undefined;
      if (!existingLoginId) return;
      const match = existingLoginId.match(/_(\d+)$/);
      if (match) {
        const numeric = parseInt(match[1], 10);
        if (Number.isFinite(numeric)) {
          maxNumber = Math.max(maxNumber, numeric);
        }
      }
    });

    return `${prefix}_${String(maxNumber + 1).padStart(3, '0')}`;
  }

  static async findByLoginId(loginId: string): Promise<User | null> {
    const q = query(getUsersCollection(), where('loginId', '==', loginId));
    const snapshot = await getDocs(q);
    if (snapshot.empty) return null;
    const d = snapshot.docs[0];
    return { id: d.id, ...d.data() } as User;
  }

  static async getAll(): Promise<User[]> {
    const snapshot = await getDocs(getUsersCollection());
    return snapshot.docs.map(d => ({
      id: d.id,
      ...d.data()
    })) as User[];
  }

  static async findById(id: string): Promise<User | null> {
    const docRef = doc(db, 'users', id);
    const docSnap = await getDoc(docRef);
    if (!docSnap.exists()) return null;
    return { id: docSnap.id, ...docSnap.data() } as User;
  }

  static async findByUsername(username: string): Promise<User | null> {
    const q = query(getUsersCollection(), where('username', '==', username));
    const snapshot = await getDocs(q);
    if (snapshot.empty) return null;
    const d = snapshot.docs[0];
    return { id: d.id, ...d.data() } as User;
  }

  static async findByEmail(email: string): Promise<User | null> {
    const q = query(getUsersCollection(), where('email', '==', email));
    const snapshot = await getDocs(q);
    if (snapshot.empty) return null;
    const d = snapshot.docs[0];
    return { id: d.id, ...d.data() } as User;
  }

  static async create(user: Omit<User, 'id'>): Promise<string> {
    // Check uniqueness of username, email, and loginId first
    const existingUser = await this.findByUsername(user.username);
    if (existingUser) {
      throw { code: 'ER_DUP_ENTRY', message: 'Username already exists' };
    }

    const existingEmail = await this.findByEmail(user.email);
    if (existingEmail) {
      throw { code: 'ER_DUP_ENTRY', message: 'Email already exists' };
    }

    if (user.loginId) {
      const existingLoginId = await this.findByLoginId(user.loginId);
      if (existingLoginId) {
        throw { code: 'ER_DUP_ENTRY', message: 'Login ID already exists' };
      }
    }

    if (!user.loginId) {
      user.loginId = await this.generateLoginId(user.roles[0] || 'StandardUser');
    }

    const docRef = await addDoc(getUsersCollection(), {
      ...user,
      created_at: new Date(),
      updated_at: new Date()
    });
    return docRef.id;
  }

  static async update(id: string, updates: Partial<Pick<User, 'email' | 'status' | 'roles'>>): Promise<void> {
    // If updating email, check uniqueness
    if (updates.email) {
      const existingEmail = await this.findByEmail(updates.email);
      if (existingEmail && existingEmail.id !== id) {
        throw { code: 'ER_DUP_ENTRY', message: 'Email already exists' };
      }
    }

    const docRef = doc(db, 'users', id);
    await updateDoc(docRef, {
      ...updates,
      updated_at: new Date()
    });
  }

  static async delete(id: string): Promise<void> {
    const docRef = doc(db, 'users', id);
    await deleteDoc(docRef);
  }

  static async getPermissions(id: string): Promise<string[]> {
    const user = await this.findById(id);
    if (!user) return [];

    const permissionsSet = new Set<string>();
    for (const roleName of user.roles) {
      const role = await RoleModel.findByName(roleName);
      if (role && role.permissions) {
        role.permissions.forEach(p => permissionsSet.add(p));
      }
    }
    return Array.from(permissionsSet);
  }
}
