import { useNavigate, useLocation } from "react-router-dom";
import { Home, History, BarChart3, Settings, LogOut, AlertTriangle } from "lucide-react";

export default function Sidebar({ onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = JSON.parse(localStorage.getItem("user") || "{}");

  const menuItems = user.role === "admin" ? [
    { icon: Home, path: "/admin", label: "Dashboard" },
    { icon: History, path: "/history", label: "History" },
    { icon: BarChart3, path: "/analytics", label: "Analytics" },
    { icon: Settings, path: "/settings", label: "Settings" }
  ] : [
    { icon: AlertTriangle, path: "/emergency", label: "Incidents" },
    { icon: History, path: "/history", label: "History" }
  ];

  return (
    <nav className="sidebar-nav" data-testid="sidebar">
      <div className="w-10 h-10 rounded-full bg-red-600 flex items-center justify-center mb-4">
        <AlertTriangle className="w-5 h-5 text-white" />
      </div>

      <div className="flex flex-col gap-2 flex-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || location.pathname.startsWith(item.path);
          
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              data-testid={`nav-${item.label.toLowerCase()}`}
              className={`sidebar-nav-item ${isActive ? "active" : ""}`}
              title={item.label}
            >
              <Icon className="w-5 h-5" />
            </button>
          );
        })}
      </div>

      <button
        onClick={onLogout}
        data-testid="logout-button"
        className="sidebar-nav-item text-red-500 hover:bg-red-500/10"
        title="Logout"
      >
        <LogOut className="w-5 h-5" />
      </button>
    </nav>
  );
}
