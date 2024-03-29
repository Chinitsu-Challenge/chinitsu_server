from typing import List, Dict
import random, time

WAITING, RUNNING, RECONNECT, ENDED = 0, 1, 2, 3

class ChinnitsuPlayer:
    def __init__(self, name, active=True) -> None:
        self.name = name
        self.active = active
        self.is_oya = False
        self.hand = []
    
    def draw(self, cards):
        self.hand.extend(cards)
        
class ChinnitsuGame:
    def __init__(self) -> None:
        self._players: List[ChinnitsuPlayer] = []
        self.status = WAITING
        self.yama : List[int] = []
    
    @property
    def player_ids(self):
        return [p.name for p in self._players]
    
    @property
    def is_waiting(self):
        return self.status == WAITING
    @property
    def is_running(self):
        return self.status == RUNNING
    @property
    def is_reconnecting(self):
        return self.status == RECONNECT
    @property
    def is_ended(self):
        return self.status == ENDED
    
    def set_waiting(self):
        self.status = WAITING
    def set_running(self):
        self.status = RUNNING
    def set_reconnecting(self):
        self.status = RECONNECT
    def set_ended(self):
        self.status = ENDED
    
    def draw_from_yama(self, player_idx, cnt=1):
        if cnt > len(self.yama):
            raise ValueError(f"Too few cards to draw! {cnt} > {len(self.yama)}")
        cards = self.yama[:cnt]
        self._players[player_idx].draw(cards)
        self.yama = self.yama[cnt:]
    
    def start_game(self):
        # randomize the yama and draw cards
        self.yama = ([i for i in range(1, 9+1)] * 4)[:]
        random.seed(time.time())
        random.shuffle(self.yama)
        
        # set oyabann (dealer)
        oya = random.randint(0, 1)
        ko  = 1 - oya
        self._players[oya].is_oya = True
        self._players[ko].is_oya = False
        
        # simulate drawing cards just for fun :)
        for _ in range(3):
            self.draw_from_yama(oya, 4)
            self.draw_from_yama(ko, 4)
        self.draw_from_yama(oya, 2)
        self.draw_from_yama(ko, 1)
        
        
    
    def add_player(self, player_name: str):
        if len(self._players) >= 2:
            raise AssertionError(f"Too many Players ({len(self._players)})!")
        self._players.append(ChinnitsuPlayer(player_name))
        
    def activate_player(self, player_name):
        found = False
        for i in [0, 1]:
            if self._players[i].name == player_name:
                self._players[i].active = True
                found = True
        if not found:
            raise ValueError(f"{player_name} not found!")
                
    def deactivate_player(self, player_name):
        found = False
        for i in [0, 1]:
            if self._players[i].name == player_name:
                self._players[i].active = False
                found = True
        if not found:
            raise ValueError(f"{player_name} not found!")
        
    def remove_player(self, player_name: str):
        if self.is_running or self.is_reconnecting:
            raise AssertionError("Cannot remove player in game!")
        self._players.remove(player_name)
    
    
    def input(self, message: str, player_id: str) -> bool:
        if  "start" in message:
            self.start_game()
            
            res = {p.name: p.hand for p in self._players}
            
            return res