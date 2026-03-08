import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useSearchParams, Link, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Toaster, toast } from 'sonner';
import { 
  Users, Clock, Shield, Briefcase, LogOut, Menu, X, ChevronRight, 
  CheckCircle, XCircle, AlertCircle, Crown, Server, Gamepad2,
  FileText, User, Settings, Home as HomeIcon
} from 'lucide-react';
import "@/App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ==================== AUTH CONTEXT ====================
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('auth_token'));

  const fetchUser = useCallback(async (authToken) => {
    if (!authToken) {
      setLoading(false);
      return;
    }
    try {
      const response = await axios.get(`${API}/auth/me?authorization=${authToken}`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      localStorage.removeItem('auth_token');
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser(token);
  }, [token, fetchUser]);

  const login = () => {
    window.location.href = `${API}/auth/login`;
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
    toast.success('Logged out successfully');
  };

  const setAuthToken = (newToken) => {
    localStorage.setItem('auth_token', newToken);
    setToken(newToken);
    fetchUser(newToken);
  };

  return (
    <AuthContext.Provider value={{ user, loading, token, login, logout, setAuthToken }}>
      {children}
    </AuthContext.Provider>
  );
};

// ==================== AUTH CALLBACK ====================
const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setAuthToken } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      setAuthToken(token);
      toast.success('Successfully logged in!');
      navigate('/dashboard');
    } else {
      toast.error('Authentication failed');
      navigate('/');
    }
  }, [searchParams, setAuthToken, navigate]);

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-[#39FF14] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-white font-mono uppercase tracking-wider">Authenticating...</p>
      </div>
    </div>
  );
};

// ==================== LAYOUT ====================
const Layout = ({ children }) => {
  const { user, logout, login } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Home', icon: HomeIcon },
    { path: '/queue', label: 'Queue', icon: Users },
    { path: '/apply', label: 'Apply', icon: FileText },
    ...(user ? [{ path: '/dashboard', label: 'Dashboard', icon: User }] : []),
    ...(user?.is_admin ? [{ path: '/admin', label: 'Admin', icon: Shield }] : []),
  ];

  return (
    <div className="min-h-screen bg-[#050505] relative">
      {/* Noise texture overlay */}
      <div className="fixed inset-0 opacity-[0.02] pointer-events-none z-50" 
           style={{backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")'}}></div>
      
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-40 glass border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3">
              <Gamepad2 className="w-8 h-8 text-[#39FF14]" />
              <span className="text-xl font-bold text-white tracking-wider hidden sm:block">FIVEM PORTAL</span>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-4 py-2 text-sm font-medium uppercase tracking-wider transition-colors ${
                    location.pathname === item.path
                      ? 'text-[#39FF14] bg-[#39FF14]/10'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                  data-testid={`nav-${item.label.toLowerCase()}`}
                >
                  {item.label}
                </Link>
              ))}
            </div>

            {/* User Menu */}
            <div className="flex items-center gap-4">
              {user ? (
                <div className="flex items-center gap-3">
                  <img 
                    src={user.avatar_url || 'https://via.placeholder.com/40'} 
                    alt={user.username}
                    className="w-8 h-8 rounded border border-[#39FF14]/50"
                  />
                  <span className="text-white text-sm hidden sm:block">{user.username}</span>
                  {user.is_vip && <Crown className="w-4 h-4 text-[#00F0FF]" />}
                  <button 
                    onClick={logout}
                    className="p-2 text-gray-400 hover:text-[#FF003C] transition-colors"
                    data-testid="logout-btn"
                  >
                    <LogOut className="w-5 h-5" />
                  </button>
                </div>
              ) : (
                <button 
                  onClick={login}
                  className="btn-steam px-4 py-2 text-sm flex items-center gap-2"
                  data-testid="login-btn"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3l-.5 3H13v6.95c5.05-.5 9-4.76 9-9.95 0-5.52-4.48-10-10-10z"/>
                  </svg>
                  Login with Steam
                </button>
              )}

              {/* Mobile Menu Button */}
              <button 
                className="md:hidden p-2 text-gray-400 hover:text-white"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                data-testid="mobile-menu-btn"
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-white/10 bg-[#0A0A0A]">
            <div className="px-4 py-2 space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 text-sm font-medium uppercase tracking-wider ${
                    location.pathname === item.path
                      ? 'text-[#39FF14] bg-[#39FF14]/10'
                      : 'text-gray-400'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Main Content */}
      <main className="pt-16">
        {children}
      </main>
    </div>
  );
};

