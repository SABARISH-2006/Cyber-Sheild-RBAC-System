import dotenv from 'dotenv';
dotenv.config();

import bcrypt from 'bcrypt';
import { collection, query, getDocs, deleteDoc, doc, setDoc, where } from 'firebase/firestore';
import db from './config/db.js';
import logger from './config/logger.js';

const setupDefaultAdmin = async () => {
  try {
    console.log('🔧 Setting up default admin...\n');

    // 1. Hash the new admin password
    const newPassword = 'Kcs@1234';
    const hashedPassword = await bcrypt.hash(newPassword, 12);
    console.log('✓ Password hashed');

    // 2. Get all existing users
    console.log('\n📋 Fetching existing admins...');
    const usersRef = collection(db, 'users');
    const querySnapshot = await getDocs(usersRef);

    const usersToDelete: { id: string; username: string }[] = [];
    let defaultAdminExists = false;

    querySnapshot.forEach((doc) => {
      const userData = doc.data();
      console.log(`  - Found user: ${userData.username} (${doc.id})`);
      
      // Check if this is our new default admin
      if (userData.username === 'SABARISH K C') {
        defaultAdminExists = true;
        console.log('    └─ This is the new default admin');
      } else {
        // Mark for deletion if it's an admin
        usersToDelete.push({ id: doc.id, username: userData.username });
      }
    });

    // 3. Delete existing admin users
    if (usersToDelete.length > 0) {
      console.log(`\n🗑️  Deleting ${usersToDelete.length} existing admin(s)...`);
      for (const user of usersToDelete) {
        await deleteDoc(doc(db, 'users', user.id));
        console.log(`  ✓ Deleted: ${user.username}`);
      }
    } else {
      console.log('\n✓ No existing admins to delete');
    }

    // 4. Create/Update default admin user
    console.log('\n➕ Setting up default admin: SABARISH K C');
    
    if (defaultAdminExists) {
      console.log('  ℹ️  Admin already exists, updating password...');
    }

    const adminDocId = 'admin_sabarish_kc';
    const adminData = {
      username: 'SABARISH K C',
      email: 'sabarish.kc@cybersecurity.local',
      password_hash: hashedPassword,
      status: 'active',
      roles: ['SuperAdmin'],
      created_at: new Date(),
      updated_at: new Date(),
      is_default_admin: true
    };

    await setDoc(doc(db, 'users', adminDocId), adminData);
    console.log('  ✓ Default admin created successfully');

    console.log('\n' + '='.repeat(60));
    console.log('✅ DEFAULT ADMIN SETUP COMPLETED');
    console.log('='.repeat(60));
    console.log('\n📝 DEFAULT ADMIN CREDENTIALS:');
    console.log(`   Username: SABARISH K C`);
    console.log(`   Password: Kcs@1234`);
    console.log(`   Email:    sabarish.kc@cybersecurity.local`);
    console.log(`   Role:     SuperAdmin`);
    console.log(`   Status:   Active`);
    console.log('\n✓ All other admins have been deleted');
    console.log('='.repeat(60) + '\n');

  } catch (error) {
    console.error('❌ Error during setup:', error);
    process.exit(1);
  }
};

setupDefaultAdmin();
