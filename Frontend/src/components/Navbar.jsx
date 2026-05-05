import { Link, NavLink } from "react-router-dom";
import { BrainCircuit, Workflow } from "lucide-react";

function Navbar() {
  return (
    <nav className="navbar">
      <Link to="/" className="logo">
        <BrainCircuit size={22} />
        <span>SynapseAI</span>
      </Link>

      <div className="nav-links">
        <NavLink to="/" className="nav-link">
          Research
        </NavLink>

        <NavLink to="/engineering" className="engineering-btn">
          <Workflow size={18} />
          Engineering
        </NavLink>
      </div>
    </nav>
  );
}

export default Navbar;