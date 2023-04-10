import clipboard
import PySimpleGUI as gui
import asyncio
import re

PLAY = asyncio.Event()
CLOSE = False
WORDS = []
WORDS_LENGTH = 0

def CalculateDelayFromWPM(wpm:int) -> float:
    return 60.0 / float(wpm)


async def windowRead(window:gui.Window):
    global CLOSE
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
            if PLAY.is_set():
                PLAY.clear()
                window["playPauseButton"].update("Play")
            else:
                PLAY.set()
                window["playPauseButton"].update("Pause")
            window.Refresh()
            
    CLOSE = True
    window.close()
    return


async def updateWordDisplay(window:gui.Window) -> None:
    paragraphIndex = 0
    wordIndex = 0
    for word in WORDS:
        if CLOSE:
            break
        await wordAdvance()
        window["-OUTPUT-"].update(word)
        window.refresh()
        print(word)
        wordIndex += 1
        if CLOSE:
            break
        paragraphIndex += 1
    return


async def wordAdvance(wpm:float=None) -> None:
    wpm = wpm or 250
    delay = CalculateDelayFromWPM(wpm)
    await asyncio.sleep(delay)
    await PLAY.wait()
    if CLOSE:
        return
    return


async def main(window:gui.Window):
    await asyncio.gather(windowRead(window), updateWordDisplay(window))
    return

if __name__ == "__main__":
    layout = [
        [gui.Text("Ready?", font=("Any", 64, "bold"),key="-OUTPUT-")],
        [gui.Button("Paste", key="pasteButton")],
        [gui.Button("Play", key="playPauseButton")],
        [gui.Button("Close")]
    ]
    window = gui.Window(title="So Many Words", layout=layout, finalize=True)
    window.bind("<space>", "playPauseButton")

    text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua. Varius duis at consectetur lorem "
        "donec massa. Phasellus faucibus scelerisque eleifend donec pretium vulputate. "
        "Nulla facilisi nullam vehicula ipsum a. Sem nulla pharetra diam sit amet nisl "
        "suscipit. Id interdum velit laoreet id donec ultrices tincidunt. Vulputate "
        "dignissim suspendisse in est ante in nibh mauris cursus. Ultricies lacus sed "
        "turpis tincidunt id aliquet risus feugiat in. Curs us sit amet dictum sit amet. "
        "Tempus imperdiet nulla malesuada pellentesque elit eget gravida cum. Orci sagittis "
        "eu volutpat odio. Bibendum neque egestas congue quisque egestas diam.\n"
        "Lacus vestibulum sed arcu non odio. Dignissim enim sit amet venenatis urna cursus "
        "eget.  Porta non pulvinar neque laoreet suspendisse interdum. Tristique nulla "
        "aliquet enim tortor at. Enim neque volutpat ac tincidunt vitae semper quis lectus "
        "nulla. Et odio pellentesque diam volutpat commodo sed egestas. Tortor at auctor "
        "urna nunc id cursus metus aliquam. Id velit ut tortor pretium viverra suspendisse "
        "potenti nullam ac. Risus quis varius quam quisque id diam vel. Ultricies tristique "
        "nulla aliquet enim. Vulputate sapien nec sagittis aliquam malesuada bibendum. "
        "Risus at ultrices mi tempus imperdiet nulla malesuada pellentesque. Feugiat in "
        "fermentum posuere urna nec. Sagittis vitae et leo duis ut diam quam. "
    )
    clip = clipboard.paste()
    # text = clip if type(clip) is str else text

    # WORDS = re.findall(r'\b\w+\b', text)
    WORDS = text.split()
    asyncio.run(main(window))
