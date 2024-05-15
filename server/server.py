import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict
from game import ChinitsuGame

app = FastAPI()
logger = logging.getLogger("uvicorn")
# logger.warn("Game Logger Active")

class GameManager:
    def __init__(self) -> None:
        self.games = dict()

    def init_game(self, room_name):
        if room_name not in self.games:
            self.games[room_name] = ChinitsuGame()
            return True
        return False  # Game already started

    def end_game(self, room_name):
        if room_name in self.games:
            del self.games[room_name]

    def get_game(self, room_name) -> ChinitsuGame:
        return self.games.get(room_name, None)


class ConnectionManager:
    def __init__(self, game_manager: GameManager):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_owner : Dict[WebSocket, str] = {}
        self.game_manager = game_manager

    async def connect(self, websocket: WebSocket, room_name: str, player_id: str):
        if room_name in self.active_connections:
            if len(self.active_connections[room_name]) >= 2:
                err_msg = "room_full"
                await websocket.accept()
                await websocket.close(code=1003, reason=err_msg)  # Room full
                return False
            cur_game = self.game_manager.get_game(room_name)
            if player_id in cur_game.player_ids and not cur_game.is_reconnecting:  # same id but not reconnecting, so duplicate id.   
                err_msg = "duplicate_id"
                await websocket.accept()
                await websocket.close(code=1003, reason=err_msg)
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
        logger.info(f"Disconnected: {room_name} {player_id}")
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
            await connection.send_json({"broadcast":True, "message": message})
            
    async def send_text_to(self, message: str, room_name: str, player_id: str):
        """
        Send text to some specific player_id in room_name
        """
        logger.info(f"{room_name} - {player_id} -> {message} ")
        if room_name not in self.active_connections:
            return 
        for connection in self.active_connections[room_name]:
            if self.connection_owner[connection] == player_id:
                await connection.send_text(message)
    
    async def send_dict_to(self, info: dict, room_name: str, player_id: str):
        """
        Send dict to some specific player_id in room_name
        """
        info["broadcast"] = False
        logger.info(f"{room_name} - {player_id} -> {info} ")
        if room_name not in self.active_connections:
            return 
        for connection in self.active_connections[room_name]:
            if self.connection_owner[connection] == player_id:
                await connection.send_json(info)
    
    async def game_action(self, info: dict, room_name: str, player_id: str):
        
        if room_name not in self.active_connections:
            return
        cur_game = self.game_manager.get_game(room_name)
        
        card_idx = int(info["card_idx"]) if info["card_idx"].isdigit() else None
        result = cur_game.input(info["action"], card_idx, player_id)
        if result:
            for connection in self.active_connections[room_name]:
                recv_player = self.connection_owner[connection]
                if recv_player in result:
                    await self.send_dict_to(result[recv_player], room_name, recv_player)
        
                
game_manager = GameManager()
manager = ConnectionManager(game_manager)


@app.websocket("/ws/{room_name}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, player_id: str):
    if not await manager.connect(websocket, room_name, player_id):
        return
        
    try:
        while True:
            
            data = await websocket.receive_json()
            # await manager.broadcast(f"{player_id}: {data}", room_name)
            await manager.game_action(data, room_name, player_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name, player_id)
        await manager.broadcast(f"{player_id} left the room {room_name}", room_name)
