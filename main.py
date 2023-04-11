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
WPM = 200


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
            playPause(window)
        if event == "pasteButton":
            WORDS, WORDS_LENGTH = textClean(clipboard.paste())
            WORD_INDEX = 0
            PARAGRAPH_INDEX = 0
            playPause(window, forcePlay=True)
        if event == "cursorBeginning":
            PARAGRAPH_INDEX = 0
            WORD_INDEX = 0
        if event == "cursorEnd":
            PARAGRAPH_INDEX = len(WORDS) - 1
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

    CLOSE = True
    window.close()
    return

async def wordHandler(window: gui.Window) -> None:
    global PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX
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
    global PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX
    wordsUp = 20
    halfUp = int(wordsUp / 2)
    preIndex = 0
    postIndex = 0
    words = WORDS[PARAGRAPH_INDEX]
    if WORD_INDEX < 10:
        print("small pre")
        preIndex = 0
        targetIndex = wordsUp - WORD_INDEX + 1
        postIndex = targetIndex if (targetIndex + WORD_INDEX) < len(words) else None
    elif (len(words) - WORD_INDEX) < halfUp:
        print("small post")
        targetIndex = WORD_INDEX - wordsUp
        preIndex =  targetIndex if targetIndex > 0 else 0
        postIndex = None
    else:
        print("balanced")
        preIndex = WORD_INDEX - 10
        postIndex = WORD_INDEX + 10
    word = words[WORD_INDEX]
    print(f"{WORD_INDEX=}")
    print(f"{preIndex=}")
    print(f"{postIndex=}")
    window["-OUTPUT-"].update(word)
    window["wordStreamPre"].update(" ".join(words[preIndex:WORD_INDEX]))
    window["wordStreamCurrent"].update(word)
    window["wordStreamPost"].update(" ".join(words[WORD_INDEX + 1:postIndex]))
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
        f"(WPM).\nThis is currently set to {WPM}.\nCopy text to the clipboard and hit "
        'the "Paste" button.'
    )
    clip = clipboard.paste()
    # text = clip if type(clip) is str else text
    # WORDS = re.findall(r'\b\w+\b', text)
    WORDS, WORDS_LENGTH = textClean(text)
    asyncio.run(main(window))
