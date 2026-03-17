import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import { toast } from "sonner";
import { Eye, EyeOff, Shield } from "lucide-react";

export default function Login() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    name: "",
    role: "admin"
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        const response = await axios.post(`${API}/auth/login`, {
          email: formData.email,
          password: formData.password
        });
        
        localStorage.setItem("token", response.data.access_token);
        localStorage.setItem("user", JSON.stringify(response.data.user));
        
        toast.success("Login successful");
        
        if (response.data.user.role === "admin") {
          navigate("/admin");
        } else {
          navigate("/emergency");
        }
      } else {
        const response = await axios.post(`${API}/auth/register`, formData);
        toast.success("Registration successful! Please login.");
        setIsLogin(true);
        setFormData({ email: "", password: "", name: "", role: "admin" });
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{
        backgroundImage: `url('https://images.unsplash.com/photo-1580035144415-01307b0e464a?crop=entropy&cs=srgb&fm=jpg&q=85')`,
        backgroundSize: 'cover',
        backgroundPosition: 'center'
      }}>
      <div className="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm"></div>
      
      <div className="relative z-10 w-full max-w-md">
        <div className="glass-card p-8 border border-zinc-800">
          <div className="flex items-center justify-center mb-8">
            <div className="w-12 h-12 rounded-full bg-red-600 flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
          </div>
          
          <h1 className="text-3xl font-bold text-center mb-2 uppercase tracking-wide" data-testid="login-title">
            Accident Detection
          </h1>
          <p className="text-zinc-400 text-center mb-8 text-sm">Real-time Safety Monitoring System</p>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="name">Full Name</label>
                <input
                  id="name"
                  type="text"
                  data-testid="register-name-input"
                  placeholder="Enter your name"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all placeholder:text-zinc-600"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                data-testid="login-email-input"
                placeholder="admin@example.com"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all placeholder:text-zinc-600"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="password">Password</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  data-testid="login-password-input"
                  placeholder="Enter your password"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all placeholder:text-zinc-600"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                  onClick={() => setShowPassword(!showPassword)}
                  data-testid="toggle-password-visibility"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="role">Role</label>
                <select
                  id="role"
                  data-testid="register-role-select"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                >
                  <option value="admin">Admin</option>
                  <option value="emergency_services">Emergency Services</option>
                </select>
              </div>
            )}
            
            <button
              type="submit"
              data-testid="login-submit-button"
              disabled={loading}
              className="w-full btn-primary py-2.5 font-semibold uppercase tracking-wide disabled:opacity-50"
            >
              {loading ? "Processing..." : isLogin ? "Login" : "Register"}
            </button>
          </form>
          
          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setIsLogin(!isLogin);
                setFormData({ email: "", password: "", name: "", role: "admin" });
              }}
              data-testid="toggle-auth-mode"
              className="text-blue-400 hover:text-blue-300 text-sm transition-colors"
            >
              {isLogin ? "Need an account? Register" : "Already have an account? Login"}
            </button>
          </div>
        </div>
        
        <div className="mt-4 text-center text-xs text-zinc-500">
          <p>Demo credentials: admin@demo.com / password123</p>
        </div>
      </div>
    </div>
  );
}
