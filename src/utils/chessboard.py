import matplotlib.pyplot as plt
import numpy as np
from Move import Move
VALID_PIECE = None

class Chessboard:
    def __init__(self):
        self.size = 8
        self.board = {
            (letter, str(number)): 0
            for letter in 'abcdefghijklmnopqrstuvwxyz'[:self.size] 
            for number in range(1, self.size + 1)
        }

    def add_2_board(self,move:str):
        return Move.parse(move)

    def count_positions(self, movesArray:list[Move]):
        """
        Given a list of moves, count the number of times each square on the board has a piece on it.
        """
        for move in movesArray:
            square = move.to_square
            if square in self.board:
                self.board[square] += 1

# Visualization for chessboard
    def draw(self):
        fig, ax = plt.subplots()
        for (letter, number), count in self.board.items():
            x = ord(letter) - ord('a')
            y = int(number) - 1
            color = 'white' if (x + y) % 2 == 0 else 'black'
            rect = plt.Rectangle((x, y), 1, 1, facecolor=color)
            ax.add_patch(rect)
        ax.set_xticks([i + 0.5 for i in range(self.size)])
        ax.set_yticks([i + 0.5 for i in range(self.size)])
        ax.set_xticklabels('abcdefghijklmnopqrstuvwxyz'[:self.size])
        ax.set_yticklabels(range(1, self.size + 1))
        ax.set_xlim(0, self.size)
        ax.set_ylim(0, self.size)
        ax.set_aspect('equal')
        plt.show()

    def draw_heatmap(self):
        fig, ax = plt.subplots()
        heatmap = np.zeros((self.size, self.size))
        for (letter, number), count in self.board.items():
            x = ord(letter) - ord('a')
            y = int(number) - 1
            heatmap[y, x] = count
        cax = ax.matshow(heatmap, cmap='hot')
        fig.colorbar(cax)
        ax.set_xticks(range(self.size))
        ax.set_yticks(range(self.size))
        ax.set_xticklabels('abcdefghijklmnopqrstuvwxyz'[:self.size])
        ax.set_yticklabels(range(1, self.size + 1))
        plt.show()
            

