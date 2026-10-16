import matplotlib.pyplot as plt

VALID_PIECE = None

class Chessboard:
    def __init__(self):
        self.size = 8

    def draw(self):
        fig, ax = plt.subplots()
        for i in range(self.size):
            for j in range(self.size):
                color = 'white' if (i + j) % 2 == 0 else 'black'
                rect = plt.Rectangle((i, j), 1, 1, facecolor=color)
                ax.add_patch(rect)
        ax.set_xlim(0, self.size)
        ax.set_ylim(0, self.size)
        ax.set_aspect('equal')
        plt.show()

    @staticmethod
    def parse_move(move:str):
        if len(move) == 2: # Pawn
            return move[0], move[1]
        

    def add_2_board(self,move:str):
        return self.parse_move(move)



if __name__ == "__main__":
    board = Chessboard()
    board.draw()
    board.parse_move("e4")