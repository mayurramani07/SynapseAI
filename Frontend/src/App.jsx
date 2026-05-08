import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Research from "./pages/Research";
import Engineering from "./pages/Engineering";

function App() {
  return (
    <div className="app">
      <Navbar />

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/research" element={<Research />} />
        <Route path="/engineering" element={<Engineering />} />
      </Routes>
    </div>
  );
}

export default App;