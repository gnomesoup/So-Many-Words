# -*- coding: utf-8 -*-
from AppKit import NSPasteboard, NSStringPboardType

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.properties import ListProperty, NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from kivy.config import Config
from kivy.metrics import dp

import json
from pypdf import PdfReader
import re


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


class SoManyWordsLayout(BoxLayout):
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

    words = ListProperty()
    wordIndex = NumericProperty(0)
    wordSubIndex = NumericProperty(0)
    paragraphIndex = NumericProperty(0)
    wpm = NumericProperty(250)
    skipNextBeat = BooleanProperty(False)
    atEndOfWords = BooleanProperty(False)

    def build(self):
        self.words = textClean(
            self.config.get("somanywords", "text")
        )
        self.wpm = int(self.config.get("somanywords", "wpm"))
        self.paragraphIndex = int(self.config.get("somanywords", "paragraphIndex"))
        self.wordIndex = int(self.config.get("somanywords", "wordIndex"))
        self.wordIndex -= 1
        return SoManyWordsLayout()

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
                "paragraphIndex": "0"
            },
        )

    def playPause(self, status=None):
        b = self.root.ids.playButton
        status = status or b.text
        if status == "play":
            b.color = get_color_from_hex("#64778C")
            b.text = "pause"
            if self.atEndOfWords:
                self.resetIndexes()
            self.clock = Clock.schedule_interval(self.wordUpdate, (60.0 / self.wpm))
        else:
            b.color = get_color_from_hex("#FC0000")
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
        paragraphLength = len(self.words[self.paragraphIndex])
        if (
            self.wordIndex == paragraphLength - 1
            and self.paragraphIndex == len(self.words) - 1
        ):
            return
        self.wordIndex += 1
        self.wordSubIndex = 0
        self.atEndOfWords = False
        self.indexCheck()
        self.wordUpdate(advanceIndex=False)

    def wordEnd(self):
        self.playPause(status="pause")
        lastParagraphIndex = len(self.words) - 1
        thisParagraphLastIndex = len(self.words[self.paragraphIndex]) - 1
        # If we decided we are at the end, don't do anything
        if self.atEndOfWords:
            return
        self.wordSubIndex = 0
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
        self.wordUpdate(advanceIndex=False)

    def wordPrevious(self):
        self.playPause(status="pause")
        self.wordIndex -= 1
        self.wordSubIndex = 0
        self.indexCheck()
        self.wordUpdate(advanceIndex=False)

    def wordBeginning(self):
        self.playPause(status="pause")
        if self.wordIndex == 0:
            self.paragraphIndex -= 1
        self.wordIndex = 0
        self.wordSubIndex = 0
        self.indexCheck()
        self.wordUpdate(advanceIndex=False)

    def wordAdvance(self):
        pass

    def wordUpdate(self, advanceIndex=True, *args):
        if advanceIndex and self.skipNextBeat:
            self.skipNextBeat = False
            return True
        currentWordLabel = self.root.ids.currentWord
        ## Dashed and slashed words are annoying, break them up
        paragraph = self.words[self.paragraphIndex]
        word = paragraph[self.wordIndex]
        iterator = re.finditer(r"\w[-–—/]\w", word) if len(word) > 7 else []
        matches = list(iterator)
        startIndex = None
        endIndex = None
        if matches:
            ## Check if the sub index is out of wack
            advanceIndex = False
            if self.wordSubIndex > len(matches):
                self.wordSubIndex = 0
            ## What happens if this is the first sub index
            if self.wordSubIndex == 0:
                print("first sub")
                endIndex = matches[self.wordSubIndex].span()[1] - 1
                self.wordSubIndex += 1
            ## What happens if this is the last sub index
            elif self.wordSubIndex == len(matches):
                print("last sub")
                startIndex = matches[self.wordSubIndex - 1].span()[1] - 1
                self.wordSubIndex = 0
                if self.wordIndex == len(paragraph):
                    self.skipNextBeat = True
                else:
                    advanceIndex = True
            ## What happens the rest of the time
            else:
                startIndex = matches[self.wordSubIndex - 1].span()[1] - 1
                endIndex = matches[self.wordSubIndex].span()[1] - 1
                self.wordSubIndex += 1
        currentWordLabel.text = word[startIndex:endIndex]
        wordStreamCurrentLabel = self.root.ids.wordStreamCurrent
        wordStreamCurrentLabel.text = f" {word} "
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
        if advanceIndex:
            self.wordIndex += 1
            if self.wordIndex == len(paragraph):
                self.skipNextBeat = True
        if not self.indexCheck():
            self.playPause(status="pause")
            return False
        return True

    def resetIndexes(self):
        self.paragraphIndex = 0
        self.wordIndex = 0
        self.wordSubIndex = 0
        self.skipNextBeat = False

    def indexCheck(self):
        if self.paragraphIndex < 0:
            self.paragraphIndex = 0
        if self.wordIndex == len(self.words[self.paragraphIndex]) - 1:
            if self.paragraphIndex == len(self.words) - 1:
                self.atEndOfWords = True
                self.root.ids.debugLabel.text = f"end of words"
                return False
        if self.wordIndex > len(self.words[self.paragraphIndex]) - 1:
            self.paragraphIndex += 1
            self.wordIndex = 0
            self.wordSubIndex = 0
        elif self.wordIndex < 0:
            self.paragraphIndex -= 1
            self.wordIndex = 0
            self.wordSubIndex = 0
        if self.paragraphIndex < 0:
            self.resetIndexes()
            self.root.ids.debugLabel.text = f"[{self.paragraphIndex}, {self.wordIndex}]"
            return False
        self.root.ids.debugLabel.text = f"[{self.paragraphIndex}, {self.wordIndex}]"
        return True

    def wpmUp(self):
        self.wpm += 10
        self.config.set("somanywords", "wpm", self.wpm)
        self.config.write()
        self.root.ids.wpmInput.text = str(self.wpm)

    def wpmDown(self):
        self.wpm -= 10
        self.config.set("somanywords", "wpm", self.wpm)
        self.config.write()
        self.root.ids.wpmInput.text = str(self.wpm)

    def wpmManualInput(self):
        pass

    def paste(self):
        try:
            self.clock.cancel()
        except:
            pass
        self.wordIndex = 0
        self.paragraphIndex = 0
        self.config.set("somanywords", "text", macClipboardPaste())
        self.config.write()
        self.words = textClean(self.config.get("somanywords", "text"))
        self.playPause(status="play")

    def _on_file_drop(self, window, filepath):
        self.root.ids.debugLabel.text = str(filepath)
        return

    def _keyboard_down(self, keyboard, keycode, text, modifier):
        message = f"{keycode}: {modifier}"
        self.root.ids.debugLabel.text = message
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
