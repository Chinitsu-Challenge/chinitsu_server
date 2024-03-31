from typing import List, Dict, Tuple
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.meld import Meld
from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
from mahjong.shanten import Shanten
from mahjong.tile import TilesConverter
from mahjong.hand_calculating.hand_response import HandResponse

# useful helper
def print_hand_result(hand_result):
    print(hand_result.han, hand_result.fu)
    print(hand_result.cost['main'])
    print(hand_result.yaku)
    for fu_item in hand_result.fu_details:
        print(fu_item)
    print('')


calculator = HandCalculator()

class AgariJudger():    
    def __init__(self, has_daisharin=False, renhou_as_yakuman=False, ) -> None:
        self.calculator = HandCalculator()
        self.options = OptionalRules(has_open_tanyao=False,
                                     has_aka_dora=False,
                                     has_double_yakuman=True,
                                     has_daisharin=has_daisharin,
                                     has_daisharin_other_suits=has_daisharin,
                                     renhou_as_yakuman=renhou_as_yakuman,
                                     )
    
    
    def judge(self, hand: List[str], 
              fuuro: List[Tuple[str]], 
              win_card: str, 
              is_tsumo=False,
              is_riichi=False,
              is_ippatsu=False,
              is_rinshan=False,
              is_haitei=False,
              is_houtei=False,
              is_daburu_riichi=False,
              is_tenhou=False,
              is_renhou=False,
              is_chiihou=False,
              is_open_riichi=False,
              kyoutaku_number=0,
              tsumi_number=0) -> HandResponse:
        hand_souzi_str = ''.join(sorted([s.strip('s') for s in hand]))
        tiles = TilesConverter.string_to_136_array(sou=hand_souzi_str)
        win_tile = TilesConverter.string_to_136_array(sou=win_card.strip('s'))[0]
        result: HandResponse = calculator.estimate_hand_value(tiles, 
                                                              win_tile, 
                                                              config=HandConfig(options=self.options,
                                                                                is_tsumo=is_tsumo,
                                                                                is_riichi=is_riichi,
                                                                                is_ippatsu=is_ippatsu,
                                                                                is_rinshan=is_rinshan,
                                                                                is_haitei=is_haitei,
                                                                                is_houtei=is_houtei,
                                                                                is_daburu_riichi=is_daburu_riichi,
                                                                                is_tenhou=is_tenhou,
                                                                                is_renhou=is_renhou,
                                                                                is_chiihou=is_chiihou,
                                                                                is_open_riichi=is_open_riichi,
                                                                                kyoutaku_number=kyoutaku_number,
                                                                                tsumi_number=tsumi_number)
                                                            )
        return result
        