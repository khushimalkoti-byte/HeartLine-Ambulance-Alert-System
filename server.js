
require("dotenv").config();

const express = require("express");
const cors = require("cors");
const path = require("path");

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Serve frontend files
app.use(express.static(
    path.join(__dirname, "../frontend/frontend")
));

// Home route
app.get("/", (req, res) => {
    res.sendFile(
        path.join(__dirname, "../frontend/frontend/index.html")
    );
});


app.post("/api/hospitals", async (req, res) => {
  try {
    const { hospitalName, website } = req.body;

    if (!hospitalName || !website) {
      return res.status(400).json({
        error: "Hospital name and website are required"
      });
    }

    const parsedUrl = new URL(website);

    if (!["https:", "http:"].includes(parsedUrl.protocol)) {
      return res.status(400).json({ error: "Invalid website" });
    }

    const response = await fetch(
      "https://agent.tinyfish.ai/v1/automation/run",
      {
        method: "POST",
        headers: {
          "X-API-Key": process.env.TINYFISH_API_KEY,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          url: website,
          goal: `Research ${hospitalName}. Extract its official
          address, contact number, emergency services, medical
          facilities, and published emergency bed availability.
          Include source URLs. Never guess. If availability is
          not published, say Not publicly available.
          Return structured JSON.`
        }),
        signal: AbortSignal.timeout(120000)
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return res.status(response.status).json(data);
    }

    res.json(data);

  } catch (error) {
    res.status(500).json({
      error: error.message
    });
  }
});

app.listen(3000, () => {
  console.log("HeartLine server running on port 3000");
});