// ==================== HOME PAGE ====================
const Home = () => {
  const { user, login } = useAuth();
  const [stats, setStats] = useState(null);
  const [serverStatus, setServerStatus] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, statusRes] = await Promise.all([
          axios.get(`${API}/stats`),
          axios.get(`${API}/server/status`)
        ]);
        setStats(statsRes.data);
        setServerStatus(statusRes.data);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="relative">
      {/* Hero Section */}
      <div 
        className="relative min-h-[90vh] flex items-center justify-center"
        style={{
          backgroundImage: 'url("https://images.unsplash.com/photo-1605218427306-022ba78fa38a?q=80&w=2070&auto=format&fit=crop")',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      >
        <div className="hero-overlay absolute inset-0"></div>
        <div className="scanlines absolute inset-0"></div>
        
        <div className="relative z-10 text-center px-4 max-w-4xl mx-auto animate-slide-up">
          <div className="inline-flex items-center gap-2 px-4 py-2 mb-6 border border-[#39FF14]/30 bg-black/50 backdrop-blur">
            <span className={`w-2 h-2 rounded-full ${serverStatus?.online ? 'bg-[#39FF14] animate-pulse' : 'bg-[#FF003C]'}`}></span>
            <span className="text-sm font-mono uppercase tracking-wider text-gray-300">
              {serverStatus?.online ? 'Server Online' : 'Server Offline'}
            </span>
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-black text-white uppercase tracking-tighter mb-4">
            <span className="text-[#39FF14] neon-text">FiveM</span> Roleplay
          </h1>
          <p className="text-lg sm:text-xl text-gray-400 mb-8 max-w-2xl mx-auto">
            Join the ultimate GTA V roleplay experience. Apply for whitelist, queue to join, and become part of our community.
          </p>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <div className="glass p-4">
              <div className="text-3xl font-bold text-[#39FF14] font-mono">{stats?.players_online || 0}/{stats?.max_players || 64}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Players Online</div>
            </div>
            <div className="glass p-4">
              <div className="text-3xl font-bold text-[#00F0FF] font-mono">{stats?.queue_length || 0}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">In Queue</div>
            </div>
            <div className="glass p-4">
              <div className="text-3xl font-bold text-[#FAFF00] font-mono">{stats?.pending_applications || 0}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Pending Apps</div>
            </div>
            <div className="glass p-4">
              <div className="text-3xl font-bold text-white font-mono">{stats?.total_users || 0}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Total Members</div>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {user ? (
              <>
                <Link 
                  to="/queue" 
                  className="btn-primary px-8 py-4 flex items-center justify-center gap-2"
                  data-testid="join-queue-cta"
                >
                  <Users className="w-5 h-5" />
                  Join Queue
                </Link>
                <Link 
                  to="/apply" 
                  className="btn-outline px-8 py-4 flex items-center justify-center gap-2"
                  data-testid="apply-cta"
                >
                  <FileText className="w-5 h-5" />
                  Apply Now
                </Link>
              </>
            ) : (
              <button 
                onClick={login}
                className="btn-steam px-8 py-4 text-lg flex items-center justify-center gap-3"
                data-testid="hero-login-btn"
              >
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3l-.5 3H13v6.95c5.05-.5 9-4.76 9-9.95 0-5.52-4.48-10-10-10z"/>
                </svg>
                Login with Steam to Start
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <section className="py-20 px-4 bg-[#050505]">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-white text-center uppercase tracking-tight mb-12">
            How It <span className="text-[#39FF14]">Works</span>
          </h2>
          
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: Shield, title: 'Apply for Whitelist', desc: 'Submit your application with character backstory and RP experience.' },
              { icon: Users, title: 'Join the Queue', desc: 'Once approved, join the queue with priority based on VIP status.' },
              { icon: Gamepad2, title: 'Start Playing', desc: 'Connect to the server when your turn comes and enjoy the RP!' }
            ].map((feature, idx) => (
              <div key={idx} className="glass p-6 card-hover group">
                <div className="w-12 h-12 flex items-center justify-center bg-[#39FF14]/10 border border-[#39FF14]/30 mb-4 group-hover:bg-[#39FF14]/20 transition-colors">
                  <feature.icon className="w-6 h-6 text-[#39FF14]" />
                </div>
                <h3 className="text-xl font-bold text-white uppercase tracking-wide mb-2">{feature.title}</h3>
                <p className="text-gray-400">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

// ==================== QUEUE PAGE ====================
const QueuePage = () => {
  const { user, token, login } = useAuth();
  const [queueStatus, setQueueStatus] = useState(null);
  const [queueList, setQueueList] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchQueueData = useCallback(async () => {
    try {
      const [listRes, statusRes] = await Promise.all([
        axios.get(`${API}/queue/list`),
        token ? axios.get(`${API}/queue/status?authorization=${token}`) : Promise.resolve({ data: { in_queue: false } })
      ]);
      setQueueList(listRes.data.queue || []);
      setQueueStatus(statusRes.data);
    } catch (error) {
      console.error('Failed to fetch queue:', error);
    }
  }, [token]);

  useEffect(() => {
    fetchQueueData();
    const interval = setInterval(fetchQueueData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchQueueData]);

  const joinQueue = async () => {
    if (!user) {
      login();
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/queue/join?authorization=${token}`);
      toast.success('Successfully joined the queue!');
      fetchQueueData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join queue');
    } finally {
      setLoading(false);
    }
  };

  const leaveQueue = async () => {
    setLoading(true);
    try {
      await axios.delete(`${API}/queue/leave?authorization=${token}`);
      toast.success('Left the queue');
      fetchQueueData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to leave queue');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-8 pb-20 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-white uppercase tracking-tight mb-8 text-center">
          Server <span className="text-[#39FF14]">Queue</span>
        </h1>

        {/* User Queue Status Card */}
        {user && (
          <div className="glass p-8 mb-8 animate-fade-in">
            {queueStatus?.in_queue ? (
              <div className="text-center">
                <div className="mb-4">
                  <span className="text-sm text-gray-500 uppercase tracking-wider">Your Position</span>
                  <div className="queue-position">{queueStatus.entry?.position || '-'}</div>
                </div>
                <div className="grid grid-cols-2 gap-4 max-w-md mx-auto mb-6">
                  <div className="bg-black/30 p-4">
                    <Clock className="w-5 h-5 text-[#00F0FF] mx-auto mb-2" />
                    <div className="text-2xl font-bold text-white">{queueStatus.entry?.estimated_wait_minutes || 0}</div>
                    <div className="text-xs text-gray-500 uppercase">Est. Minutes</div>
                  </div>
                  <div className="bg-black/30 p-4">
                    <Crown className="w-5 h-5 text-[#FAFF00] mx-auto mb-2" />
                    <div className="text-lg font-bold text-white uppercase">{queueStatus.entry?.priority || 'Regular'}</div>
                    <div className="text-xs text-gray-500 uppercase">Priority</div>
                  </div>
                </div>
                <button 
                  onClick={leaveQueue}
                  disabled={loading}
                  className="btn-outline px-8 py-3 text-[#FF003C] border-[#FF003C] hover:bg-[#FF003C]/10"
                  data-testid="leave-queue-btn"
                >
                  {loading ? 'Processing...' : 'Leave Queue'}
                </button>
              </div>
            ) : (
              <div className="text-center">
                <p className="text-gray-400 mb-6">You are not currently in the queue</p>
                <button 
                  onClick={joinQueue}
                  disabled={loading}
                  className="btn-primary px-8 py-4 text-lg"
                  data-testid="join-queue-btn"
                >
                  {loading ? 'Joining...' : 'Join Queue'}
                </button>
              </div>
            )}
          </div>
        )}

        {!user && (
          <div className="glass p-8 mb-8 text-center">
            <p className="text-gray-400 mb-4">Login with Steam to join the queue</p>
            <button onClick={login} className="btn-steam px-6 py-3" data-testid="queue-login-btn">
              Login with Steam
            </button>
          </div>
        )}

        {/* Queue List */}
        <div className="glass p-6">
          <h2 className="text-xl font-bold text-white uppercase tracking-wide mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-[#39FF14]" />
            Current Queue ({queueList.length})
          </h2>
          
          {queueList.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Queue is empty</p>
          ) : (
            <div className="space-y-2">
              {queueList.map((entry, idx) => (
                <div 
                  key={entry.id} 
                  className={`flex items-center gap-4 p-4 bg-black/30 border border-white/5 ${
                    entry.user_id === user?.id ? 'border-[#39FF14]/50 bg-[#39FF14]/5' : ''
                  }`}
                >
                  <div className="w-10 h-10 flex items-center justify-center bg-black/50 font-mono font-bold text-[#39FF14]">
                    {entry.position}
                  </div>
                  <img 
                    src={entry.avatar_url || 'https://via.placeholder.com/40'} 
                    alt={entry.username}
                    className="w-10 h-10 rounded"
                  />
                  <div className="flex-1">
                    <div className="text-white font-medium">{entry.username}</div>
                    <div className="text-xs text-gray-500 font-mono">Est. {entry.estimated_wait_minutes} min</div>
                  </div>
                  {entry.priority === 'vip' && (
                    <span className="badge-vip px-2 py-1 text-xs font-mono">VIP</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== APPLY PAGE ====================
const ApplyPage = () => {
  const { user, token, login } = useAuth();
  const [activeTab, setActiveTab] = useState('whitelist');
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    discord_username: '',
    in_game_hours: '',
    roleplay_experience: '',
    character_backstory: '',
    why_join: '',
    previous_servers: '',
    job_type: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!user) {
      login();
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/applications?authorization=${token}`, {
        application_type: activeTab,
        job_type: activeTab === 'job' ? formData.job_type : null,
        discord_username: formData.discord_username,
        in_game_hours: parseInt(formData.in_game_hours) || 0,
        roleplay_experience: formData.roleplay_experience,
        character_backstory: formData.character_backstory,
        why_join: formData.why_join,
        previous_servers: formData.previous_servers || null
      });
      toast.success('Application submitted successfully!');
      setFormData({
        discord_username: '',
        in_game_hours: '',
        roleplay_experience: '',
        character_backstory: '',
        why_join: '',
        previous_servers: '',
        job_type: ''
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit application');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen pt-20 pb-20 px-4">
        <div className="max-w-2xl mx-auto glass p-8 text-center">
          <Shield className="w-16 h-16 text-[#39FF14] mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white uppercase tracking-tight mb-4">Apply Now</h1>
          <p className="text-gray-400 mb-6">Login with Steam to submit your application</p>
          <button onClick={login} className="btn-steam px-6 py-3" data-testid="apply-login-btn">
            Login with Steam
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-8 pb-20 px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold text-white uppercase tracking-tight mb-8 text-center">
          Submit <span className="text-[#39FF14]">Application</span>
        </h1>

        {/* Tabs */}
        <div className="flex mb-8 border-b border-white/10">
          <button
            onClick={() => setActiveTab('whitelist')}
            className={`flex-1 py-4 text-center font-bold uppercase tracking-wider transition-colors ${
              activeTab === 'whitelist' 
                ? 'text-[#39FF14] border-b-2 border-[#39FF14]' 
                : 'text-gray-500 hover:text-white'
            }`}
            data-testid="whitelist-tab"
          >
            <Shield className="w-5 h-5 inline mr-2" />
            Whitelist
          </button>
          <button
            onClick={() => setActiveTab('job')}
            className={`flex-1 py-4 text-center font-bold uppercase tracking-wider transition-colors ${
              activeTab === 'job' 
                ? 'text-[#39FF14] border-b-2 border-[#39FF14]' 
                : 'text-gray-500 hover:text-white'
            }`}
            data-testid="job-tab"
          >
            <Briefcase className="w-5 h-5 inline mr-2" />
            Job Application
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="glass p-6 space-y-6">
          {activeTab === 'job' && (
            <div>
              <label className="block text-sm font-mono text-gray-400 uppercase tracking-wider mb-2">
                Job Type *
              </label>
              <select
                name="job_type"
                value={formData.job_type}
                onChange={handleChange}
                required
                className="w-full bg-black/50 border border-white/10 text-white p-3 focus:border-[#39FF14] outline-none"
                data-testid="job-type-select"
              >
                <option value="">Select a job...</option>
                <option value="police">Police Department</option>
                <option value="ems">Emergency Medical Services</option>
                <option value="mechanic">Mechanic</option>
                <option value="taxi">Taxi Driver</option>
                <option value="lawyer">Lawyer</option>
                <option value="real_estate">Real Estate Agent</option>
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-mono text-gray-400 uppercase tracking-wider mb-2">
              Discord Username *
            </label>
            <input
              type="text"
              name="discord_username"
              value={formData.discord_username}
              onChange={handleChange}
              required
              placeholder="e.g., username#1234"
              className="terminal-input w-full text-white p-3"
              data-testid="discord-input"
            />
          </div>

          <div>
            <label className="block text-sm font-mono text-gray-400 uppercase tracking-wider mb-2">
              In-Game Hours *
            </label>
            <input
              type="number"
              name="in_game_hours"
              value={formData.in_game_hours}
              onChange={handleChange}
              required
              placeholder="Total hours in GTA V/FiveM"
              className="terminal-input w-full text-white p-3"
              data-testid="hours-input"
            />
          </div>

          <div>
            <label className="block text-sm font-mono text-gray-400 uppercase tracking-wider mb-2">
              Roleplay Experience *
            </label>
            <textarea
              name="roleplay_experience"
              value={formData.roleplay_experience}
              onChange={handleChange}
              required
              rows={4}
              placeholder="Describe your previous roleplay experience..."
              className="terminal-input w-full text-white p-3 resize-none"
              data-testid="experience-textarea"
            />
          </div>

          <div>
            <label className="block text-sm font-mono text-gray-400 uppercase tracking-wider mb-2">
              Character Backstory *
            </label>
            <textarea
              name="character_backstory"
              value={formData.character_backstory}
              onChange={handleChange}
              required
              rows={6}
              placeholder="Tell us about your character's background, motivations, and goals..."
              className="terminal-input w-full text-white p-3 resize-none"
              data-testid="backstory-textarea"
            />
          </div>

          <div>
            <label className="block text-sm font-mono text-gray-400 uppercase tracking-wider mb-2">
              Why Do You Want to Join? *
            </label>
            <textarea
              name="why_join"
              value={formData.why_join}
              onChange={handleChange}
              required
              rows={4}
              placeholder="What attracts you to our server?"
              className="terminal-input w-full text-white p-3 resize-none"
              data-testid="why-join-textarea"
            />
          </div>

          <div>
            <label className="block text-sm font-mono text-gray-400 uppercase tracking-wider mb-2">
              Previous Servers (Optional)
            </label>
            <input
              type="text"
              name="previous_servers"
              value={formData.previous_servers}
              onChange={handleChange}
              placeholder="List any previous FiveM servers you've played on"
              className="terminal-input w-full text-white p-3"
              data-testid="servers-input"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-4 text-lg"
            data-testid="submit-application-btn"
          >
            {loading ? 'Submitting...' : 'Submit Application'}
          </button>
        </form>
      </div>
    </div>
  );
};

// ==================== DASHBOARD PAGE ====================
const DashboardPage = () => {
  const { user, token } = useAuth();
  const [applications, setApplications] = useState([]);
  const [queueStatus, setQueueStatus] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [appsRes, queueRes] = await Promise.all([
          axios.get(`${API}/applications/my?authorization=${token}`),
          axios.get(`${API}/queue/status?authorization=${token}`)
        ]);
        setApplications(appsRes.data.applications || []);
        setQueueStatus(queueRes.data);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      }
    };
    if (token) fetchData();
  }, [token]);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'approved':
        return <span className="badge-online px-2 py-1 text-xs font-mono flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Approved</span>;
      case 'denied':
        return <span className="badge-offline px-2 py-1 text-xs font-mono flex items-center gap-1"><XCircle className="w-3 h-3" /> Denied</span>;
      default:
        return <span className="badge-pending px-2 py-1 text-xs font-mono flex items-center gap-1"><AlertCircle className="w-3 h-3" /> Pending</span>;
    }
  };

  if (!user) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen pt-8 pb-20 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-white uppercase tracking-tight mb-8">
          Welcome, <span className="text-[#39FF14]">{user.username}</span>
        </h1>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Profile Card */}
          <div className="glass p-6">
            <h2 className="text-xl font-bold text-white uppercase tracking-wide mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-[#39FF14]" />
              Profile
            </h2>
            <div className="flex items-center gap-4">
              <img 
                src={user.avatar_url || 'https://via.placeholder.com/80'} 
                alt={user.username}
                className="w-20 h-20 rounded border-2 border-[#39FF14]/50"
              />
              <div>
                <div className="text-xl font-bold text-white">{user.username}</div>
                <div className="text-sm text-gray-500 font-mono">{user.steam_id}</div>
                <div className="flex gap-2 mt-2">
                  {user.is_vip && <span className="badge-vip px-2 py-1 text-xs">VIP</span>}
                  {user.is_admin && <span className="badge-online px-2 py-1 text-xs">Admin</span>}
                </div>
              </div>
            </div>
          </div>

          {/* Queue Status Card */}
          <div className="glass p-6">
            <h2 className="text-xl font-bold text-white uppercase tracking-wide mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-[#39FF14]" />
              Queue Status
            </h2>
            {queueStatus?.in_queue ? (
              <div>
                <div className="text-4xl font-bold text-[#39FF14] mb-2">#{queueStatus.entry?.position}</div>
                <div className="text-gray-400">Estimated wait: {queueStatus.entry?.estimated_wait_minutes} minutes</div>
                <Link to="/queue" className="btn-outline mt-4 inline-block px-4 py-2 text-sm">
                  View Queue
                </Link>
              </div>
            ) : (
              <div>
                <p className="text-gray-400 mb-4">You're not in the queue</p>
                <Link to="/queue" className="btn-primary px-4 py-2 text-sm inline-block" data-testid="dashboard-join-queue">
                  Join Queue
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Applications */}
        <div className="glass p-6 mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white uppercase tracking-wide flex items-center gap-2">
              <FileText className="w-5 h-5 text-[#39FF14]" />
              My Applications
            </h2>
            <Link to="/apply" className="btn-outline px-4 py-2 text-sm" data-testid="new-application-btn">
              New Application
            </Link>
          </div>
          
          {applications.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No applications yet</p>
          ) : (
            <div className="space-y-4">
              {applications.map((app) => (
                <div key={app.id} className="bg-black/30 p-4 border border-white/5">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-white font-bold uppercase">
                        {app.application_type === 'whitelist' ? 'Whitelist' : `Job: ${app.job_type}`}
                      </span>
                      <div className="text-xs text-gray-500 font-mono mt-1">
                        Submitted: {new Date(app.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    {getStatusBadge(app.status)}
                  </div>
                  {app.admin_notes && (
                    <div className="mt-3 p-3 bg-black/30 border-l-2 border-[#39FF14]">
                      <div className="text-xs text-gray-500 uppercase mb-1">Admin Notes:</div>
                      <div className="text-gray-300 text-sm">{app.admin_notes}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== ADMIN PAGE ====================
const AdminPage = () => {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState('applications');
  const [applications, setApplications] = useState([]);
  const [counts, setCounts] = useState({});
  const [queue, setQueue] = useState([]);
  const [users, setUsers] = useState([]);
  const [filter, setFilter] = useState('pending');
  const [loading, setLoading] = useState(false);

  const fetchApplications = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/applications?status=${filter}&authorization=${token}`);
      setApplications(res.data.applications || []);
      setCounts(res.data.counts || {});
    } catch (error) {
      console.error('Failed to fetch applications:', error);
    }
  }, [token, filter]);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/queue?authorization=${token}`);
      setQueue(res.data.queue || []);
    } catch (error) {
      console.error('Failed to fetch queue:', error);
    }
  }, [token]);

  const fetchUsers = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/users?authorization=${token}`);
      setUsers(res.data.users || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  }, [token]);

  useEffect(() => {
    if (activeTab === 'applications') fetchApplications();
    else if (activeTab === 'queue') fetchQueue();
    else if (activeTab === 'users') fetchUsers();
  }, [activeTab, fetchApplications, fetchQueue, fetchUsers]);

  const reviewApplication = async (appId, status, notes = '') => {
    setLoading(true);
    try {
      await axios.put(`${API}/admin/applications/${appId}/review?authorization=${token}`, {
        status,
        admin_notes: notes
      });
      toast.success(`Application ${status}`);
      fetchApplications();
    } catch (error) {
      toast.error('Failed to review application');
    } finally {
      setLoading(false);
    }
  };

  const removeFromQueue = async (entryId) => {
    try {
      await axios.delete(`${API}/admin/queue/${entryId}?authorization=${token}`);
      toast.success('Removed from queue');
      fetchQueue();
    } catch (error) {
      toast.error('Failed to remove from queue');
    }
  };

  const toggleVip = async (userId) => {
    try {
      await axios.put(`${API}/admin/users/${userId}/toggle-vip?authorization=${token}`);
      toast.success('VIP status updated');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update VIP status');
    }
  };

  const toggleAdmin = async (userId) => {
    try {
      await axios.put(`${API}/admin/users/${userId}/toggle-admin?authorization=${token}`);
      toast.success('Admin status updated');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update admin status');
    }
  };

  if (!user?.is_admin) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen pt-8 pb-20 px-4" data-testid="admin-panel">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-white uppercase tracking-tight mb-8">
          Admin <span className="text-[#39FF14]">Panel</span>
        </h1>

        {/* Tabs */}
        <div className="flex gap-2 mb-8 border-b border-white/10 pb-4">
          {[
            { id: 'applications', label: 'Applications', icon: FileText },
            { id: 'queue', label: 'Queue', icon: Users },
            { id: 'users', label: 'Users', icon: User }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 font-bold uppercase tracking-wider flex items-center gap-2 transition-colors ${
                activeTab === tab.id 
                  ? 'text-[#39FF14] bg-[#39FF14]/10' 
                  : 'text-gray-500 hover:text-white hover:bg-white/5'
              }`}
              data-testid={`admin-tab-${tab.id}`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Applications Tab */}
        {activeTab === 'applications' && (
          <div>
            {/* Filters */}
            <div className="flex gap-2 mb-6">
              {['pending', 'approved', 'denied'].map((status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={`px-4 py-2 text-sm font-mono uppercase ${
                    filter === status 
                      ? 'bg-[#39FF14] text-black' 
                      : 'bg-black/30 text-gray-400 hover:text-white'
                  }`}
                  data-testid={`filter-${status}`}
                >
                  {status} ({counts[status] || 0})
                </button>
              ))}
            </div>

            {/* Applications List */}
            <div className="space-y-4">
              {applications.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No {filter} applications</p>
              ) : (
                applications.map((app) => (
                  <div key={app.id} className="glass p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-4">
                        <img 
                          src={app.avatar_url || 'https://via.placeholder.com/50'} 
                          alt={app.username}
                          className="w-12 h-12 rounded"
                        />
                        <div>
                          <div className="text-white font-bold">{app.username}</div>
                          <div className="text-xs text-gray-500 font-mono">{app.steam_id}</div>
                          <div className="text-xs text-gray-500 mt-1">
                            {app.application_type === 'whitelist' ? 'Whitelist' : `Job: ${app.job_type}`}
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 font-mono">
                        {new Date(app.created_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-4 mb-4 text-sm">
                      <div>
                        <div className="text-gray-500 uppercase text-xs mb-1">Discord</div>
                        <div className="text-white">{app.discord_username}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase text-xs mb-1">In-Game Hours</div>
                        <div className="text-white">{app.in_game_hours}</div>
                      </div>
                    </div>

                    <div className="space-y-3 mb-4">
                      <div>
                        <div className="text-gray-500 uppercase text-xs mb-1">RP Experience</div>
                        <div className="text-gray-300 text-sm bg-black/30 p-3">{app.roleplay_experience}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase text-xs mb-1">Character Backstory</div>
                        <div className="text-gray-300 text-sm bg-black/30 p-3">{app.character_backstory}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase text-xs mb-1">Why Join</div>
                        <div className="text-gray-300 text-sm bg-black/30 p-3">{app.why_join}</div>
                      </div>
                    </div>

                    {app.status === 'pending' && (
                      <div className="flex gap-3">
                        <button
                          onClick={() => reviewApplication(app.id, 'approved')}
                          disabled={loading}
                          className="btn-primary px-6 py-2 flex items-center gap-2"
                          data-testid={`approve-${app.id}`}
                        >
                          <CheckCircle className="w-4 h-4" /> Approve
                        </button>
                        <button
                          onClick={() => reviewApplication(app.id, 'denied')}
                          disabled={loading}
                          className="btn-outline px-6 py-2 text-[#FF003C] border-[#FF003C] flex items-center gap-2"
                          data-testid={`deny-${app.id}`}
                        >
                          <XCircle className="w-4 h-4" /> Deny
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Queue Tab */}
        {activeTab === 'queue' && (
          <div className="glass p-6">
            <h2 className="text-xl font-bold text-white uppercase tracking-wide mb-4">
              Queue Management ({queue.length} in queue)
            </h2>
            {queue.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Queue is empty</p>
            ) : (
              <div className="space-y-2">
                {queue.map((entry) => (
                  <div key={entry.id} className="flex items-center gap-4 p-4 bg-black/30 border border-white/5">
                    <div className="w-10 h-10 flex items-center justify-center bg-black/50 font-mono font-bold text-[#39FF14]">
                      {entry.position}
                    </div>
                    <img 
                      src={entry.avatar_url || 'https://via.placeholder.com/40'} 
                      alt={entry.username}
                      className="w-10 h-10 rounded"
                    />
                    <div className="flex-1">
                      <div className="text-white font-medium">{entry.username}</div>
                      <div className="text-xs text-gray-500 font-mono">{entry.steam_id}</div>
                    </div>
                    <span className={entry.priority === 'vip' ? 'badge-vip' : 'badge-pending'}>
                      {entry.priority.toUpperCase()}
                    </span>
                    <button
                      onClick={() => removeFromQueue(entry.id)}
                      className="p-2 text-[#FF003C] hover:bg-[#FF003C]/10"
                      data-testid={`remove-queue-${entry.id}`}
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="glass p-6">
            <h2 className="text-xl font-bold text-white uppercase tracking-wide mb-4">
              User Management ({users.length} users)
            </h2>
            <div className="space-y-2">
              {users.map((u) => (
                <div key={u.id} className="flex items-center gap-4 p-4 bg-black/30 border border-white/5">
                  <img 
                    src={u.avatar_url || 'https://via.placeholder.com/40'} 
                    alt={u.username}
                    className="w-10 h-10 rounded"
                  />
                  <div className="flex-1">
                    <div className="text-white font-medium">{u.username}</div>
                    <div className="text-xs text-gray-500 font-mono">{u.steam_id}</div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => toggleVip(u.id)}
                      className={`px-3 py-1 text-xs font-mono uppercase ${
                        u.is_vip ? 'badge-vip' : 'bg-black/30 text-gray-500'
                      }`}
                      data-testid={`toggle-vip-${u.id}`}
                    >
                      VIP
                    </button>
                    <button
                      onClick={() => toggleAdmin(u.id)}
                      className={`px-3 py-1 text-xs font-mono uppercase ${
                        u.is_admin ? 'badge-online' : 'bg-black/30 text-gray-500'
                      }`}
                      data-testid={`toggle-admin-${u.id}`}
                    >
                      Admin
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ==================== MAIN APP ====================
function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster 
          position="top-right" 
          theme="dark"
          toastOptions={{
            style: {
              background: '#0A0A0A',
              border: '1px solid rgba(57, 255, 20, 0.3)',
              color: '#fff',
            },
          }}
        />
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/queue" element={<QueuePage />} />
            <Route path="/apply" element={<ApplyPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
