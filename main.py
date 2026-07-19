import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import Game

if __name__ == '__main__':
    Game().run()
