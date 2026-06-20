import React, { useState, useEffect } from 'react';
import { Line, Doughnut, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

// Register Chart.js elements
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface MockUser {
  id: number;
  loginId: string;
  username: string;
  email: string;
  roles: string[];
  status: 'active' | 'suspended' | 'inactive';
}

interface MockRole {
  id: number;
  name: string;
  permissions: string[];
  description: string;
}

interface BehaviorAlert {
  id: number;
  user: string;
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  status: 'open' | 'investigating' | 'resolved' | 'dismissed';
  triggered_at: string;
  resolved_by?: string;
}

interface AuditLog {
  id: number;
  timestamp: string;
  action: string;
  user: string;
  ip: string;
  status: 'SUCCESS' | 'FAILURE';
}

interface LoggedInUser {
  id: number;
  loginId: string;
  username: string;
  email: string;
  role: string;
  permissions: string[];
}

export default function App() {
  // Authentication states
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [loginStage, setLoginStage] = useState<'credentials' | 'otp'>('credentials');
  const [usernameInput, setUsernameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [otpInput, setOtpInput] = useState('');
  const [simulatedOtp, setSimulatedOtp] = useState('');
  const [loginError, setLoginError] = useState('');
  const [tempUserId, setTempUserId] = useState<number | null>(null);
  
  const [loggedInUser, setLoggedInUser] = useState<LoggedInUser | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'users' | 'roles' | 'alerts' | 'audits'>('dashboard');

  // State lists
  const [users, setUsers] = useState<MockUser[]>([
    { id: 1, loginId: 'ADM_101', username: 'superadmin', email: 'superadmin@cybersecurity.local', roles: ['SuperAdmin'], status: 'active' },
    { id: 2, loginId: 'EMP_101', username: 'secadmin', email: 'secadmin@cybersecurity.local', roles: ['SecurityAdmin'], status: 'active' },
    { id: 3, loginId: 'MAN_101', username: 'analyst01', email: 'analyst01@cybersecurity.local', roles: ['Analyst'], status: 'active' },
    { id: 4, loginId: 'AUD_101', username: 'auditor01', email: 'auditor01@cybersecurity.local', roles: ['Auditor'], status: 'active' },
    { id: 5, loginId: 'MAN_102', username: 'malicious_user', email: 'compromised@external.net', roles: ['Analyst'], status: 'suspended' },
  ]);

  const [roles, setRoles] = useState<MockRole[]>([
    { id: 1, name: 'SuperAdmin', description: 'Full unrestricted domain control.', permissions: ['user:create', 'user:read', 'user:update', 'user:delete', 'role:create', 'role:read', 'role:update', 'role:delete', 'role:assign', 'system:configure', 'logs:view', 'audit:read'] },
    { id: 2, name: 'SecurityAdmin', description: 'Manage users, assign roles, configure firewalls.', permissions: ['user:create', 'user:read', 'user:update', 'role:create', 'role:read', 'role:update', 'role:delete', 'role:assign', 'system:configure', 'logs:view'] },
    { id: 3, name: 'Analyst', description: 'Run network scans and inspect activity logs.', permissions: ['user:read', 'role:read', 'network:scan', 'logs:view'] },
    { id: 4, name: 'Auditor', description: 'Inspect audit trail and configurations.', permissions: ['user:read', 'role:read', 'audit:read', 'logs:view'] },
  ]);

  const [behaviorAlerts, setBehaviorAlerts] = useState<BehaviorAlert[]>([
    { id: 1, user: 'malicious_user', alert_type: 'IMPOSSIBLE_TRAVEL', severity: 'critical', description: 'Geographically impossible travel detected between consecutive sessions.', status: 'open', triggered_at: '10:15:22' },
    { id: 2, user: 'analyst01', alert_type: 'BRUTE_FORCE', severity: 'high', description: 'Repeated failed authentication attempts detected.', status: 'open', triggered_at: '10:20:45' },
    { id: 3, user: 'secadmin', alert_type: 'ANOMALOUS_ACCESS', severity: 'medium', description: 'Accessing resources outside typical business hours.', status: 'resolved', triggered_at: '09:05:12', resolved_by: 'superadmin' }
  ]);

  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([
    { id: 1, timestamp: new Date(Date.now() - 500000).toLocaleTimeString(), action: 'USER_LOGIN', user: 'superadmin', ip: '192.168.1.50', status: 'SUCCESS' },
    { id: 2, timestamp: new Date(Date.now() - 400000).toLocaleTimeString(), action: 'FIREWALL_UPDATE', user: 'secadmin', ip: '10.0.4.15', status: 'SUCCESS' },
    { id: 3, timestamp: new Date(Date.now() - 300000).toLocaleTimeString(), action: 'UNAUTHORIZED_ATTEMPT', user: 'analyst01', ip: '192.168.2.11', status: 'FAILURE' },
    { id: 4, timestamp: new Date(Date.now() - 200000).toLocaleTimeString(), action: 'PORT_SCAN_TRIGGERED', user: 'analyst01', ip: '192.168.2.11', status: 'SUCCESS' },
  ]);

  // Form states
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newUserRole, setNewUserRole] = useState('Analyst');

  const roleLoginPrefixes: { [key: string]: string } = {
    SuperAdmin: 'ADM',
    SecurityAdmin: 'EMP',
    Analyst: 'MAN',
    Auditor: 'AUD'
  };

  const generateUniqueRoleLoginId = (roleName: string) => {
    const prefix = roleLoginPrefixes[roleName] || 'USR';
    const existingIds = users
      .filter(u => u.roles[0] === roleName)
      .map(u => u.loginId)
      .filter(Boolean);

    const nextNumber = existingIds.reduce((max, id) => {
      const match = id.match(/_(\d+)$/);
      const numeric = match ? parseInt(match[1], 10) : 0;
      return Number.isFinite(numeric) ? Math.max(max, numeric) : max;
    }, 100);

    return `${prefix}_${String(nextNumber + 1).padStart(3, '0')}`;
  };

  // Trigger Mock Alert Form
  const [mockAlertType, setMockAlertType] = useState('BRUTE_FORCE');
  const [mockAlertUser, setMockAlertUser] = useState('analyst01');
  const [mockAlertSeverity, setMockAlertSeverity] = useState<'low' | 'medium' | 'high' | 'critical'>('high');

  // Helper function to dynamically generate unique User ID by role type
  const getFormattedUserId = (userId: number, roleName: string) => {
    const rolePrefixes: { [key: string]: string } = {
      'SuperAdmin': 'SAD',
      'SecurityAdmin': 'SEC',
      'Analyst': 'ANA',
      'Auditor': 'AUD'
    };
    const prefix = rolePrefixes[roleName] || 'USR';
    return `UID-${prefix}-${String(userId).padStart(3, '0')}`;
  };

  // Real-time security events simulation
  useEffect(() => {
    if (!isAuthenticated) return;
    const actions = ['USER_LOGIN', 'USER_CREATION', 'ROLE_CHANGE', 'UNAUTHORIZED_ATTEMPT', 'SESSION_REVOKED'];
    const mockUsers = ['secadmin', 'analyst01', 'auditor01', 'unknown_ip'];
    const ips = ['192.168.1.100', '10.0.5.210', '82.165.10.4', '192.168.1.120'];

    const interval = setInterval(() => {
      const randomAction = actions[Math.floor(Math.random() * actions.length)];
      const randomUser = mockUsers[Math.floor(Math.random() * mockUsers.length)];
      const randomIp = ips[Math.floor(Math.random() * ips.length)];
      const randomStatus = randomAction === 'UNAUTHORIZED_ATTEMPT' ? 'FAILURE' : 'SUCCESS';

      setAuditLogs(prev => [
        {
          id: prev.length + 1,
          timestamp: new Date().toLocaleTimeString(),
          action: randomAction,
          user: randomUser,
          ip: randomIp,
          status: randomStatus
        },
        ...prev.slice(0, 20)
      ]);
    }, 7000);

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Form handler: Credentials Login (Stage 1)
  const handleCredentialsSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');

    const userMatch = users.find(
      u => u.loginId.toLowerCase() === usernameInput.toLowerCase()
    );

    if (!userMatch || passwordInput !== 'P@ssw0rd123!') {
      setLoginError('Invalid username/email or password (hint: password is P@ssw0rd123!)');
      
      // Log failed login to mock audits
      setAuditLogs(prev => [
        {
          id: prev.length + 1,
          timestamp: new Date().toLocaleTimeString(),
          action: 'USER_LOGIN_ATTEMPT',
          user: usernameInput || 'anonymous',
          ip: '127.0.0.1',
          status: 'FAILURE'
        },
        ...prev
      ]);
      return;
    }

    if (userMatch.status !== 'active') {
      setLoginError(`Account is currently ${userMatch.status}. Login blocked.`);
      return;
    }

    // Generate random OTP
    const generatedOtp = String(Math.floor(100000 + Math.random() * 900000));
    setSimulatedOtp(generatedOtp);
    setTempUserId(userMatch.id);
    setLoginStage('otp');
  };

  // Form handler: OTP Verification (Stage 2)
  const handleOtpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');

    if (otpInput !== simulatedOtp) {
      setLoginError('Invalid verification code');
      return;
    }

    const matchedUser = users.find(u => u.id === tempUserId);
    if (!matchedUser) {
      setLoginError('Authentication expired. Please restart.');
      setLoginStage('credentials');
      return;
    }

    const userRoleName = matchedUser.roles[0];
    const roleConfig = roles.find(r => r.name === userRoleName);
    const userPermissions = roleConfig ? roleConfig.permissions : [];

    setLoggedInUser({
      id: matchedUser.id,
      loginId: matchedUser.loginId,
      username: matchedUser.username,
      email: matchedUser.email,
      role: userRoleName,
      permissions: userPermissions
    });

    setIsAuthenticated(true);
    setUsernameInput('');
    setPasswordInput('');
    setOtpInput('');
    
    // Log successful auth
    setAuditLogs(prev => [
      {
        id: prev.length + 1,
        timestamp: new Date().toLocaleTimeString(),
        action: 'USER_LOGIN',
        user: matchedUser.username,
        ip: '127.0.0.1',
        status: 'SUCCESS'
      },
      ...prev
    ]);
  };

  // Logout
  const handleLogout = () => {
    if (loggedInUser) {
      setAuditLogs(prev => [
        {
          id: prev.length + 1,
          timestamp: new Date().toLocaleTimeString(),
          action: 'USER_LOGOUT',
          user: loggedInUser.username,
          ip: '127.0.0.1',
          status: 'SUCCESS'
        },
        ...prev
      ]);
    }
    setLoggedInUser(null);
    setIsAuthenticated(false);
    setLoginStage('credentials');
  };

  // Form handler: Create user
  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!loggedInUser || !loggedInUser.permissions.includes('user:create')) return;
    if (!newUsername || !newEmail) return;

    const newUser: MockUser = {
      id: users.length + 1,
      loginId: generateUniqueRoleLoginId(newUserRole),
      username: newUsername,
      email: newEmail,
      roles: [newUserRole],
      status: 'active'
    };

    setUsers([...users, newUser]);
    
    // Add audit entry
    setAuditLogs(prev => [
      {
        id: prev.length + 1,
        timestamp: new Date().toLocaleTimeString(),
        action: 'USER_CREATION',
        user: loggedInUser.username,
        ip: '127.0.0.1',
        status: 'SUCCESS'
      },
      ...prev
    ]);

    setNewUsername('');
    setNewEmail('');
  };

  const handleToggleStatus = (id: number) => {
    if (!loggedInUser || !loggedInUser.permissions.includes('user:update')) return;
    setUsers(users.map(u => {
      if (u.id === id) {
        const nextStatus = u.status === 'active' ? 'suspended' : 'active';
        setAuditLogs(prev => [
          {
            id: prev.length + 1,
            timestamp: new Date().toLocaleTimeString(),
            action: nextStatus === 'suspended' ? 'USER_SUSPENSION' : 'USER_ACTIVATION',
            user: loggedInUser.username,
            ip: '127.0.0.1',
            status: 'SUCCESS'
          },
          ...prev
        ]);
        return { ...u, status: nextStatus };
      }
      return u;
    }));
  };

  // Trigger Behavior Alert
  const handleTriggerAlert = (e: React.FormEvent) => {
    e.preventDefault();
    if (!loggedInUser || !loggedInUser.permissions.includes('system:configure')) return;
    const newAlert: BehaviorAlert = {
      id: behaviorAlerts.length + 1,
      user: mockAlertUser,
      alert_type: mockAlertType,
      severity: mockAlertSeverity,
      description: `Automated testing indicator triggered for anomaly check type: ${mockAlertType}.`,
      status: 'open',
      triggered_at: new Date().toLocaleTimeString()
    };
    
    setBehaviorAlerts([newAlert, ...behaviorAlerts]);

    setAuditLogs(prev => [
      {
        id: prev.length + 1,
        timestamp: new Date().toLocaleTimeString(),
        action: 'BEHAVIOR_ALERT_TRIGGERED',
        user: mockAlertUser,
        ip: '127.0.0.1',
        status: 'FAILURE'
      },
      ...prev
    ]);
  };

  // Resolve Behavior Alert
  const handleResolveAlert = (id: number) => {
    if (!loggedInUser || !loggedInUser.permissions.includes('system:configure')) return;
    setBehaviorAlerts(behaviorAlerts.map(a => {
      if (a.id === id) {
        setAuditLogs(prev => [
          {
            id: prev.length + 1,
            timestamp: new Date().toLocaleTimeString(),
            action: 'BEHAVIOR_ALERT_RESOLVED',
            user: loggedInUser.username,
            ip: '127.0.0.1',
            status: 'SUCCESS'
          },
          ...prev
        ]);
        return { ...a, status: 'resolved', resolved_by: loggedInUser.username };
      }
      return a;
    }));
  };

  // Chart Data Calculations
  const roleDistributionCounts = roles.map(role => {
    return users.filter(u => u.roles.includes(role.name)).length;
  });

  const doughnutData = {
    labels: roles.map(r => r.name),
    datasets: [
      {
        label: 'Users per Role',
        data: roleDistributionCounts,
        backgroundColor: [
          '#4facfe', // SuperAdmin (Blue)
          '#00f2fe', // SecurityAdmin (Cyan)
          '#00db8b', // Analyst (Green)
          '#f39c12'  // Auditor (Orange)
        ],
        borderWidth: 1,
        borderColor: '#1f2d47'
      }
    ]
  };

  const lineData = {
    labels: ['04:00', '05:00', '06:00', '07:00', '08:00', '09:00', '10:00', 'Current'],
    datasets: [
      {
        label: 'System Logins',
        data: [4, 7, 10, 5, 12, 9, 18, auditLogs.filter(l => l.action === 'USER_LOGIN').length + 5],
        borderColor: '#4facfe',
        backgroundColor: 'rgba(79, 172, 254, 0.1)',
        fill: true,
        tension: 0.4
      },
      {
        label: 'Threat Anomalies',
        data: [1, 0, 2, 0, 1, 3, 2, behaviorAlerts.filter(a => a.status === 'open').length],
        borderColor: '#ff3860',
        backgroundColor: 'rgba(255, 56, 96, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  };

  const severityCounts = {
    low: behaviorAlerts.filter(a => a.severity === 'low').length,
    medium: behaviorAlerts.filter(a => a.severity === 'medium').length,
    high: behaviorAlerts.filter(a => a.severity === 'high').length,
    critical: behaviorAlerts.filter(a => a.severity === 'critical').length
  };

  const barData = {
    labels: ['Low', 'Medium', 'High', 'Critical'],
    datasets: [
      {
        label: 'Active Alerts',
        data: [severityCounts.low, severityCounts.medium, severityCounts.high, severityCounts.critical],
        backgroundColor: [
          '#64748b', // Low (Slate)
          '#4facfe', // Medium (Blue)
          '#f39c12', // High (Orange)
          '#ff3860'  // Critical (Red)
        ],
        borderWidth: 1,
        borderColor: '#1f2d47'
      }
    ]
  };

  const averageRiskScore = (() => {
    let base = 15.0;
    const openAlerts = behaviorAlerts.filter(a => a.status === 'open');
    openAlerts.forEach(a => {
      if (a.severity === 'critical') base += 25.0;
      else if (a.severity === 'high') base += 15.0;
      else if (a.severity === 'medium') base += 8.0;
      else base += 3.0;
    });
    return Math.min(base, 100.0).toFixed(1);
  })();

  // Render Login view
  if (!isAuthenticated) {
    return (
      <div className="container-fluid bg-dark text-light min-vh-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: '#0a0e17' }}>
        <div className="card bg-secondary bg-opacity-25 border border-secondary p-4 rounded-3 shadow-lg" style={{ width: '450px', backdropFilter: 'blur(8px)' }}>
          <div className="text-center mb-4">
            <h2 className="text-white fw-bold h3">
              <span style={{ color: '#00f2fe' }}>🛡️ Cyber-Shield</span>
            </h2>
            <p className="text-secondary small">RBAC Cybersecurity Gateway</p>
          </div>

          {loginError && (
            <div className="alert alert-danger p-2 small text-center" role="alert">
              ❌ {loginError}
            </div>
          )}

          {loginStage === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} className="d-flex flex-column gap-3">
              <div>
                <label className="form-label text-secondary small">Login ID</label>
                <input 
                  type="text" 
                  value={usernameInput} 
                  onChange={(e) => setUsernameInput(e.target.value)} 
                  className="form-control bg-dark text-white border-secondary"
                  placeholder="e.g. ADM_101"
                  required 
                />
              </div>

              <div>
                <label className="form-label text-secondary small">Security Password</label>
                <input 
                  type="password" 
                  value={passwordInput} 
                  onChange={(e) => setPasswordInput(e.target.value)} 
                  className="form-control bg-dark text-white border-secondary"
                  placeholder="••••••••••••"
                  required 
                />
              </div>

              <button type="submit" className="btn btn-info w-100 fw-bold mt-2">
                Initiate Secure Session
              </button>

              <div className="card bg-dark border-secondary p-2 mt-2 small text-secondary">
                <div className="fw-bold text-info small mb-1">Testing Credentials (Password: P@ssw0rd123!)</div>
                <div style={{ fontSize: '0.75rem' }}>
                  • <strong>superadmin</strong> (SuperAdmin Role)<br />
                  • <strong>secadmin</strong> (SecurityAdmin Role)<br />
                  • <strong>analyst01</strong> (Analyst Role)<br />
                  • <strong>auditor01</strong> (Auditor Role)
                </div>
              </div>
            </form>
          ) : (
            <form onSubmit={handleOtpSubmit} className="d-flex flex-column gap-3">
              <div className="text-center py-2">
                <div className="text-warning small mb-2">🛡️ Multi-Factor Authentication Required</div>
                <p className="text-secondary small">A one-time verification code has been issued.</p>
              </div>

              {/* Secure SMS Simulation Banner */}
              <div className="alert alert-success p-2 px-3 small text-center" style={{ backgroundColor: 'rgba(0,219,139,0.1)', borderColor: 'rgba(0,219,139,0.3)', color: '#00db8b' }}>
                📟 [2FA Simulator] SMS delivery code: <strong>{simulatedOtp}</strong>
              </div>

              <div>
                <label className="form-label text-secondary small">One-Time Password (6-Digit OTP)</label>
                <input 
                  type="text" 
                  maxLength={6}
                  value={otpInput} 
                  onChange={(e) => setOtpInput(e.target.value)} 
                  className="form-control bg-dark text-white border-secondary text-center fw-bold h4 mb-0"
                  placeholder="000 000"
                  required 
                />
              </div>

              <div className="d-flex gap-2 mt-2">
                <button type="button" className="btn btn-outline-secondary w-50" onClick={() => setLoginStage('credentials')}>
                  Back
                </button>
                <button type="submit" className="btn btn-info w-50 fw-bold">
                  Verify Identity
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    );
  }

  // Check custom permission filters
  const hasPermission = (permissionName: string) => {
    return loggedInUser ? loggedInUser.permissions.includes(permissionName) : false;
  };

  return (
    <div className="container-fluid bg-dark text-light min-vh-100 p-4" style={{ backgroundColor: '#0a0e17' }}>
      
      {/* Header bar */}
      <header className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom border-secondary">
        <div>
          <h1 className="h2 text-white fw-bold mb-1">
            <span style={{ color: '#00f2fe' }}>🛡️ Cyber-Shield</span> RBAC Security Control
          </h1>
          <p className="text-secondary small mb-0">High-fidelity identity verification, session authorization, and threat intelligence dashboard.</p>
        </div>
        
        {/* Logged in User Profile Info */}
        {loggedInUser && (
          <div className="d-flex align-items-center gap-3 bg-secondary bg-opacity-25 border border-secondary p-2 px-3 rounded shadow-sm">
            <div className="text-end">
              <div className="text-muted text-uppercase fw-bold" style={{ fontSize: '0.65rem', letterSpacing: '0.05em' }}>
                Operator: <span className="text-info">{loggedInUser.username}</span>
              </div>
              <div className="fw-semibold text-warning small">
                {loggedInUser.role} ({getFormattedUserId(loggedInUser.id, loggedInUser.role)})
              </div>
            </div>
            <button 
              onClick={handleLogout} 
              className="btn btn-sm btn-outline-danger p-1 px-2 text-danger border-danger border-opacity-50"
              style={{ fontSize: '0.8rem' }}
            >
              Revoke Session
            </button>
          </div>
        )}
      </header>

      {/* Grid structure: Sidebar nav + Content */}
      <div className="row g-4">
        
        {/* Sidebar Nav */}
        <nav className="col-12 col-md-3 col-lg-2 d-flex flex-column gap-2">
          <div className="text-muted text-uppercase fw-bold ps-2 mb-2" style={{ fontSize: '0.7rem', letterSpacing: '0.08em' }}>Navigation</div>
          
          <button 
            onClick={() => setActiveTab('dashboard')}
            className={`btn text-start p-3 w-100 rounded-3 border ${activeTab === 'dashboard' ? 'btn-info text-dark border-info fw-bold' : 'btn-outline-secondary text-white border-secondary'}`}
            style={{ transition: 'all 0.25s' }}
          >
            📊 Security Analytics
          </button>
          
          {hasPermission('user:read') && (
            <button 
              onClick={() => setActiveTab('users')}
              className={`btn text-start p-3 w-100 rounded-3 border ${activeTab === 'users' ? 'btn-info text-dark border-info fw-bold' : 'btn-outline-secondary text-white border-secondary'}`}
              style={{ transition: 'all 0.25s' }}
            >
              👥 User Registry
            </button>
          )}
          
          {hasPermission('role:read') && (
            <button 
              onClick={() => setActiveTab('roles')}
              className={`btn text-start p-3 w-100 rounded-3 border ${activeTab === 'roles' ? 'btn-info text-dark border-info fw-bold' : 'btn-outline-secondary text-white border-secondary'}`}
              style={{ transition: 'all 0.25s' }}
            >
              🛡️ Role Privilege Maps
            </button>
          )}
          
          {(hasPermission('logs:view') || hasPermission('system:configure')) && (
            <button 
              onClick={() => setActiveTab('alerts')}
              className={`btn text-start p-3 w-100 rounded-3 border ${activeTab === 'alerts' ? 'btn-info text-dark border-info fw-bold' : 'btn-outline-secondary text-white border-secondary'}`}
              style={{ transition: 'all 0.25s' }}
            >
              🚨 Behavior Threat Alerts
              {behaviorAlerts.filter(a => a.status === 'open').length > 0 && (
                <span className="badge bg-danger ms-2">{behaviorAlerts.filter(a => a.status === 'open').length}</span>
              )}
            </button>
          )}

          {hasPermission('audit:read') && (
            <button 
              onClick={() => setActiveTab('audits')}
              className={`btn text-start p-3 w-100 rounded-3 border ${activeTab === 'audits' ? 'btn-info text-dark border-info fw-bold' : 'btn-outline-secondary text-white border-secondary'}`}
              style={{ transition: 'all 0.25s' }}
            >
              📑 Global Audit Trails
            </button>
          )}

          {loggedInUser && (
            <div className="card bg-secondary bg-opacity-10 border border-secondary mt-3 p-3 text-secondary" style={{ fontSize: '0.8rem' }}>
              <h6 className="text-info fw-bold mb-2 small">Profile Privileges</h6>
              <div className="d-flex flex-wrap gap-1 mt-1">
                {loggedInUser.permissions.slice(0, 5).map(p => (
                  <span key={p} className="badge bg-secondary bg-opacity-25 text-muted p-1" style={{ fontSize: '0.65rem' }}>{p}</span>
                ))}
                {loggedInUser.permissions.length > 5 && (
                  <span className="badge bg-secondary bg-opacity-25 text-muted p-1" style={{ fontSize: '0.65rem' }}>+{loggedInUser.permissions.length - 5} more</span>
                )}
              </div>
            </div>
          )}
        </nav>

        {/* Central Display */}
        <main className="col-12 col-md-9 col-lg-10">
          
          {/* DASHBOARD ANALYTICS VIEW */}
          {activeTab === 'dashboard' && (
            <div>
              {/* Metrics cards row */}
              <div className="row g-3 mb-4">
                <div className="col-12 col-sm-6 col-xl-3">
                  <div className="card bg-secondary bg-opacity-25 border border-secondary p-3 h-100 rounded-3">
                    <div className="text-secondary small text-uppercase">Active Users</div>
                    <div className="d-flex align-items-baseline gap-2 mt-1">
                      <span className="h2 fw-bold text-white mb-0">{users.filter(u => u.status === 'active').length}</span>
                      <span className="text-muted small">/ {users.length} registered</span>
                    </div>
                  </div>
                </div>
                
                <div className="col-12 col-sm-6 col-xl-3">
                  <div className="card bg-secondary bg-opacity-25 border border-secondary p-3 h-100 rounded-3">
                    <div className="text-secondary small text-uppercase">Critical & High Threats</div>
                    <div className="d-flex align-items-baseline gap-2 mt-1">
                      <span className={`h2 fw-bold mb-0 ${behaviorAlerts.filter(a => a.status === 'open' && (a.severity === 'critical' || a.severity === 'high')).length > 0 ? 'text-danger' : 'text-success'}`}>
                        {behaviorAlerts.filter(a => a.status === 'open' && (a.severity === 'critical' || a.severity === 'high')).length}
                      </span>
                      <span className="text-muted small">Active Alarms</span>
                    </div>
                  </div>
                </div>

                <div className="col-12 col-sm-6 col-xl-3">
                  <div className="card bg-secondary bg-opacity-25 border border-secondary p-3 h-100 rounded-3">
                    <div className="text-secondary small text-uppercase">Computed Threat Index</div>
                    <div className="d-flex align-items-baseline gap-2 mt-1">
                      <span className={`h2 fw-bold mb-0 ${Number(averageRiskScore) > 50 ? 'text-danger' : Number(averageRiskScore) > 25 ? 'text-warning' : 'text-success'}`}>
                        {averageRiskScore}%
                      </span>
                      <span className="text-muted small">Risk Level</span>
                    </div>
                  </div>
                </div>

                <div className="col-12 col-sm-6 col-xl-3">
                  <div className="card bg-secondary bg-opacity-25 border border-secondary p-3 h-100 rounded-3">
                    <div className="text-secondary small text-uppercase">Audit Trail Count</div>
                    <div className="d-flex align-items-baseline gap-2 mt-1">
                      <span className="h2 fw-bold text-white mb-0">{auditLogs.length}</span>
                      <span className="text-muted small">compliance logs</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chart Grid Section */}
              <div className="row g-4 mb-4">
                {/* Line chart: Telemetry */}
                <div className="col-12 col-xl-8">
                  <div className="card bg-secondary bg-opacity-10 border border-secondary p-3 rounded-3">
                    <h5 className="card-title text-white fw-bold mb-3 small text-uppercase" style={{ letterSpacing: '0.05em' }}>System Telemetry Trends (Last 8 Hours)</h5>
                    <div style={{ height: '300px' }}>
                      <Line data={lineData} options={{ responsive: true, maintainAspectRatio: false, scales: { y: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2d47' } }, x: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2d47' } } }, plugins: { legend: { labels: { color: '#f8fafc' } } } }} />
                    </div>
                  </div>
                </div>

                {/* Doughnut: Roles */}
                <div className="col-12 col-md-6 col-xl-4">
                  <div className="card bg-secondary bg-opacity-10 border border-secondary p-3 rounded-3 h-100">
                    <h5 className="card-title text-white fw-bold mb-3 small text-uppercase" style={{ letterSpacing: '0.05em' }}>User Role Distribution</h5>
                    <div className="d-flex align-items-center justify-content-center" style={{ height: '240px' }}>
                      <Doughnut data={doughnutData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#f8fafc' }, position: 'bottom' } } }} />
                    </div>
                  </div>
                </div>

                {/* Bar chart: Severity */}
                <div className="col-12 col-md-6 col-xl-4">
                  <div className="card bg-secondary bg-opacity-10 border border-secondary p-3 rounded-3 h-100">
                    <h5 className="card-title text-white fw-bold mb-3 small text-uppercase" style={{ letterSpacing: '0.05em' }}>Threat Severity Distribution</h5>
                    <div style={{ height: '220px' }}>
                      <Bar data={barData} options={{ responsive: true, maintainAspectRatio: false, scales: { y: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2d47' } }, x: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2d47' } } }, plugins: { legend: { display: false } } }} />
                    </div>
                  </div>
                </div>

                {/* Recent Alerts Feed */}
                <div className="col-12 col-xl-8">
                  <div className="card bg-secondary bg-opacity-10 border border-secondary p-3 rounded-3 h-100">
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="card-title text-white fw-bold mb-0 small text-uppercase" style={{ letterSpacing: '0.05em' }}>Active Critical Alerts Stream</h5>
                      {(hasPermission('logs:view') || hasPermission('system:configure')) && (
                        <button className="btn btn-sm btn-outline-info" onClick={() => setActiveTab('alerts')}>Manage Alerts</button>
                      )}
                    </div>
                    <div className="list-group list-group-flush" style={{ fontSize: '0.9rem' }}>
                      {behaviorAlerts.slice(0, 3).map(alert => (
                        <div key={alert.id} className="list-group-item bg-transparent text-light border-secondary d-flex justify-content-between align-items-start p-3 px-0">
                          <div>
                            <div className="d-flex align-items-center gap-2 mb-1">
                              <span className={`badge ${alert.severity === 'critical' ? 'bg-danger' : alert.severity === 'high' ? 'bg-warning text-dark' : alert.severity === 'medium' ? 'bg-info text-dark' : 'bg-secondary'}`}>
                                {alert.severity.toUpperCase()}
                              </span>
                              <strong className="text-white">{alert.alert_type}</strong>
                              <span className="text-muted small">@{alert.triggered_at}</span>
                            </div>
                            <div className="text-secondary small">{alert.description}</div>
                          </div>
                          <div>
                            {alert.status === 'open' ? (
                              <button 
                                className="btn btn-sm btn-outline-success p-1 px-2 text-success" 
                                onClick={() => handleResolveAlert(alert.id)}
                                disabled={!hasPermission('system:configure')}
                              >
                                Resolve
                              </button>
                            ) : (
                              <span className="badge bg-secondary text-light">RESOLVED</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* USER REGISTRY VIEW */}
          {activeTab === 'users' && hasPermission('user:read') && (
            <div className="card bg-secondary bg-opacity-10 border border-secondary p-4 rounded-3">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h3 className="h4 text-white fw-bold mb-0">System User Accounts</h3>
                <span className="text-success small">● DB Engine Sync Simulator</span>
              </div>

              {/* Add User Form */}
              {hasPermission('user:create') ? (
                <form onSubmit={handleCreateUser} className="row g-3 mb-4 p-3 bg-secondary bg-opacity-10 border border-secondary rounded shadow-sm">
                  <div className="col-12 col-md-4">
                    <label className="form-label text-secondary small">Username</label>
                    <input 
                      type="text" 
                      placeholder="e.g. sec_engineer" 
                      value={newUsername} 
                      onChange={(e) => setNewUsername(e.target.value)} 
                      className="form-control bg-dark text-white border-secondary"
                      required 
                    />
                  </div>
                  <div className="col-12 col-md-4">
                    <label className="form-label text-secondary small">Security Email</label>
                    <input 
                      type="email" 
                      placeholder="email@cybersecurity.local" 
                      value={newEmail} 
                      onChange={(e) => setNewEmail(e.target.value)} 
                      className="form-control bg-dark text-white border-secondary"
                      required 
                    />
                  </div>
                  <div className="col-12 col-md-2">
                    <label className="form-label text-secondary small">Assigned Role</label>
                    <select 
                      value={newUserRole} 
                      onChange={(e) => setNewUserRole(e.target.value)}
                      className="form-select bg-dark text-white border-secondary"
                    >
                      {roles.map(r => <option key={r.id} value={r.name}>{r.name}</option>)}
                    </select>
                  </div>
                  <div className="col-12 col-md-2 d-flex align-items-end">
                    <button type="submit" className="btn btn-info w-100 fw-bold">Deploy User</button>
                  </div>
                </form>
              ) : (
                <div className="alert alert-secondary p-2 mb-4 small border-secondary bg-dark text-secondary">
                  🔒 Your account doesn't have privileges to deploy new users (requires <code>user:create</code>).
                </div>
              )}

              {/* Users Table */}
              <div className="table-responsive">
                <table className="table table-dark table-striped table-hover align-middle border-secondary">
                  <thead>
                    <tr className="border-secondary text-secondary" style={{ fontSize: '0.85rem' }}>
                      <th>Unique User ID</th>
                      <th>Username</th>
                      <th>Credentials Email</th>
                      <th>Security Role</th>
                      <th>Status</th>
                      {hasPermission('user:update') && <th className="text-end">Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id} className="border-secondary">
                        <td className="text-info fw-semibold font-monospace">
                          {u.loginId}
                        </td>
                        <td className="fw-semibold">{u.username}</td>
                        <td className="text-secondary">{u.email}</td>
                        <td>
                          <span className="badge bg-info bg-opacity-10 text-info border border-info border-opacity-25 p-2 small">
                            {u.roles.join(', ')}
                          </span>
                        </td>
                        <td>
                          <span className={`badge p-2 ${u.status === 'active' ? 'bg-success' : 'bg-danger'}`}>
                            {u.status.toUpperCase()}
                          </span>
                        </td>
                        {hasPermission('user:update') && (
                          <td className="text-end">
                            <button 
                              onClick={() => handleToggleStatus(u.id)}
                              className={`btn btn-sm ${u.status === 'active' ? 'btn-outline-danger' : 'btn-outline-success'}`}
                            >
                              {u.status === 'active' ? 'Suspend' : 'Activate'}
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ROLE PRIVILEGE MAPS VIEW */}
          {activeTab === 'roles' && hasPermission('role:read') && (
            <div className="card bg-secondary bg-opacity-10 border border-secondary p-4 rounded-3">
              <h3 className="h4 text-white fw-bold mb-4">RBAC Privilege Assignment Matrix</h3>
              <div className="row g-4">
                {roles.map(r => (
                  <div key={r.id} className="col-12 col-lg-6">
                    <div className="card bg-dark bg-opacity-50 border border-secondary p-3 rounded-3 h-100 shadow-sm">
                      <div className="d-flex justify-content-between align-items-center mb-2">
                        <h4 className="text-info fw-bold mb-0 h5">{r.name}</h4>
                        <span className="text-muted small">0{r.id}</span>
                      </div>
                      <p className="text-secondary small mb-3">{r.description}</p>
                      
                      <div className="d-flex flex-wrap gap-2">
                        {r.permissions.map(p => (
                          <span key={p} className="badge bg-secondary bg-opacity-25 border border-secondary text-secondary p-2" style={{ fontSize: '0.7rem' }}>
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* BEHAVIOR THREAT ALERTS VIEW */}
          {activeTab === 'alerts' && (hasPermission('logs:view') || hasPermission('system:configure')) && (
            <div className="card bg-secondary bg-opacity-10 border border-secondary p-4 rounded-3">
              <h3 className="h4 text-white fw-bold mb-4">Behavioral Anomaly & Threat Intel</h3>

              {/* Trigger Mock Anomaly Form */}
              {hasPermission('system:configure') ? (
                <form onSubmit={handleTriggerAlert} className="row g-3 mb-4 p-3 bg-secondary bg-opacity-10 border border-secondary rounded shadow-sm">
                  <div className="col-12 col-md-3">
                    <label className="form-label text-secondary small">Anomaly Type</label>
                    <select 
                      value={mockAlertType} 
                      onChange={(e) => setMockAlertType(e.target.value)}
                      className="form-select bg-dark text-white border-secondary"
                    >
                      <option value="IMPOSSIBLE_TRAVEL">IMPOSSIBLE_TRAVEL</option>
                      <option value="BRUTE_FORCE">BRUTE_FORCE</option>
                      <option value="ANOMALOUS_ACCESS">ANOMALOUS_ACCESS</option>
                      <option value="UNUSUAL_API_VOLUME">UNUSUAL_API_VOLUME</option>
                    </select>
                  </div>
                  <div className="col-12 col-md-3">
                    <label className="form-label text-secondary small">Target User</label>
                    <select 
                      value={mockAlertUser} 
                      onChange={(e) => setMockAlertUser(e.target.value)}
                      className="form-select bg-dark text-white border-secondary"
                    >
                      {users.map(u => <option key={u.id} value={u.username}>{u.username}</option>)}
                    </select>
                  </div>
                  <div className="col-12 col-md-3">
                    <label className="form-label text-secondary small">Severity level</label>
                    <select 
                      value={mockAlertSeverity} 
                      onChange={(e) => setMockAlertSeverity(e.target.value as any)}
                      className="form-select bg-dark text-white border-secondary"
                    >
                      <option value="low">Low Severity</option>
                      <option value="medium">Medium Severity</option>
                      <option value="high">High Severity</option>
                      <option value="critical">Critical Severity</option>
                    </select>
                  </div>
                  <div className="col-12 col-md-3 d-flex align-items-end">
                    <button type="submit" className="btn btn-danger w-100 fw-bold">Trigger Threat Alert</button>
                  </div>
                </form>
              ) : (
                <div className="alert alert-secondary p-2 mb-4 small border-secondary bg-dark text-secondary">
                  🔒 Your account doesn't have privileges to configure system or trigger threat indicators (requires <code>system:configure</code>).
                </div>
              )}

              {/* Alerts Table */}
              <div className="table-responsive">
                <table className="table table-dark table-striped table-hover align-middle border-secondary">
                  <thead>
                    <tr className="border-secondary text-secondary" style={{ fontSize: '0.85rem' }}>
                      <th>ID</th>
                      <th>Time</th>
                      <th>User</th>
                      <th>Type</th>
                      <th>Severity</th>
                      <th>Summary</th>
                      <th>Status</th>
                      <th className="text-end">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {behaviorAlerts.map(a => (
                      <tr key={a.id} className="border-secondary">
                        <td className="text-muted">0{a.id}</td>
                        <td className="small text-secondary">{a.triggered_at}</td>
                        <td className="fw-semibold text-info">{a.user}</td>
                        <td><code className="text-warning fw-bold">{a.alert_type}</code></td>
                        <td>
                          <span className={`badge p-2 ${a.severity === 'critical' ? 'bg-danger' : a.severity === 'high' ? 'bg-warning text-dark' : a.severity === 'medium' ? 'bg-info text-dark' : 'bg-secondary'}`}>
                            {a.severity.toUpperCase()}
                          </span>
                        </td>
                        <td className="small text-secondary" style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {a.description}
                        </td>
                        <td>
                          <span className={`badge p-2 ${a.status === 'open' ? 'bg-danger bg-opacity-25 text-danger border border-danger border-opacity-20' : 'bg-success'}`}>
                            {a.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="text-end">
                          {a.status === 'open' ? (
                            <button 
                              onClick={() => handleResolveAlert(a.id)}
                              className="btn btn-sm btn-outline-success"
                              disabled={!hasPermission('system:configure')}
                            >
                              Resolve
                            </button>
                          ) : (
                            <span className="small text-secondary">By: {a.resolved_by}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* GLOBAL AUDIT TRAILS VIEW */}
          {activeTab === 'audits' && hasPermission('audit:read') && (
            <div className="card bg-secondary bg-opacity-10 border border-secondary p-4 rounded-3">
              <h3 className="h4 text-white fw-bold mb-4">Cryptographic Compliance Audit Logs</h3>
              <div className="d-flex flex-column gap-2" style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                {auditLogs.map(log => (
                  <div key={log.id} className="p-3 bg-dark bg-opacity-70 border-start border-3 border-secondary rounded shadow-sm d-flex justify-content-between align-items-center" style={{ borderLeftColor: log.status === 'SUCCESS' ? '#00db8b' : '#ff3860' }}>
                    <div className="d-flex flex-wrap gap-3 align-items-center">
                      <span className="text-muted">[{log.timestamp}]</span>
                      <span className="text-info fw-bold">{log.action}</span>
                      <span className="text-secondary">operator: {log.user}</span>
                      <span className="text-muted">src_ip: {log.ip}</span>
                    </div>
                    <div>
                      <span className={`fw-bold small ${log.status === 'SUCCESS' ? 'text-success' : 'text-danger'}`}>
                        {log.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
