from typing import List, Dict, Tuple
import random, time
from agari_judge import AgariJudger

WAITING, RUNNING, RECONNECT, ENDED = 0, 1, 2, 3
default_rules = {
    "initial_point" : 150_000,
    "sort_hand" : False,
    "yaku_rules": {
        "has_daisharin" : False, 
        "renhou_as_yakuman" : False,
    }
}


class ChinitsuPlayer:
    def __init__(self, name, initial_point: int, active=True) -> None:
        self.name = name
        self.active = active
        self.point = initial_point
        
        self.reset_game()
    
    def reset_game(self):
        self.is_oya = False
        self.is_riichi = False
        # last card of hand is tsumo card (only after drawing a card)
        self.hand: List[str] = []
        self.fuuro: List[Tuple[str]] = []
        self.kawa = []
        self.num_kang = 0
    
    @property
    def len_hand(self):
        return len(self.hand)
    
    def draw(self, cards):
        self.hand.extend(cards)

    def discard(self, idx) -> str:
        if idx > 13 - self.num_kang * 3:
            raise IndexError(idx)
        
        card = self.hand.pop(idx)
        self.kawa.append(card)
        
        return card
    
    def get_info(self):
        info = {
            "is_oya": self.is_oya,
            "hand" : self.hand,
        }
        return info
    


class ChinitsuGame:
    def __init__(self, rules: Dict={}) -> None:
        self._players: Dict[str, ChinitsuPlayer] = {}
        self.status = WAITING
        self.yama : List[str] = []
        self.current_player: str = None
        self.kyoutaku_number = 0
        self.tsumi_number = 0
        
        self.set_rules(rules)
    
    def set_rules(self, rules: dict):
        if not rules:
            self.rules = default_rules
        self.agari_judger = AgariJudger(self.rules['yaku_rules'])
    
    @property
    def player_ids(self):
        return list(self._players.keys())
    
    
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
    
    def draw_from_yama(self, player_name, cnt=1):
        if cnt > len(self.yama):
            raise ValueError(f"Too few cards to draw! {cnt} > {len(self.yama)}")
        cards = self.yama[:cnt]
        self._players[player_name].draw(cards)
        self.yama = self.yama[cnt:]
        return cards
    
    def next_turn(self):
        i = self.player_ids.index(self.current_player)
        self.current_player = self.player_ids[1 - i]
    
    def start_game(self):
        # randomize the yama and draw cards
        self.yama = ([f"{i}s" for i in range(1, 9+1)] * 4)[:]
        random.seed(time.time())
        random.shuffle(self.yama)
        
        for _, p in self._players.items():
            p.reset()
        # set oyabann (dealer)
        idx = random.randint(0, 1)
        
        
        oya = self.player_ids[idx]
        ko  = self.player_ids[1 - idx]
        self._players[oya].is_oya = True
        self._players[ko].is_oya = False
        
        # simulate drawing cards just for fun :)
        for _ in range(3):
            self.draw_from_yama(oya, 4)
            self.draw_from_yama(ko, 4)
        self.draw_from_yama(oya, 2)
        self.draw_from_yama(ko, 1)
        
        self.current_player = oya
        
        
    
    def add_player(self, player_name: str):
        if len(self._players) >= 2:
            raise AssertionError(f"Too many Players ({len(self._players)})!")
        if player_name in self._players:
            raise ValueError(f"{player_name} exists!")
        self._players[player_name] = ChinitsuPlayer(player_name)
        
    def activate_player(self, player_name):
        if player_name not in self._players:
            raise ValueError(player_name)
        self._players[player_name].active = True
                    
    def deactivate_player(self, player_name):
        if player_name not in self._players:
            raise ValueError(player_name)
        self._players[player_name].active = False
        
    def remove_player(self, player_name: str):
        if self.is_running or self.is_reconnecting:
            raise AssertionError("Cannot remove player in game!")
        if player_name not in self._players:
            raise ValueError(player_name)
        self._players.pop(player_name)
    
    
    def input(self, action: str, card_idx: int, player_id: str) -> bool:
        
        # public info to be retured to every connection
        public_info = {
            "player_id": player_id,
            "action" : action,
            "card_idx" : -1,         # index of card played or drawn, depending on action
            "played_card" : None,
            "fuuro" : {
                name: p.fuuro for name, p in self._players.items()
            },
            "kawa" : {
                name: p.kawa for name, p in self._players.items()
            },
        }
        
    
        # start the game
        if action == "start":
            if len(self._players) == 2:
                self.start_game()
                res = {player_id: {"message": "ok"}}
                for name, p in self._players.items():
                    if name not in res:
                        res[name] = {}
                    res[name]["hand"] = p.hand
                    res[name]["is_oya"] = p.is_oya
                
            else:
                res = {player_id: {"message": "not_enough_players"}}
                return res
        
        # check if action turn is legal
        if action in ["discard", "draw", "tsumo", "riichi", "kang"] and self.current_player != player_id:
            res = {player_id: {"message": "not_your_turn"}}
            return res
        if action in ["ron", "skip"] and self.current_player == player_id:
            res = {player_id: {"message": "not_opponent_turn"}}
            return res
        
        if action == "discard":
            try:
                card = self._players[player_id].discard(card_idx)
                public_info["card_idx"] = card_idx
                public_info["played_card"] = card
                res = {player_id: {"message": "ok"}}
            except IndexError as e:
                res = {player_id: {"message": f"card_index_out_of_range. {e}"}}
                return res
        
        if action == "draw":
            try:
                cards = self.draw_from_yama(player_id)
                public_info["card_idx"] = self._players[player_id].len_hand
                if player_id not in res:
                    res[player_id] = {}
                res[player_id]["hand"] = self._players[player_id].hand
            except ValueError as e:
                res = {player_id: {"message": f"card_index_out_of_range. {e}"}}
                return res
        
        if action == "tsumo":
            p = self._players[player_id]
            # TODO: complete all the special riichi and tsumo cases
            agari_condition = {
                "is_tsumo" : True,
                "is_riichi": p.is_riichi,
                "is_ippatsu": False,
                "is_rinshan": False,
                "is_haitei": False,
                "is_houtei": False,
                "is_daburu_riichi": False,
                "is_tenhou": False,
                "is_renhou": False,
                "is_chiihou": False,
                "is_open_riichi": False,
                "kyoutaku_number": 0,
                "tsumi_number": 0
            }
            
            result = self.agari_judger.judge(p.hand, p.fuuro, p.hand[-1], **agari_condition)
        
        # skip opponent turn (not ron)    
        if action == "skip":
            self.next_turn()
            res = {player_id: {"message": "ok"}}
        
        
        
        # add public info to result
        for p_id in self.player_ids:
            if p_id not in res:
                res[p_id] = {}
            for k, v in public_info.items():
                res[p_id][k] = v
        
        return res