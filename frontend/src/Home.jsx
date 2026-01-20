import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./index.css"

function Home() {
  const [symbol, setSymbol] = useState("BTC-USDT");
  const [imageUrl, setImageUrl] = useState(null);
  const navigate = useNavigate();

  const runPrediction = async () => {
    const res = await fetch(
      `http://localhost:5000/predict?symbol=${symbol}`
    );
    const data = await res.json();
    setImageUrl(data.image_url);
  };

  return (
    <div className="p-6 max-w-xl mx-auto space-y-4 container">
      <div className="container-top flex justify-between items-center">
        <h1 className="text-xl font-semibold">Cryptocurrency</h1>

        <div className="flex gap-2">
          <button
            className="login"
            onClick={() => navigate("/login")}
          >
            Login
          </button>

          <button
            className="signup"
            onClick={() => navigate("/signup")}
          >
            Signup
          </button>
        </div>
      </div>

      <div className="container-bottom space-y-2">
        <h2>Crypto Types</h2>

        <input
          className="p-2 border rounded-xl w-full"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />

        <button
          className="p-2 bg-blue-600 text-white rounded-xl result w-full"
          onClick={runPrediction}
        >
          Run guess
        </button>
      </div>

      {imageUrl && (
        <div className="mt-4">
          <img
            src={imageUrl}
            alt="Prediction Chart"
            className="rounded-xl"
          />
        </div>
      )}
    </div>
  );
}

export default Home;