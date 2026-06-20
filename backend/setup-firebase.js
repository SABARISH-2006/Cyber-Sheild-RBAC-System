#!/usr/bin/env node

/**
 * Firebase Configuration Setup
 * Helps you get the correct Firebase credentials
 */

const readline = require('readline');
const fs = require('fs');
const path = require('path');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const question = (prompt) => new Promise((resolve) => rl.question(prompt, resolve));

async function setup() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║           FIREBASE CONFIGURATION SETUP                          ║');
  console.log('║        (Data Storage & Sync to Firebase/Firestore)              ║');
  console.log('╚════════════════════════════════════════════════════════════════╝\n');

  console.log('To find your Firebase Project ID:\n');
  console.log('  1. Go to: https://console.firebase.google.com');
  console.log('  2. Select your project (cyber-shield-73e01 or similar)');
  console.log('  3. Click Project Settings (gear icon)');
  console.log('  4. Copy the "Project ID" value\n');

  const projectId = await question('Enter your Firebase Project ID: ');
  const apiKey = await question('Enter your Firebase API Key (or press Enter to skip): ');

  if (!projectId) {
    console.log('\n❌ Project ID is required!');
    rl.close();
    return;
  }

  // Update .env file
  const envPath = path.join(__dirname, '.env');
  let envContent = fs.readFileSync(envPath, 'utf8');

  // Replace Project ID
  envContent = envContent.replace(
    /FIREBASE_PROJECT_ID=.*/,
    `FIREBASE_PROJECT_ID=${projectId}`
  );

  // Replace API Key if provided
  if (apiKey) {
    envContent = envContent.replace(
      /FIREBASE_API_KEY=.*/,
      `FIREBASE_API_KEY=${apiKey}`
    );
  }

  fs.writeFileSync(envPath, envContent);

  console.log('\n✅ .env file updated!\n');
  console.log('Updated configuration:');
  console.log(`  FIREBASE_PROJECT_ID=${projectId}`);
  if (apiKey) console.log(`  FIREBASE_API_KEY=${apiKey.substring(0, 20)}...`);

  console.log('\n📝 Next steps:');
  console.log('  1. Stop the server (Press Ctrl+C)');
  console.log('  2. Run: npm run build');
  console.log('  3. Run: npm start');
  console.log('  4. Your data should now sync to Firebase!\n');

  rl.close();
}

setup();
