
import random

debug_cards = {
    114514 : ("11123455678999", "1112224567899")
}

# ref: reverse this process
# for _ in range(3):
#     self.draw_from_yama(oya, 4)
#     self.draw_from_yama(ko, 4)
#         self.draw_from_yama(oya, 2)
#         self.draw_from_yama(ko, 1)

def insert_into_yama(yama: list, hand: list, cnt: int):
    for _ in range(cnt):
        yama.insert(0, hand.pop()) # slow but so what
def debug_yama(debug_code: int):
    """
    Use debug code to create cheat yama that gives designed hands for players.
    """
    yama = []
    oya_hand,  ko_hand = [c + 's' for c in list(debug_cards[debug_code][0])], [c + 's' for c in list(debug_cards[debug_code][1])]
    
    insert_into_yama(yama, ko_hand, 1)
    insert_into_yama(yama, oya_hand, 2)
    for _ in range(3):
        insert_into_yama(yama, ko_hand, 4)
        insert_into_yama(yama, oya_hand, 4)
    
    for _ in range(4*9-14-13):
        x = random.randint(1,9)
        yama.append(f"{x}s")

    return yama
    
    
if __name__ == "__main__":
    print(debug_yama(114514))
    