# -*- coding: utf-8 -*-

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.properties import ListProperty, NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.bubble import Bubble
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from kivy.config import Config
from kivy.metrics import dp

# from pypdf import PdfReader
import os.path
import re


def get_config_file_name():
    # return any file name here
    configDir = os.path.join(os.path.expanduser('~'), '.somanywords')
    if not os.path.exists(configDir):
        os.mkdir(configDir)
    configPath =  str(os.path.join(configDir, 'somanywords.ini'))
    print(f"{configPath=}")
    return configPath


# def readPDF(fileName):
#     try:
#         reader = PdfReader(fileName)
#         if reader.is_encrypted:
#             return "PDF is encrypted"
#         text = ""
#         for page in reader.pages:
#             text = text + page.extract_text()
#     except Exception as e:
#         return f"Error reading PDF: {e}"
#     if not text:
#         return "No text was extracted from the PDF file"
#     return text


def macClipboardPaste():
    pb = NSPasteboard.generalPasteboard()
    pbType = pb.availableTypeFromArray_([NSStringPboardType])
    if pbType:
        clipString = pb.stringForType_(pbType)
        if clipString:
            return clipString
        else:
            return ""
    return


def textClean(text):
    words = [words.split() for words in text.splitlines()]
    return [paragraph for paragraph in words if paragraph]


def getProgress(words, wordIndex, paragraphIndex):
    position = 0
    count = 0
    total = 0
    for i, paragraph in enumerate(words):
        for word in paragraph:
            total += 1
            if paragraphIndex > i:
                count += 1
    count += wordIndex + 1
    return [str(count), str(total)]


class SoManyWordsLayout(BoxLayout):
    pass

class WPMBubble(Bubble):
    pass

class SoManyWordsApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._keyboard = Window.request_keyboard(self._keyboard_closed, None)
        self._keyboard.bind(on_key_down=self._keyboard_down)
        Window.bind(on_dropfile=self._on_file_drop)
        Window.size = (
            int(Config.getdefault("graphics", "width", 1000)),
            int(Config.getdefault("graphics", "height", 500)),
        )
        Clock.schedule_once(self.wordUpdate, 2)

    words = ListProperty()
    wordIndex = NumericProperty(0)
    wordSubIndex = NumericProperty(-1)
    paragraphIndex = NumericProperty(0)
    wpm = NumericProperty(250)
    skipNextBeat = BooleanProperty(False)
    atEndOfWords = BooleanProperty(False)
    wordIsSubWord = BooleanProperty(False)

    def build(self):
        self.icon = 'App Icons MacOS 12-assets/Icon-MacOS-256x256@1x.png'
        self.words = textClean(self.config.get("somanywords", "text"))
        self.wpm = int(self.config.get("somanywords", "wpm"))
        self.paragraphIndex = int(self.config.get("somanywords", "paragraphIndex"))
        self.wordIndex = int(self.config.get("somanywords", "wordIndex"))
        layout = SoManyWordsLayout()
        # layout.ids.menuBar.pos_hint = 0
        # layout.ids.debugLabel.text = (
        #     f"[{self.paragraphIndex}, {self.wordIndex}, {self.wordSubIndex}]"
        # )
        return layout

    def build_config(self, config):
        config.read("somanywords.ini")
        config.setdefaults(
            "somanywords",
            {
                "wpm": "250",
                "text": "This utility will display words to you one at a time at your desired "
                "speed. You can set the words-per-minute below.\nCopy text to the clipboard"
                ' and hit the "Paste" button to get started.',
                "wordIndex": "0",
                "paragraphIndex": "0",
            },
        )

    def on_pre_enter(self):
        Clock.schedule_once(self.wakeupApp, 0.25)

    def wakeupApp(self, *args):
        self.root.ids.menuBar.bottom = self.root.y
        self.wordUpdate()

    def playPause(self, status=None):
        b = self.root.ids.playButton
        status = status or b.text
        if status == "play":
            b.color = get_color_from_hex("#FFFFFF")
            b.buttonActiveColor = get_color_from_hex("#FFFFFF")
            b.buttonColor = get_color_from_hex("#F37F23")
            b.text = "pause"
            self.indexCheck()
            if self.atEndOfWords:
                self.resetIndexes()
            self.atEndOfWords = False
            self.wordUpdate()
            self.clock = Clock.schedule_interval(self.wordAdvance, (60.0 / self.wpm))
        else:
            b.color = get_color_from_hex("#F37F23")
            b.buttonActiveColor = get_color_from_hex("#F37F23")
            b.buttonColor = get_color_from_hex("#FFFFFF")
            b.text = "play"
            try:
                self.clock.cancel()
            except:
                pass
            self.config.set("somanywords", "paragraphIndex", self.paragraphIndex)
            self.config.set("somanywords", "wordIndex", self.wordIndex)
            self.config.write()

    def wordNext(self):
        self.playPause(status="pause")
        if self.atEndOfWords:
            return
        paragraphLength = len(self.words[self.paragraphIndex])
        if (
            self.wordIndex == paragraphLength - 1
            and self.paragraphIndex == len(self.words) - 1
        ):
            return
        self.wordIndex += 1
        # self.wordSubIndex = 0
        # self.atEndOfWords = False
        self.indexCheck()
        self.wordUpdate()

    def wordEnd(self):
        self.playPause(status="pause")
        lastParagraphIndex = len(self.words) - 1
        thisParagraphLastIndex = len(self.words[self.paragraphIndex]) - 1
        # If we decided we are at the end, don't do anything
        if self.atEndOfWords:
            return
        self.wordSubIndex = -1
        # If we are on the last paragraph go to the last word of the last paragraph
        if self.paragraphIndex == lastParagraphIndex:
            self.wordIndex = thisParagraphLastIndex
        # If we are in the middle of a paragraph, go to the end
        elif self.wordIndex == thisParagraphLastIndex or self.wordIndex == 0:
            self.paragraphIndex += 1
            self.wordIndex = 0
        else:
            self.wordIndex = thisParagraphLastIndex
        self.indexCheck()
        self.wordUpdate()

    def wordPrevious(self):
        self.playPause(status="pause")
        self.atEndOfWords = False
        if self.wordSubIndex > 0:
            self.wordSubIndex -= 1
        else:
            self.wordIndex -= 1
        self.indexCheck()
        self.wordUpdate()

    def wordBeginning(self):
        self.playPause(status="pause")
        self.atEndOfWords = False
        if self.wordIndex == 0:
            self.paragraphIndex -= 1
        self.wordIndex = 0
        self.wordSubIndex = -1
        self.indexCheck()
        self.wordUpdate()

    def wordAdvance(self, *args):
        if self.skipNextBeat:
            self.skipNextBeat = False
            return True
        continuePlay = True
        if not self.wordIsSubWord:
            self.wordIndex += 1
            if not self.indexCheck():
                continuePlay = False
        paragraph = self.words[self.paragraphIndex]
        word = paragraph[self.wordIndex]
        iterator = re.finditer(r"\w[-–—/]\w", word) if len(word) > 7 else []
        matches = list(iterator)
        if matches:
            self.wordIsSubWord = True
            indexes = [0]
            for item in matches:
                indexes.append(item.span()[1] - 1)
            parts = [word[i:j] for i, j in zip(indexes, indexes[1:] + [None])]
            self.wordSubIndex += 1
            word = parts[self.wordSubIndex]
            if self.wordSubIndex == len(parts) - 1:
                self.wordIsSubWord = False
                self.wordSubIndex = -1
        self.wordUpdate(word=word)
        if not self.wordIsSubWord and self.wordIndex == len(paragraph) - 1:
            self.skipNextBeat = True
        if not continuePlay:
            self.playPause(status="pause")
        return continuePlay

    def wordUpdate(self, timeCalled=None, word=None, *args):
        currentWordLabel = self.root.ids.currentWord
        ## Dashed and slashed words are annoying, break them up
        paragraph = self.words[self.paragraphIndex]
        wholeWord = paragraph[self.wordIndex]
        word = word or wholeWord
        currentWordLabel.text = str(word)
        wordStreamCurrentLabel = self.root.ids.wordStreamCurrent
        wordStreamCurrentLabel.text = f" {wholeWord} "
        wordStreamBeforeLabel = self.root.ids.wordStreamBefore
        if self.wordIndex > 0:
            startIndex = None if self.wordIndex < 12 else self.wordIndex - 12
            streamText = " ".join(paragraph[startIndex : self.wordIndex])
            if len(streamText) > 42:
                streamText = streamText[-42:]
            wordStreamBeforeLabel.text = streamText
        else:
            wordStreamBeforeLabel.text = ""
        wordStreamAfterLabel = self.root.ids.wordStreamAfter
        if self.wordIndex < len(paragraph) - 1:
            endIndex = (
                None if self.wordIndex > len(paragraph) - 12 else self.wordIndex + 12
            )
            streamText = " ".join(paragraph[self.wordIndex + 1 : endIndex])
            if len(streamText) > 42:
                streamText = streamText[:42]
            wordStreamAfterLabel.text = streamText
        else:
            wordStreamAfterLabel.text = ""
        message = " of ".join(
            getProgress(self.words, self.wordIndex, self.paragraphIndex)
        )
        self.root.ids.debugLabel.text = f"{message}"
        # self.root.ids.debugLabel.text = f"{message}: {self.atEndOfWords=}"
        return True

    def resetIndexes(self):
        self.paragraphIndex = 0
        self.wordIndex = 0
        self.wordSubIndex = -1
        self.skipNextBeat = False

    def indexCheck(self):
        continuePlay = True
        if self.paragraphIndex < 0:
            self.paragraphIndex = 0
        elif self.paragraphIndex >= len(self.words):
            self.resetIndexes()
            continuePlay = False
        if self.wordIndex == len(self.words[self.paragraphIndex]) - 1:
            if self.paragraphIndex == len(self.words) - 1:
                self.atEndOfWords = True
                return False
        if self.wordIndex > len(self.words[self.paragraphIndex]) - 1:
            self.paragraphIndex += 1
            self.wordIndex = 0
            self.wordSubIndex = -1
        elif self.wordIndex < 0:
            self.paragraphIndex -= 1
            self.wordIndex = len(self.words[self.paragraphIndex]) - 1
            self.wordSubIndex = -1
        if self.paragraphIndex == len(self.words):
            self.resetIndexes()
            continuePlay = False
        # self.root.ids.debugLabel.text = (
        #     f"[{self.paragraphIndex}, {self.wordIndex}, {self.wordSubIndex}]"
        # )
        return continuePlay

    def wpmUp(self):
        self.playPause(status="pause")
        self.wpm += 10
        self.config.set("somanywords", "wpm", self.wpm)
        self.config.write()
        self.root.ids.wpmInput.text = str(self.wpm)

    def wpmDown(self):
        self.playPause(status="pause")
        self.wpm -= 10
        self.config.set("somanywords", "wpm", self.wpm)
        self.config.write()
        self.root.ids.wpmInput.text = str(self.wpm)

    def wpmManualInput(self):
        self.playPause(status="pause")
        self.wpmBubble = WPMBubble()
        self.root.ids.mainFloat.add_widget(WPMBubble())

    def setWPM(self, value, instance):
        self.wpm = int(value)
        self.root.ids.mainFloat.remove_widget(instance)

    def paste(self):
        try:
            self.clock.cancel()
        except:
            pass
        self.resetIndexes()
        self.config.set("somanywords", "text", Clipboard.paste())
        self.config.write()
        self.words = textClean(self.config.get("somanywords", "text"))
        self.playPause(status="play")

    def _on_file_drop(self, window, filepath):
        self.root.ids.debugLabel.text = str(filepath)
        return

    def _keyboard_down(self, keyboard, keycode, text, modifier):
        # message = f"{keycode}: {modifier}"
        # self.root.ids.debugLabel.text = message
        if keycode[1] == "spacebar":
            self.playPause()
        if keycode[1] in ["left", "up"]:
            if modifier == ["shift"]:
                self.wordBeginning()
            else:
                self.wordPrevious()
        if keycode[1] in ["right", "down"]:
            if modifier == ["shift"]:
                self.wordEnd()
            else:
                self.wordNext()
        if keycode[1] == "=":
            self.wpmUp()
        if keycode[1] == "-":
            self.wpmDown()
        if keycode[1] == "v":
            self.paste()

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        # self._keyboard.unbind(on_key_up=self._on_keyboard_up)
        self._keyboard = None
    
    def _on_keyboard_down(self):
        pass

    def on_request_close(self):
        self.config.set("somanywords", "paragraphIndex", self.paragraphIndex)
        self.config.set("somanywords", "wordIndex", self.wordIndex)
        self.config.write()
        return True


if __name__ == "__main__":
    Config.read("kivy.ini")
    Config.setdefault("graphics", "width", "1000")
    Config.setdefault("graphics", "height", "400")
    Config.write()
    LabelBase.register(name="Source Code Pro", fn_regular="SourceCodePro[wght].ttf")
    SoManyWordsApp().run()
    Config.set("graphics", "width", Window.size[0])
    Config.set("graphics", "height", Window.size[1])
    Config.write()
