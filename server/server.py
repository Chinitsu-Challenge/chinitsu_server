from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict
from game import ChinnitsuGame

app = FastAPI()

class GameManager:
    def __init__(self) -> None:
        self.games = dict()

    def init_game(self, room_name):
        if room_name not in self.games:
            self.games[room_name] = ChinnitsuGame()
            return True
        return False  # Game already started

    def end_game(self, room_name):
        if room_name in self.games:
            del self.games[room_name]

    def get_game(self, room_name) -> ChinnitsuGame:
        return self.games.get(room_name, None)


class ConnectionManager:
    def __init__(self, game_manager: GameManager):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_owner : Dict[WebSocket, str] = {}
        self.game_manager = game_manager

    async def connect(self, websocket: WebSocket, room_name: str, player_id: str):
        if room_name in self.active_connections:
            if len(self.active_connections[room_name]) >= 2:
                await websocket.close(code=1003, reason="Room full")  # Room full
                return False
            cur_game = self.game_manager.get_game(room_name)
            if player_id in cur_game.player_ids and not cur_game.is_reconnecting:  # same id but not reconnecting, so duplicate id.
                await websocket.close(code=1000, reason="Duplicate ID")  # Room full
                return False
            
        await websocket.accept()
        if room_name not in self.active_connections:
            self.active_connections[room_name] = []
        self.active_connections[room_name].append(websocket)
        self.connection_owner[websocket] = player_id
        
        # Initialize game for the first player (host)
        if len(self.active_connections[room_name]) == 1:
            self.game_manager.init_game(room_name)
            self.game_manager.get_game(room_name).add_player(player_id)
            await self.broadcast(f"Game started in room {room_name}! Host is {player_id}", room_name)
        # second player (new or rejoin)   
        elif len(self.active_connections[room_name]) == 2:   
            cur_game = self.game_manager.get_game(room_name)
            if cur_game.is_reconnecting:
                cur_game.activate_player(player_id)
                await self.broadcast(f"{player_id} rejoins {room_name}.", room_name)
            else:
                cur_game.add_player(player_id)
                cur_game.set_running()
                await self.broadcast(f"{player_id} joins {room_name}. Game START!", room_name)
                
        
        return True

    def disconnect(self, websocket: WebSocket, room_name: str, player_id: str):
        if room_name in self.active_connections:
            self.active_connections[room_name].remove(websocket)
            cur_game = self.game_manager.get_game(room_name)
            if cur_game.is_running:
                cur_game.deactivate_player(player_id)
                cur_game.set_reconnecting()
            elif cur_game.is_waiting or cur_game.is_ended:
                cur_game.remove_player(player_id)
            
            
            if len(self.active_connections[room_name]) == 0:
                self.game_manager.end_game(room_name)
                del self.active_connections[room_name]
                
            self.connection_owner[websocket] = None
                

    async def broadcast(self, message: str, room_name: str):
        """
        Send to everyone in room_name
        """
        if room_name not in self.active_connections:
            return 
        for connection in self.active_connections[room_name]:
            await connection.send_text(message)
            
    async def send_to(self, message: str, room_name: str, player_id: str):
        """
        Send to some specific player_id in room_name
        """
        if room_name not in self.active_connections:
            return 
        for connection in self.active_connections[room_name]:
            if self.connection_owner[connection] == player_id:
                await connection.send_text(message)
    
    async def game_action(self, message: str, room_name: str, player_id: str):
        if room_name not in self.active_connections:
            return
        cur_game = self.game_manager.get_game(room_name)
        result = cur_game.input(message, player_id)
        
        for connection in self.active_connections[room_name]:
            await self.send_to(str(result[player_id]), room_name, self.connection_owner[connection] )
        
                
game_manager = GameManager()
manager = ConnectionManager(game_manager)


@app.websocket("/ws/{room_name}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, player_id: str):
    await manager.connect(websocket, room_name, player_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"{player_id}: {data}", room_name)
            await manager.game_action(f"{player_id}: {data}", room_name, player_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name, player_id)
        await manager.broadcast(f"{player_id} left the room {room_name}", room_name)
