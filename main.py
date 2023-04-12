import asyncio
import clipboard
import plistlib
from configparser import ConfigParser
from os import path
import base64

# from pydantic import BaseModel, ValidationError, validator
import PySimpleGUI as gui

PLAY = asyncio.Event()
CLOSE = False
WORDS = []
WORDS_LENGTH = 0
WORD_INDEX = 0
PARAGRAPH_INDEX = 0
CONFIG_PATH = "./so-many-words.ini"
SMW_CONFIG = ConfigParser()
WPM = 240

# class SMWConfig(BaseModel):
#     wpm: int

#     @validator('wpm')
#     def wpm_in_range(cls, v):
#         if not 1 < v < 3000:
#             raise ValueError('must be an integer between 0 and 3000')
#         return v


# def readConfig(configData:ConfigParser) -> dict:

#     if path.exists(configPath):
#     return


# def saveConfig(configPath:str) -> dict:
#     return


def CalculateDelayFromWPM(wpm: int) -> float:
    return 60.0 / float(wpm)


async def windowRead(window: gui.Window):
    global CLOSE, PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX, SMW_CONFIG, WPM
    while True:
        await asyncio.sleep(0.01)
        event, values = window.read(0)
        if event == "__TIMEOUT__":
            continue
        if event == "Close" or event == gui.WIN_CLOSED:
            PLAY.set()
            break
        if event == "playPauseButton":
            playPause(window)
        if event == "pasteButton":
            try:
                text = clipboard.paste()
                if not text:
                    text = "Clipboard does not contain text"
                SMW_CONFIG["settings"]["text"] = str(text)
                with open(CONFIG_PATH, "w") as f:
                    SMW_CONFIG.write(f)
                WORDS, WORDS_LENGTH = textClean(text)
                WORD_INDEX = 0
                PARAGRAPH_INDEX = 0
                playPause(window, forcePlay=True)
            except Exception as e:
                text = f"Error processing pasted material: {e}"
        if event == "cursorBeginning":
            if WORD_INDEX == 0:
                PARAGRAPH_INDEX -= 1
                PARAGRAPH_INDEX = PARAGRAPH_INDEX if PARAGRAPH_INDEX > 0 else 0
            WORD_INDEX = 0
        if event == "cursorEnd":
            if WORD_INDEX == len(WORDS[PARAGRAPH_INDEX]) - 1 or WORD_INDEX == 0:
                PARAGRAPH_INDEX += 1
                WORD_INDEX = 0
                if PARAGRAPH_INDEX > len(WORDS) - 1:
                    PARAGRAPH_INDEX = len(WORDS) - 1
                    WORD_INDEX = len(WORDS[PARAGRAPH_INDEX]) - 1
            else:
                WORD_INDEX = len(WORDS[PARAGRAPH_INDEX]) - 1
        if event == "cursorPrevious":
            targetIndex = WORD_INDEX - 1
            if targetIndex < 0:
                if PARAGRAPH_INDEX == 0:
                    WORD_INDEX = 0
                else:
                    PARAGRAPH_INDEX -= 1
                    WORD_INDEX = len(WORDS[PARAGRAPH_INDEX]) - 1
            else:
                WORD_INDEX = targetIndex
        if event == "cursorNext":
            targetIndex = WORD_INDEX + 1
            if targetIndex > len(WORDS[PARAGRAPH_INDEX]) - 1:
                if PARAGRAPH_INDEX != len(WORDS) - 1:
                    PARAGRAPH_INDEX += 1
                    WORD_INDEX = 0
            else:
                WORD_INDEX = targetIndex
        if event.startswith("cursor"):
            playPause(window, forcePause=True)
            updateWord(window)
        if event == "wpmAdd":
            WPM += 20
        if event == "wpmSubtract":
            WPM -= 20
        if event.startswith("wpm"):
            window["wpm"].update(f"{WPM} wpm")
            SMW_CONFIG["settings"]["wpm"] = str(WPM)
            with open(CONFIG_PATH, "w") as f:
                SMW_CONFIG.write(f)

    CLOSE = True
    window.close()
    return


async def wordHandler(window: gui.Window) -> None:
    global PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX, WPM
    while True:
        if CLOSE:
            break
        await wordAdvance(WPM)
        words = WORDS[PARAGRAPH_INDEX]
        if WORD_INDEX < len(words):
            updateWord(window)
            WORD_INDEX += 1
        else:
            PARAGRAPH_INDEX += 1
            WORD_INDEX = 0
            if PARAGRAPH_INDEX >= len(WORDS):
                PARAGRAPH_INDEX = 0
                WORD_INDEX = 0
                playPause(window, forcePause=True)
            else:
                await wordAdvance(WPM)
        if CLOSE:
            break
    return


