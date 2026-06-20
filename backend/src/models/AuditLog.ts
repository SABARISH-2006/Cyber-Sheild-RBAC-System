import db from '../config/db.js';
import { collection, addDoc, getDocs, query, orderBy } from 'firebase/firestore';

export interface AuditLog {
  id?: string;
  user_id: string | null;
  action: string;
  resource: string | null;
  details: any;
  ip_address: string;
  status: 'success' | 'failure';
  created_at?: any;
}

const getAuditLogsCollection = () => collection(db, 'audit_logs');

export class AuditLogModel {
  static async create(
    user_id: string | null,
    action: string,
    resource: string | null,
    details: any,
    ip_address: string,
    status: 'success' | 'failure'
  ): Promise<void> {
    await addDoc(getAuditLogsCollection(), {
      user_id,
      action,
      resource,
      details,
      ip_address,
      status,
      created_at: new Date()
    });
  }

  static async getAll(): Promise<AuditLog[]> {
    const q = query(getAuditLogsCollection(), orderBy('created_at', 'desc'));
    const snapshot = await getDocs(q);
    return snapshot.docs.map(d => ({
      id: d.id,
      ...d.data()
    })) as AuditLog[];
  }
}
