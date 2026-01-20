import { Routes, Route } from "react-router-dom";
import Home from "./Home";
import Login from "./Login";
import Signup from "./Signup";
import MyCryptocurrency from "./myCryptocurrency";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/myCryptocurrency" element={<MyCryptocurrency />} />
    </Routes>
  );
}

export default App;