if __name__ == "__main__":
    moves_1 = [{'san': 'd4', 'clk': '0:03:00', 'eval': None}, {'san': 'd5', 'clk': '0:03:00', 'eval': None}, {'san': 'c4', 'clk': '0:02:59', 'eval': None}, {'san': 'c5', 'clk': '0:03:01', 'eval': None}, {'san': 'Nc3', 'clk': '0:02:56', 'eval': None}, {'san': 'e6', 'clk': '0:03:02', 'eval': None}, {'san': 'Nf3', 'clk': '0:02:55', 'eval': None}, {'san': 'Nf6', 'clk': '0:03:03', 'eval': None}, {'san': 'Bg5', 'clk': '0:02:56', 'eval': None}, {'san': 'b6', 'clk': '0:02:54', 'eval': None}, {'san': 'cxd5', 'clk': '0:02:52', 'eval': None}, {'san': 'exd5', 'clk': '0:02:51', 'eval': None}, {'san': 'Bxf6', 'clk': '0:02:46', 'eval': None}, {'san': 'Qxf6', 'clk': '0:02:51', 'eval': None}, {'san': 'Nxd5', 'clk': '0:02:46', 'eval': None}, {'san': 'Qd8', 'clk': '0:02:52', 'eval': None}, {'san': 'dxc5', 'clk': '0:02:43', 'eval': None}, {'san': 'Bb7', 'clk': '0:02:48', 'eval': None}, {'san': 'Nf6+', 'clk': '0:02:30', 'eval': None}, {'san': 'gxf6', 'clk': '0:02:46', 'eval': None}, {'san': 'Qxd8+', 'clk': '0:02:28', 'eval': None}, {'san': 'Kxd8', 'clk': '0:02:48', 'eval': None}, {'san': 'O-O-O+', 'clk': '0:02:30', 'eval': None}, {'san': 'Ke7', 'clk': '0:02:42', 'eval': None}, {'san': 'cxb6', 'clk': '0:02:25', 'eval': None}, {'san': 'axb6', 'clk': '0:02:41', 'eval': None}, {'san': 'Nd4', 'clk': '0:02:25', 'eval': None}, {'san': 'Na6', 'clk': '0:02:34', 'eval': None}, {'san': 'e4', 'clk': '0:02:22', 'eval': None}, {'san': 'Bxe4', 'clk': '0:02:27', 'eval': None}, {'san': 'Re1', 'clk': '0:02:23', 'eval': None}, {'san': 'Rc8+', 'clk': '0:02:27', 'eval': None}, {'san': 'Kd2', 'clk': '0:02:16', 'eval': None}, {'san': 'Bh6+', 'clk': '0:02:24', 'eval': None}, {'san': 'Ke2', 'clk': '0:01:49', 'eval': None}, {'san': 'Kf8', 'clk': '0:02:05', 'eval': None}, {'san': 'f3', 'clk': '0:01:45', 'eval': None}, {'san': 'Bd5', 'clk': '0:01:55', 'eval': None}, {'san': 'Rd1', 'clk': '0:01:33', 'eval': None}, {'san': 'Bc4+', 'clk': '0:01:45', 'eval': None}, {'san': 'Kf2', 'clk': '0:01:32', 'eval': None}, {'san': 'Bxf1', 'clk': '0:01:28', 'eval': None}, {'san': 'Rhxf1', 'clk': '0:01:33', 'eval': None}, {'san': 'Kg7', 'clk': '0:01:29', 'eval': None}, {'san': 'Nf5+', 'clk': '0:01:32', 'eval': None}, {'san': 'Kg6', 'clk': '0:01:30', 'eval': None}, {'san': 'Ne7+', 'clk': '0:01:33', 'eval': None}, {'san': 'Kg7', 'clk': '0:01:29', 'eval': None}, {'san': 'Nxc8', 'clk': '0:01:30', 'eval': None}, {'san': 'Rxc8', 'clk': '0:01:28', 'eval': None}, {'san': 'Rc1', 'clk': '0:01:18', 'eval': None}, {'san': 'Bxc1', 'clk': '0:01:24', 'eval': None}, {'san': 'g4', 'clk': '0:01:16', 'eval': None}, {'san': 'Bxb2', 'clk': '0:01:24', 'eval': None}, {'san': 'Kg3', 'clk': '0:01:16', 'eval': None}, {'san': 'Be5+', 'clk': '0:01:24', 'eval': None}, {'san': 'f4', 'clk': '0:01:17', 'eval': None}, {'san': 'Rc3+', 'clk': '0:01:25', 'eval': None}, {'san': 'Kh4', 'clk': '0:01:19', 'eval': None}, {'san': 'Bc7', 'clk': '0:01:21', 'eval': None}, {'san': 'f5', 'clk': '0:01:18', 'eval': None}, {'san': 'Rc2', 'clk': '0:01:20', 'eval': None}, {'san': 'h3', 'clk': '0:01:19', 'eval': None}, {'san': 'Rxa2', 'clk': '0:00:56', 'eval': None}, {'san': 'Kh5', 'clk': '0:01:18', 'eval': None}, {'san': 'Rh2', 'clk': '0:00:54', 'eval': None}, {'san': 'h4', 'clk': '0:01:18', 'eval': None}, {'san': 'Bg3', 'clk': '0:00:47', 'eval': None}, {'san': 'g5', 'clk': '0:01:11', 'eval': None}, {'san': 'Rxh4#', 'clk': '0:00:43', 'eval': None}]

    board = Chessboard()

    board.count_positions([Move.parse(move['san']) for move in moves_1])
    board.draw_heatmap()