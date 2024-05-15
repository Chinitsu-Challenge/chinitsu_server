from typing import List, Dict, Tuple
import random, time, logging
from agari_judge import AgariJudger
from debug_setting import debug_yama
logger = logging.getLogger("uvicorn")

WAITING, RUNNING, RECONNECT, ENDED = 0, 1, 2, 3
default_rules = {
    "initial_point" : 150_000,
    "no_agari_punishment": 20_000,
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
        self.is_daburu_riichi = False
        self.riichi_turn = None
        self.is_ippatsu = False
        self.is_rinshan = False
        self.is_furiten = False
        
        # last card of hand is tsumo card (only after drawing a card)
        self.hand: List[str] = []
        self.fuuro: List[Tuple[str]] = []
        self.kawa: List[Tuple[str, bool]]= []
        self.num_kan = 0
    
    @property
    def len_hand(self):
        return len(self.hand)
    
    @property
    def num_fuuro(self):
        return len(self.fuuro)
    
    def draw(self, cards, is_rinshan=False):
        self.hand.extend(cards)
        self.is_rinshan = is_rinshan  # set rinshan state for rinshan tsumo

    def discard(self, idx, is_riichi: bool) -> str:
        if idx > 13 - self.num_kan * 3:
            raise IndexError(idx)
        
        card = self.hand.pop(idx)
        self.kawa.append((card, is_riichi))

        if is_riichi:
            self.is_ippatsu = True
        else:
            self.is_ippatsu = False
        
        return card
    
    def kan(self, kan_card: str) -> bool:
        if self.hand.count(kan_card) != 4 or len(self.hand) < 5:
            return False
        self.hand = [card for card in self.hand if card != kan_card]
        self.fuuro.append((kan_card, kan_card, kan_card, kan_card))
        return True
            
    def get_info(self):
        info = {
            "is_oya": self.is_oya,
            "hand" : self.hand,
        }
        return info
    
class TurnState:
    BEFORE_DRAW = 1
    AFTER_DRAW = 2
    AFTER_DISCARD = 3
    def __init__(self, player_ids: List[str]) -> None:
        assert len(player_ids) == 2
        self.player_ids = player_ids
        self.current_player: str = None
        self.turn = 1
        self.stage: str = self.BEFORE_DRAW
    
    def __str__(self):
        return f"{self.turn}: {self.current_player} - {self.stage}"
    
    def next(self):
        if self.stage == self.BEFORE_DRAW:
            self.stage = self.AFTER_DRAW
        elif self.stage == self.AFTER_DRAW:
            self.stage = self.AFTER_DISCARD
        elif self.stage == self.AFTER_DISCARD:
            self.stage = self.BEFORE_DRAW
            self.current_player = self.player_ids[1 - self.player_ids.index(self.current_player)]
            self.turn += 1
    
    @property
    def is_before_draw(self):
        return self.stage == self.BEFORE_DRAW
    @property
    def is_after_draw(self):
        return self.stage == self.AFTER_DRAW
    @property
    def is_after_discard(self):
        return self.stage == self.AFTER_DISCARD
    

class ChinitsuGame:
    def __init__(self, rules: Dict={}) -> None:
        self._players: Dict[str, ChinitsuPlayer] = {}
        self.status = WAITING
        self.yama : List[str] = []

        self.kyoutaku_number = 0
        self.tsumi_number = 0
        
        self.set_rules(rules)
    
    def set_rules(self, rules: dict):
        
        self.rules = default_rules
        if rules is not None:
            self.rules.update(rules)
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
    
    def draw_from_yama(self, player_name, cnt=1) -> List[str]:
        if cnt > len(self.yama):
            raise ValueError(f"Too few cards to draw! {cnt} > {len(self.yama)}")
        cards = self.yama[:cnt]
        self._players[player_name].draw(cards)
        self.yama = self.yama[cnt:]
        return cards
    
    def draw_from_rinshan(self, player_name) -> List[str]:
        if len(self.yama) <= 0:
            raise ValueError(f"Too few cards to draw! {len(self.yama)}")

        cards = self.yama[-1]
        self._players[player_name].draw(cards)
        self.yama = self.yama[:-1]
        return cards
        
    def _other_player(self, player_name):
        return self.player_ids[1 - self.player_ids.index(player_name)]
    
    def start_new_game(self, debug_code=None):
        # randomly set oyabann (dealer)
        idx = random.randint(0, 1)
        oya = self.player_ids[idx]
        self.start_game(oya, debug_code)
    
    def start_game(self, oya: str, debug_code=None):
        
        if len(self._players) != 2:
            raise ValueError(f"Too few or too many players! {self.player_ids}")
        self.state = TurnState(self.player_ids)
        self.state.current_player = oya
        
        # randomize the yama and draw cards
        random.seed(time.time())
        if not debug_code:
            self.yama = ([f"{i}s" for i in range(1, 9+1)] * 4)[:]
            random.shuffle(self.yama)
        else:   # debug mode
            self.yama = debug_yama(debug_code)
        
        
        for _, p in self._players.items():
            p.reset_game()
            
        ko  = self.player_ids[1 - self.player_ids.index(oya)]
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
        if player_name in self._players:
            raise ValueError(f"{player_name} exists!")
        self._players[player_name] = ChinitsuPlayer(player_name, initial_point=self.rules['initial_point'])
        
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
            "card_idx" : None,         # index of card played or drawn, depending on action
            "card" : None,
            "fuuro" : {
                name: p.fuuro for name, p in self._players.items()
            },
            "kawa" : {
                name: p.kawa for name, p in self._players.items()
            },
        }
        
         # start the game
        if action == "start":
            debug_code = card_idx if card_idx and card_idx > 100 else None
            if debug_code:
                logger.warn(f'Debug code: {debug_code}')   
            if len(self._players) == 2:
                self.start_new_game(debug_code=debug_code)
                self.state.next() # oya does not need to draw, set to after_draw
                res = {player_id: {"message": "ok"}}
                for name, p in self._players.items():
                    if name not in res:
                        res[name] = {}
                    res[name]["hand"] = p.hand
                    res[name]["is_oya"] = p.is_oya
                
            else:
                res = {player_id: {"message": "not_enough_players"}}
                return res
        
        p   = self._players[player_id]
        opp = self._players[self._other_player(player_id)]
        is_tenchii_tenpai = (self.state.turn in [1, 2] and all([p.num_kan == 0 for _, p in self._players.items()]))
        
       
        
        # check if action turn is legal
        if action in ["discard", "draw", "tsumo", "riichi", "kan"] and self.state.current_player != player_id:
            res = {player_id: {"message": "not_your_turn"}}
            return res
        if action in ["ron", "skip_ron"] and self.state.current_player == player_id:
            res = {player_id: {"message": "not_opponent_turn"}}
            return res
        if action in ["discard", "riichi", "kan"] and (card_idx is None or not (0 <= card_idx < 14 - self._players[player_id].num_kan)):
            res = {player_id: {"message": "card_index_error"}}
            return res
        
        
        if action == "draw":
            if p.is_oya and self.state.turn == 1 or not self.state.is_before_draw:  # oya does not draw in first turn; can't draw twice
                res = {player_id: {"message": "illegal_draw"}}
                logger.debug(str(self.state))
                return res
            try:
                cards = self.draw_from_yama(player_id)
                public_info["card_idx"] = p.len_hand
                res = {player_id: {"hand": p.hand}}
                self.state.next()
            except ValueError as e:
                res = {player_id: {"message": f"card_index_out_of_range. {e}"}}
                return res
            
        
        if action == "kan":
            if not self.state.is_after_draw:
                res = {player_id: {"message": "illegal_kan"}}
                return res
            kan_card = p.hand[card_idx]
            if not p.kan(kan_card):
                res = {player_id: {"message": f"too_few_cards_to_kan. {e}"}}
                return res
            public_info["card_idx"] = card_idx
            public_info["card"] = card
            
            rinshan_card = self.draw_from_rinshan(player_id)
            # cancel ippatsu of all players after kan
            for _, p in self._players.items():
                p.is_ippatsu = False
            
            res = {player_id: {"message": "ok", "hand": p.hand}}
            
        
        if action == "discard":
            if not self.state.is_after_draw:
                res = {player_id: {"message": "illegal_discard"}}
                
                return res
            try:
                card = p.discard(card_idx, is_riichi=False)
                public_info["card_idx"] = card_idx
                public_info["card"] = card
                res = {player_id: {"message": "ok"}}
                self.state.next()
            except IndexError as e:
                res = {player_id: {"message": f"card_index_out_of_range. {e}"}}
                return res
        
        if action == "riichi":
            if not self.state.is_after_draw:
                res = {player_id: {"message": "illegal_riichi"}}
                return res
            if p.is_riichi:
                res = {player_id: {"message": f"cannot_riichi_twice"}}
                return res
            try:
                card = p.discard(card_idx, is_riichi=True)
                p.is_riichi = True
                if is_tenchii_tenpai:
                    p.is_daburu_riichi = True
                p.riichi_turn = self.turn
                
                public_info["card_idx"] = card_idx
                public_info["card"] = card
                res = {player_id: {"message": "ok"}}
                self.state.next()
            except IndexError as e:
                res = {player_id: {"message": f"card_index_out_of_range. {e}"}}
                return res
        
        if action == "tsumo":
            if not self.state.is_after_draw:
                res = {player_id: {"message": "illegal_tsumo"}}
                return res
            if p.len_hand + p.num_fuuro * 4 != 14:
                res = {player_id: {"message": f"incorrect_card_count"}}
                return res
            
            agari_condition = {
                "is_tsumo" : True,
                "is_riichi": p.is_riichi,
                "is_ippatsu": p.is_ippatsu,
                "is_rinshan": p.is_rinshan,
                "is_haitei": (len(self.yama) == 0),
                "is_houtei": False,
                "is_daburu_riichi": (p.is_riichi and p.is_daburu_riichi),
                "is_tenhou": (p.is_oya and is_tenchii_tenpai),
                "is_renhou": False,
                "is_chiihou": ((not p.is_oya) and is_tenchii_tenpai),
                "is_open_riichi": False,
                "is_oya": p.is_oya,
                "kyoutaku_number": self.kyoutaku_number,
                "tsumi_number": self.tsumi_number,
                
            }
            
            agari = self.agari_judger.judge(p.hand, p.fuuro, p.hand[-1], **agari_condition)
            is_agari = (agari.han is not None and agari.han > 0)
            res = {player_id: {"message": "ok"}}
            if is_agari: 
                public_info.update({
                    "agari": True,
                    "han": agari.han,
                    "fu": agari.fu,
                    "point": agari.cost,
                    "yaku": agari.yaku
                })
            else:
                public_info.update({
                    "agari": False,
                    "han": 0,
                    "fu": 0,
                    "point": -self.rules['no_agari_punishment'],
                    "yaku": None
                })
                
        
        if action == 'ron':
            if not self.state.is_after_discard:
                res = {player_id: {"message": "illegal_ron"}}
                return res
            if p.len_hand + p.num_fuuro * 4 != 13:
                res = {player_id: {"message": f"incorrect_card_count"}}
                return res
            
            agari_condition = {
                "is_tsumo" : False,
                "is_riichi": p.is_riichi,
                "is_ippatsu": p.is_ippatsu,
                "is_rinshan": False,
                "is_haitei": False,
                "is_houtei": (len(self.yama) == 0),
                "is_daburu_riichi": (p.is_riichi and p.is_daburu_riichi),
                "is_tenhou": False,
                "is_renhou": is_tenchii_tenpai,
                "is_chiihou": False,
                "is_open_riichi": False,
                "is_oya": p.is_oya,
                "kyoutaku_number": self.kyoutaku_number,
                "tsumi_number": self.tsumi_number,
                
            }
            
            agari = self.agari_judger.judge(p.hand, p.fuuro, opp.kawa[-1][0], **agari_condition)
            is_agari = (agari.han is not None and agari.han > 0)
            res = {player_id: {"message": "ok"}}
            if is_agari: 
                public_info.update({
                    "agari": True,
                    "han": agari.han,
                    "fu": agari.fu,
                    "point": agari.cost,
                    "yaku": agari.yaku
                })
            else:
                public_info.update({
                    "agari": False,
                    "han": 0,
                    "fu": 0,
                    "point": -self.rules['no_agari_punishment'],
                    "yaku": None
                })
        
        # skip opponent turn (not ron)    
        if action == "skip_ron":
            if not self.state.is_after_discard:
                res = {player_id: {"message": "illegal_skip_ron"}}
                return res
            
            # opponent should give 1000 point kyoutaku if opponent just riichi'ed
            if opp.kawa[-1][1]: 
                opp.point -= 1000
                self.kyoutaku_number += 1
            
            #TODO: set riichi furiten
            if p.is_riichi:
                pass
            res = {player_id: {"message": "ok"}}
            self.state.next()
    
        # add public info to result
        for p_id in self.player_ids:
            if p_id not in res:
                res[p_id] = {}
            res[p_id].update(public_info)
        
        return res