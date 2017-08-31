from python_cowbull_game.GameObject import GameObject as BaseGameObject


class GameObject(BaseGameObject):
    game_modes = ["easy", "normal", "hard", "tough"]

    digits_used = {
        'easy': 3,
        'normal': 4,
        'hard': 6,
        'tough': 10
    }

    guesses_allowed = {
        'easy': 15,
        'normal': 10,
        'hard': 6,
        'tough': 10
    }

    def __init__(self):
        super(GameObject, self).__init__()