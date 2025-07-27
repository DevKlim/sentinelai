import { NavLink } from "react-router-dom";
import { Home, FileText, Shield } from "lucide-react";

const Sidebar = () => {
  return (
    <div className="w-64 h-screen p-4 border-r">
      <h1 className="text-2xl font-bold mb-8">Sentinel</h1>
      <nav className="flex flex-col space-y-2">
        <NavLink
          to="/"
          className="flex items-center p-2 rounded-md hover:bg-gray-100"
        >
          <Home className="w-5 h-5 mr-2" />
          Dashboard
        </NavLink>
        <NavLink
          to="/eido"
          className="flex items-center p-2 rounded-md hover:bg-gray-100"
        >
          <FileText className="w-5 h-5 mr-2" />
          EIDO Reports
        </NavLink>
        <NavLink
          to="/idx"
          className="flex items-center p-2 rounded-md hover:bg-gray-100"
        >
          <Shield className="w-5 h-5 mr-2" />
          IDX Incidents
        </NavLink>
      </nav>
    </div>
  );
};

export default Sidebar;
