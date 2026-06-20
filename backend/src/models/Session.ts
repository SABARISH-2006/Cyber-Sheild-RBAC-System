import db from '../config/db.js';
import { 
  collection, 
  query, 
  where, 
  getDocs, 
  addDoc, 
  doc, 
  deleteDoc
} from 'firebase/firestore';

export interface UserSession {
  id?: string;
  user_id: string;
  token_hash: string;
  ip_address: string;
  user_agent: string | null;
  expires_at: any;
  created_at?: any;
}

const getSessionsCollection = () => collection(db, 'user_sessions');

export class SessionModel {
  static async create(
    user_id: string,
    token_hash: string,
    ip_address: string,
    user_agent: string | null,
    expires_at: Date
  ): Promise<void> {
    await addDoc(getSessionsCollection(), {
      user_id,
      token_hash,
      ip_address,
      user_agent,
      expires_at,
      created_at: new Date()
    });
  }

  static async findActiveSession(token_hash: string): Promise<UserSession | null> {
    const q = query(
      getSessionsCollection(),
      where('token_hash', '==', token_hash)
    );
    const snapshot = await getDocs(q);
    if (snapshot.empty) return null;
    
    const d = snapshot.docs[0];
    const session = { id: d.id, ...d.data() } as UserSession;
    
    const expiresAt = session.expires_at.toDate ? session.expires_at.toDate() : new Date(session.expires_at);
    if (expiresAt < new Date()) {
      deleteDoc(doc(db, 'user_sessions', d.id)).catch(() => {});
      return null;
    }
    return session;
  }

  static async deleteByTokenHash(token_hash: string): Promise<void> {
    const q = query(getSessionsCollection(), where('token_hash', '==', token_hash));
    const snapshot = await getDocs(q);
    for (const d of snapshot.docs) {
      await deleteDoc(doc(db, 'user_sessions', d.id));
    }
  }
}
