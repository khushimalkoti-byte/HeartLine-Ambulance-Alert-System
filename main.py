
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="HeartLine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary demo storage
obstacles = []
current_alert = None


class Obstacle(BaseModel):
    latitude: float
    longitude: float
    description: str = "Road obstacle"


class RouteRequest(BaseModel):
    start: str
    destination: str


class AlertRequest(BaseModel):
    road_or_area: str


# Manages connected HeartLine users
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


@app.get("/")
def home():
    return {
        "message": "HeartLine Backend is running!",
        "status": "success"
    }


@app.post("/calculate-route")
def calculate_route(route: RouteRequest):
    if not route.start.strip() or not route.destination.strip():
        raise HTTPException(
            status_code=400,
            detail="Starting point and destination are required."
        )

    return {
        "start": route.start,
        "destination": route.destination,
        "message": "Route request received successfully."
    }


@app.post("/add-obstacle")
def add_obstacle(obstacle: Obstacle):
    new_obstacle = {
        "id": len(obstacles) + 1,
        "latitude": obstacle.latitude,
        "longitude": obstacle.longitude,
        "description": obstacle.description,
        "time": datetime.now().isoformat()
    }

    obstacles.append(new_obstacle)

    return {
        "message": "Obstacle added successfully.",
        "obstacle": new_obstacle
    }


@app.get("/obstacles")
def get_obstacles():
    return {
        "total": len(obstacles),
        "obstacles": obstacles
    }


@app.get("/ambulance-alert")
def ambulance_alert():
    return {
        "alert": "Ambulance approaching!",
        "message": "Please give way to the ambulance."
    }


# Activate a new ambulance alert from the operator panel
@app.post("/activate-alert")
async def activate_alert(request: AlertRequest):
    global current_alert

    if not request.road_or_area.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter the road or area."
        )

    current_alert = {
        "alert": "🚑 AMBULANCE APPROACHING!",
        "message": (
            f"An ambulance is approaching {request.road_or_area}. "
            "Please give way and keep the lane clear."
        ),
        "road_or_area": request.road_or_area,
        "time": datetime.now().isoformat()
    }

    await manager.broadcast({
        "type": "ambulance_alert",
        "data": current_alert
    })

    return {
        "status": "success",
        "message": "Ambulance alert sent.",
        "connected_users": len(manager.active_connections),
        "alert": current_alert
    }


# Allow users to receive live alerts
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        # Send the latest alert to a newly connected user.
        if current_alert:
            await websocket.send_json({
                "type": "ambulance_alert",
                "data": current_alert
            })

        while True:
            # Keep the connection alive.
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/current-alert")
def get_current_alert():
    return {
        "alert": current_alert
    }
