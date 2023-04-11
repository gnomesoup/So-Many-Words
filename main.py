import clipboard
import PySimpleGUI as gui
import asyncio
import re

PLAY = asyncio.Event()
CLOSE = False
WORDS = []
WORDS_LENGTH = 0
WORD_INDEX = 0
PARAGRAPH_INDEX = 0


def CalculateDelayFromWPM(wpm: int) -> float:
    return 60.0 / float(wpm)


async def windowRead(window: gui.Window):
    global CLOSE, PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX
    while True:
        await asyncio.sleep(0.01)
        event, values = window.read(0)
        if event != "__TIMEOUT__":
            print(f"event: {event}, {values}")
        if event == "Close" or event == gui.WIN_CLOSED:
            PLAY.set()
            break
        if event == "playPauseButton":
            print("play pause event")
            playPause(window)
        if event == "pasteButton":
            print("paste")
            WORDS, WORDS_LENGTH = textClean(clipboard.paste())
            WORD_INDEX = 0
            PARAGRAPH_INDEX = 0
            playPause(window, forcePlay=True)
        if event == "cursorBeginning":
            PARAGRAPH_INDEX = 0
            WORD_INDEX = 0
        if event == "cursorEnd":
            PARAGRAPH_INDEX = len(WORDS)
            WORD_INDEX = len(WORDS[PARAGRAPH_INDEX])
        if event == "cursorPrevious":
            targetIndex = WORD_INDEX - 1
            if targetIndex < 0:
                if PARAGRAPH_INDEX == 0:
                    WORD_INDEX = 0
                else:
                    PARAGRAPH_INDEX -= 1
                    WORD_INDEX = len(WORDS[PARAGRAPH_INDEX])
            else:
                WORD_INDEX = targetIndex
        if event == "cursorNext":
            targetIndex = WORD_INDEX + 1
            if targetIndex > len(WORDS[PARAGRAPH_INDEX]):
                if PARAGRAPH_INDEX != len(WORDS):
                    PARAGRAPH_INDEX += 1
                    WORD_INDEX = 0
            else:
                WORD_INDEX = targetIndex
        if event.startswith("cursor"):
            playPause(window, forcePause=True)
            updateWord(window)

    CLOSE = True
    window.close()
    return


async def wordHandler(window: gui.Window) -> None:
    global PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX
    while True:
        if CLOSE:
            break
        await wordAdvance()
        words = WORDS[PARAGRAPH_INDEX]
        if WORD_INDEX < len(words):
            updateWord(window)
            WORD_INDEX += 1
        else:
            PARAGRAPH_INDEX += 1
            WORD_INDEX = 0
            if PARAGRAPH_INDEX >= len(WORDS):
                print("Paragraph Done")
                PARAGRAPH_INDEX = 0
                WORD_INDEX = 0
                playPause(window, forcePause=True)
            else:
                await wordAdvance()
        if CLOSE:
            break
    return


def updateWord(window: gui.Window) -> None:
    global PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX
    words = WORDS[PARAGRAPH_INDEX]
    word = words[WORD_INDEX]
    print(f"{PARAGRAPH_INDEX=}")
    print(f"{WORD_INDEX=}")
    print(f"{word=}")
    if WORD_INDEX > 0:
        targetIndex = WORD_INDEX - 10
        actualIndex = targetIndex if targetIndex > 0 else WORD_INDEX
        preWords = " ".join(words[0:actualIndex])
    else:
        preWords = []
    if WORD_INDEX < len(words) - 1:
        targetIndex = WORD_INDEX + 10
        actualIndex = targetIndex if targetIndex < len(words) else WORD_INDEX + 1
        postWords = " ".join(words[WORD_INDEX + 1 : actualIndex])
    else:
        postWords = []
    window["-OUTPUT-"].update(word)
    window["wordStreamPre"].update(preWords)
    window["wordStreamCurrent"].update(word)
    window["wordStreamPost"].update(postWords)
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
    return words, len(words)


if __name__ == "__main__":
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
            gui.Button("Close"),
        ],
        [
            gui.Button("|<", key="cursorBeginning"),
            gui.Button("<", key="cursorPrevious"),
            gui.Button("Play", key="playPauseButton"),
            gui.Button(">", key="cursorNext"),
            gui.Button(">|", key="cursorEnd"),
        ],
    ]
    window = gui.Window(title="So Many Words", layout=layout, finalize=True)
    window.bind("<space>", "playPauseButton")
    window.bind("<Ctrl><v>", "pasteButton")

    text = (
        "This utility will display words to you at the specified words per minute "
        "(WPM).\nThis is currently set to {WPM}.\nCopy text to the clipboard and hit "
        'the "Paste" button.'
    )
    clip = clipboard.paste()
    # text = clip if type(clip) is str else text
    # WORDS = re.findall(r'\b\w+\b', text)
    WORDS, WORDS_LENGTH = textClean(text)
    asyncio.run(main(window))
