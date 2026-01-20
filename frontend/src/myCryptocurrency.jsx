import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./index.css";

function myCryptocurrency() {
  const navigate = useNavigate();

  // Takip edilen kripto paralar
  const [cryptos, setCryptos] = useState([
    { symbol: "BTC-USDT", imageUrl: null, loading: false },
    { symbol: "ETH-USDT", imageUrl: null, loading: false },
    { symbol: "SOL-USDT", imageUrl: null, loading: false }
  ]);

  // Input alanını güncellemek için
  const handleSymbolChange = (index, value) => {
    const newCryptos = [...cryptos];
    newCryptos[index].symbol = value.toUpperCase();
    setCryptos(newCryptos);
  };

  // Prediction çalıştır
  const runPrediction = async (index) => {
    const newCryptos = [...cryptos];
    newCryptos[index].loading = true;
    setCryptos(newCryptos);

    try {
      const res = await fetch(
        `http://localhost:5000/predict?symbol=${newCryptos[index].symbol}`
      );
      const data = await res.json();
      newCryptos[index].imageUrl = data.image_url || null;
    } catch (err) {
      console.error(err);
      newCryptos[index].imageUrl = null;
      alert("Tahmin alınamadı!");
    } finally {
      newCryptos[index].loading = false;
      setCryptos(newCryptos);
    }
  };

  // Yeni takip edilecek kripto ekle
  const addCrypto = () => {
    setCryptos([...cryptos, { symbol: "", imageUrl: null, loading: false }]);
  };

  return (
    <div className="p-6 max-w-xl mx-auto space-y-4 container">
      <div className="container-top flex justify-between items-center">
        <h1 className="text-xl font-semibold">my Cryptocurrency</h1>
      </div>

      <div className="container-bottom space-y-4">
        <h2>Followed Cryptos</h2>

        {cryptos.map((crypto, index) => (
          <div key={index} className="space-y-2">
            <input
              className="p-2 border rounded-xl w-full"
              value={crypto.symbol}
              onChange={(e) => handleSymbolChange(index, e.target.value)}
              placeholder="Enter symbol (e.g., BTC-USDT)"
            />
            <button
              className="p-2 bg-blue-600 text-white rounded-xl result w-full"
              onClick={() => runPrediction(index)}
              disabled={crypto.loading || !crypto.symbol}
            >
              {crypto.loading ? "Loading..." : "Run guess"}
            </button>

            {crypto.imageUrl && (
              <div className="mt-2">
                <img
                  src={crypto.imageUrl}
                  alt={`Prediction for ${crypto.symbol}`}
                  className="rounded-xl"
                />
              </div>
            )}
          </div>
        ))}

        <button
          className="p-2 bg-green-600 text-white rounded-xl w-full"
          onClick={addCrypto}
        >
          + Add another crypto
        </button>
      </div>
    </div>
  );
}

export default myCryptocurrency;
