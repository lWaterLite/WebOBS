from enum import Enum


class Foreground(Enum):
    DEFAULT = ''
    BLACK = '30'
    RED = '31'
    GREEN = '32'
    YELLOW = '33'
    BLUE = '34'
    PURPLE = '35'
    CYAN = '36'
    WHITE = '37'


class Background(Enum):
    DEFAULT = ''
    BLACK = '40'
    RED = '41'
    GREEN = '42'
    YELLOW = '43'
    BLUE = '44'
    PURPLE = '45'
    CYAN = '46'
    WHITE = '47'


class Display(Enum):
    DEFAULT = '0'
    HIGHLIGHT = '1'
    UNDERLINE = '4'


def logger(string: str, display: Display = Display.DEFAULT,
           foreground: Foreground = Foreground.DEFAULT,
           background: Background = Background.DEFAULT) -> str:
    display = '\033[' + display.value + 'm'
    foreground = '\033[' + foreground.value + 'm' if foreground is not Foreground.DEFAULT else Foreground.DEFAULT.value
    background = '\033[' + background.value + 'm' if background is not Background.DEFAULT else Background.DEFAULT.value
    return display + foreground + background + string + '\033[0m'