def updateWord(window: gui.Window) -> None:
    global PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX, WPM
    wordsUp = 14
    halfUp = int(wordsUp / 2)
    words = WORDS[PARAGRAPH_INDEX]
    word = words[WORD_INDEX]
    preIndex = WORD_INDEX - halfUp
    postIndex = WORD_INDEX + halfUp
    if preIndex < 0:
        preIndex = None
        postIndex = (wordsUp - WORD_INDEX) + WORD_INDEX
    elif postIndex > len(words) - 1:
        preIndex = WORD_INDEX - (wordsUp - ((len(words) - 1) - WORD_INDEX))
        preIndex = preIndex if preIndex > 0 else 0
        postIndex = None
    window["-OUTPUT-"].update(word)
    window["wordStreamPre"].update(" ".join(words[preIndex:WORD_INDEX]))
    window["wordStreamCurrent"].update(word)
    window["wordStreamPost"].update(" ".join(words[WORD_INDEX + 1 : postIndex]))
    window.refresh()


async def wordAdvance(wpm: float = None) -> None:
    wpm = wpm or 250
    delay = CalculateDelayFromWPM(wpm)
    await asyncio.sleep(delay)
    await PLAY.wait()
    if CLOSE:
        return
    return


async def main(window: gui.Window):
    await asyncio.gather(windowRead(window), wordHandler(window))
    return


def playPause(window: gui.Window, forcePlay=False, forcePause=False):
    if forcePause:
        play = True
    elif forcePlay:
        play = False
    else:
        play = PLAY.is_set()
    if play:
        PLAY.clear()
        window["playPauseButton"].update("Play")
    else:
        PLAY.set()
        window["playPauseButton"].update("Pause")
    window.Refresh()


def textClean(text: str):
    words = [words.split() for words in text.splitlines()]
    words = [paragraph for paragraph in words if paragraph]
    return words, len(words)


if __name__ == "__main__":
    if path.exists(CONFIG_PATH):
        SMW_CONFIG.read(CONFIG_PATH)
        saveConfig = False
        if "settings" not in SMW_CONFIG:
            SMW_CONFIG.add_section("settings")
            saveConfig = True
        if "wpm" not in SMW_CONFIG["settings"]:
            SMW_CONFIG.set("settings", "wpm", str(WPM))
            saveConfig = True
        if "text" not in SMW_CONFIG["settings"]:
            SMW_CONFIG.set("settings", "text", "")
            saveConfig = True
        if saveConfig:
            with open(CONFIG_PATH, "w") as f:
                SMW_CONFIG.write(f)
    else:
        SMW_CONFIG.add_section("settings")
        SMW_CONFIG.set("settings", "wpm", str(WPM))
        SMW_CONFIG.set("settings", "text", "")
        with open(CONFIG_PATH, "w") as f:
            SMW_CONFIG.write(f)

    WPM = int(SMW_CONFIG["settings"]["wpm"]) or WPM
    text = SMW_CONFIG["settings"]["text"] or ""

    layout = [
        [gui.Text("Ready?", font=("Any", 64, "bold"), key="-OUTPUT-")],
        [
            gui.Text("press", key="wordStreamPre", pad=((5, 0), 3), font=("Any", 16)),
            gui.Text(
                "play",
                key="wordStreamCurrent",
                pad=(0, 3),
                text_color="Red",
                font=("Any", 16),
            ),
            gui.Text(
                "to begin", key="wordStreamPost", pad=((0, 5), 3), font=("Any", 16)
            ),
        ],
        [
            gui.Button("Paste", key="pasteButton"),
            gui.Text(" " * 80),
            gui.Button("|<", key="cursorBeginning"),
            gui.Button("<", key="cursorPrevious"),
            gui.Button("Play", key="playPauseButton"),
            gui.Button(">", key="cursorNext"),
            gui.Button(">|", key="cursorEnd"),
            gui.Text(" " * 60),
            gui.Button("-", key="wpmSubtract"),
            gui.Text(f"{WPM} wpm", key="wpm", font=("Any", 12)),
            gui.Button("+", key="wpmAdd"),
        ],
    ]
    icon = base64.b64encode(open(r'./icon.png', 'rb').read())
    gui.set_options(icon=icon)
    window = gui.Window(
        title="So Many Words", layout=layout, finalize=True, element_justification="c"
    )
    window.bind("<space>", "playPauseButton")
    window.bind("<Ctrl><v>", "pasteButton")
    window.bind("<Left>", "cursorPrevious")
    window.bind("<Shift_L><Left>", "cursorBeginning")
    window.bind("<Right>", "cursorNext")
    window.bind("<Shift_L><Right>", "cursorEnd")
    window.bind("<v>", "pasteButton")


    text = text or (
        "This utility will display words to you at the words per minute "
        f"(WPM) specified below.\nCopy text to the clipboard and hit "
        'the "Paste" button.'
    )

    WORDS, WORDS_LENGTH = textClean(text)
    asyncio.run(main(window))
