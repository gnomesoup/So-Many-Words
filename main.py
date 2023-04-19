#-*- coding: utf-8 -*-
import asyncio
import base64
from AppKit import NSPasteboard, NSStringPboardType
from codecs import encode
from os import environ, path
import plistlib
from pypdf import PdfReader
import PySimpleGUI as gui
from subprocess import Popen, PIPE
import sys

PLAY = asyncio.Event()
CLOSE = False
WORDS = []
WORDS_LENGTH = 0
WORD_INDEX = 0
PARAGRAPH_INDEX = 0
CONFIG_PATH = (
    f'/Users/{environ.get("USER")}/Library/Preferences/com.mmjo.somanywords.plist'
)
SMW_CONFIG = dict()
WPM = 240

def resourcePath(localPath):
    if hasattr(sys, "_MEIPASS"):
        return path.join(sys._MEIPASS, localPath)
    else:
        return localPath


def CalculateDelayFromWPM(wpm: int) -> float:
    return 60.0 / float(wpm)

def readPDF(fileName):
    try:
        reader = PdfReader(fileName)
        if reader.is_encrypted:
            return "PDF is encrypted"
        text = ""
        for page in reader.pages:
            text = text + page.extract_text()
    except Exception as e:
        return f"Error reading PDF: {e}"
    if not text:
        return "No text was extracted from the PDF file"
    return text


async def windowRead(window: gui.Window):
    global CLOSE, PARAGRAPH_INDEX, WORDS, WORDS_LENGTH, WORD_INDEX, SMW_CONFIG, WPM
    while True:
        await asyncio.sleep(0.01)
        if window['-browse-'].get():
            fileName = window['-browse-'].get()
            if not fileName.lower().endswith(".pdf"):
                gui.popup("Only PDF files are accepted.")
            else:
                text = readPDF(fileName)
                WORDS, WORDS_LENGTH = textClean(text)
                WORD_INDEX = 0
                PARAGRAPH_INDEX = 0
            playPause(window, forcePlay=True)
            savePlist(CONFIG_PATH, SMW_CONFIG)
            window['-browse-'].update("")
            window.refresh()
        event, values = window.read(0)
        if event == "__TIMEOUT__":
            continue
        # print(f"{event=}")
        if event == "Close" or event == gui.WIN_CLOSED:
            PLAY.set()
            break
        if event == "playPauseButton":
            playPause(window)
        if event == "pasteButton":
            try:
                text = macClipboardPaste()
                if not text:
                    text = "Clipboard does not contain text"
                SMW_CONFIG["text"] = str(text)
            except Exception as e:
                text = f"Error processing pasted material: {e}"
            savePlist(CONFIG_PATH, SMW_CONFIG)
            WORDS, WORDS_LENGTH = textClean(text)
            WORD_INDEX = 0
            PARAGRAPH_INDEX = 0
            playPause(window, forcePlay=True)
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
            SMW_CONFIG["wpm"] = WPM
            savePlist(CONFIG_PATH, SMW_CONFIG)

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
            elif words[-1].endswith(".") or words[-1].endswith("\n"):
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


def savePlist(path: str, config: dict) -> None:
    with open(CONFIG_PATH, "wb") as f:
        plistlib.dump(value=config, fp=f)

def macClipboardPaste():
    pb = NSPasteboard.generalPasteboard()
    pbType = pb.availableTypeFromArray_([NSStringPboardType])
    if pbType:
        clipString = pb.stringForType_(pbType)
        if clipString:
            return clipString
        else:
            return ""
    # p = Popen(["pbpaste", "-P RTL"], stdout=PIPE)
    # p.wait()
    # data = p.stdout.read()
    # data = data.decode(encoding='utf-8', errors="replace")
    return

if __name__ == "__main__":
    if path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "rb") as f:
            SMW_CONFIG = plistlib.load(f)
        saveConfig = False
        if "wpm" not in SMW_CONFIG:
            SMW_CONFIG["wpm"] = WPM
            saveConfig = True
        if "text" not in SMW_CONFIG:
            SMW_CONFIG["text"] = ""
            saveConfig = True
        if saveConfig:
            savePlist(CONFIG_PATH, SMW_CONFIG)
    else:
        SMW_CONFIG = dict(wpm=WPM, text="")
        savePlist(CONFIG_PATH, SMW_CONFIG)

    WPM = int(SMW_CONFIG["wpm"]) or WPM
    text = SMW_CONFIG["text"] or ""

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
            gui.FileBrowse(target="-browse-", file_types=(("PDF Files", "*.txt"),)),
            gui.Input(key="-browse-", visible=False),
            gui.Text(" " * 60),
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

    icon = base64.b64encode(open(resourcePath("./icon.png"), "rb").read())
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
