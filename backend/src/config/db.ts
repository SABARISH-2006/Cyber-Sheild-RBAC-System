import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import dotenv from 'dotenv';

dotenv.config();

const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY || 'AIzaSyB3zxl-vXCx3_1Um3X2dJmw8-Rzj5NDsNY',
  authDomain: `${process.env.FIREBASE_PROJECT_ID || 'rbac-cybersecurity-9f6e3'}.firebaseapp.com`,
  projectId: process.env.FIREBASE_PROJECT_ID || 'rbac-cybersecurity-9f6e3',
  storageBucket: `${process.env.FIREBASE_PROJECT_ID || 'rbac-cybersecurity-9f6e3'}.appspot.com`,
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

export default db;
