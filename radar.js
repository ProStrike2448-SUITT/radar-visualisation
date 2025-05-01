// Константа для елементу форми
const form = document.querySelector("#params");
const radarElement = document.getElementById("radar");
let radarConfig = null;

// Оновлення полів форми значеннями з конфігурації
function updateFormInputs(config) {
  Object.keys(config).forEach((key) => {
    const input = form.querySelector(`[name="${key}"]`);
    if (input) {
      input.value = config[key];
    }
  });
}

// Завантаження конфігурації з сервера
async function loadRadarConfig() {
  try {
    const response = await fetch("http://localhost:4000/config", {
      method: "PUT",
    });
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    const res = await response.json();
    radarConfig = res.config;
    updateFormInputs(radarConfig);
  } catch (error) {
    console.error("Помилка при завантаженні конфігурації:", error);
  }
}

// Відправлення даних форми
async function updateRadarConfig() {
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  // Перетворення значень у числа
  for (const key in data) {
    data[key] = Number(data[key]);
  }

  try {
    const response = await fetch("http://localhost:4000/config", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    const res = await response.json();
    radarConfig = res.config;
    updateFormInputs(radarConfig);
    console.log("Конфігурація оновлена:", radarConfig);
  } catch (error) {
    console.error("Помилка при відправленні даних:", error);
  }
}

// Обробка події відправлення форми
form.addEventListener("submit", (event) => {
  event.preventDefault();
  updateRadarConfig();
});

// Ініціалізація WebSocket
function initWebSocket() {
  const socket = new WebSocket("ws://localhost:4000/");

  socket.addEventListener("open", () => {
    console.log("Підключено до WebSocket сервера");
  });

  socket.addEventListener("message", (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.echoResponses.length && radarConfig) {
        const angle = msg.scanAngle;
        const time = msg.echoResponses[0].time;
        const power = msg.echoResponses[0].power;
        const relativeDistance = (time * 300_000) / 2;

        const data = [
          {
            type: "scatterpolar",
            r: [relativeDistance],
            theta: [angle],
            fill: "toself",
            marker: {
              color: [power],
              cmin: 0.0,
              cmax: 1.0,
              colorscale: [
                [0.0, "rgb(255, 0, 0)"],
                [0.5, "rgb(255, 255, 0)"],
                [1.0, "rgb(0, 255, 0)"],
              ],
              showscale: true,
            },
          },
        ];

        const layout = {
          polar: {
            radialaxis: {
              visible: true,
              range: [0, radarConfig.emulationZoneSize],
              title: {
                text: "км",
              },
            },
          },
          showlegend: false,
        };

        const config = { responsive: true, displayModeBar: false };

        Plotly.newPlot(radarElement, data, layout, config);
      }
    } catch (error) {
      console.error("Помилка при обробці повідомлення:", error);
    }
  });

  socket.addEventListener("close", () => {
    console.log("З'єднання закрито");
  });

  socket.addEventListener("error", (error) => {
    console.error("Помилка WebSocket:", error);
  });
}

// Ініціалізація при завантаженні сторінки
document.addEventListener("DOMContentLoaded", () => {
  loadRadarConfig();
  initWebSocket();
});
