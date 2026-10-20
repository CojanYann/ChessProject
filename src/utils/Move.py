import re

class Move():
    def __init__(self):
        self.col = ''
        self.row = ''
        self.piece = ''

        # Switch all that in a dict?
        self.capture = ''
        self.check = ''
        self.checkmate = ''
        self.castling = ''
        self.promotion = ''
        
        self.score = ''

    def __str__(self):
        return f'{self.castling}{self.piece}{self.capture}{self.col}{self.row}{self.promotion}{self.check}{self.checkmate}{self.eval}'

    @staticmethod
    def parse(move:str):
        notation = move.strip()
        result = Move()

        castling = re.fullmatch(r'(?:O-O-O|O-O|0-0-0|0-0)([+#])?', notation)
        if castling:
            result.castling = notation[:-1] if castling.group(1) else notation
            result.castling = result.castling.replace('0', 'O')
            if castling.group(1) == '+':
                result.check = '+'
            elif castling.group(1) == '#':
                result.checkmate = '#'
            return result

        # Optional origin handles pawn captures (exd5) and piece disambiguation
        # (Nbd2, R1e2); the Move model stores only the destination.
        match = re.fullmatch(
            r'(?P<piece>[KQRBN])?(?P<origin>[a-h][1-8]?|[1-8])?'
            r'(?P<capture>x)?(?P<col>[a-h])(?P<row>[1-8])'
            r'(?P<promotion>=?[QRBN])?(?P<suffix>[+#])?',
            notation,
        )
        if not match:
            raise ValueError(f'Invalid chess move notation: {move!r}')

        result.piece = match.group('piece') or ''
        result.capture = match.group('capture') or ''
        result.col = match.group('col')
        result.row = match.group('row')
        promotion = match.group('promotion') or ''
        result.promotion = promotion if promotion.startswith('=') or not promotion else f'={promotion}'
        suffix = match.group('suffix')
        if suffix == '+':
            result.check = '+'
        elif suffix == '#':
            result.checkmate = '#'

        return result
    