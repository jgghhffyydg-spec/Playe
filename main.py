"""Kivy app for learning English phrases with spaced repetition reminders."""

from __future__ import annotations

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import ListProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from scheduler import REPETITION_PLAN, PhraseStore

class PhraseList(ScrollView):
    data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.container = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter("height"))
        self.add_widget(self.container)

    def on_data(self, *_):
        self.container.clear_widgets()
        if not self.data:
            self.container.add_widget(Label(text="No phrases yet.", size_hint_y=None, height=dp(44)))
            return
        for item in self.data:
            self.container.add_widget(
                Label(
                    text=item["text"],
                    font_size=item.get("font_size", "15sp"),
                    halign="left",
                    valign="middle",
                    size_hint_y=None,
                    height=dp(86),
                    text_size=(Window.width - dp(48), None),
                )
            )


class HomeScreen(Screen):
    store = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        title = Label(text="English Daily Review", font_size="24sp", size_hint_y=None, height=dp(44))
        self.summary = Label(font_size="16sp", size_hint_y=None, height=dp(44))
        self.phrase_list = PhraseList()
        add_button = Button(text="Add new phrase", size_hint_y=None, height=dp(52))
        review_button = Button(text="Review due phrases", size_hint_y=None, height=dp(52))
        add_button.bind(on_release=lambda *_: setattr(self.manager, "current", "add"))
        review_button.bind(on_release=lambda *_: setattr(self.manager, "current", "review"))
        root.add_widget(title)
        root.add_widget(self.summary)
        root.add_widget(self.phrase_list)
        root.add_widget(add_button)
        root.add_widget(review_button)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self) -> None:
        due_count = len(self.store.due_phrases()) if self.store else 0
        total = len(self.store.phrases) if self.store else 0
        self.summary.text = f"Due now: {due_count} · Total phrases: {total}"
        self.phrase_list.data = [
            {"text": f"{phrase.english}\n{phrase.translation}\n{phrase.status}", "font_size": "15sp"}
            for phrase in sorted(self.store.phrases, key=lambda item: item.next_review)
        ]


class AddScreen(Screen):
    store = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        root.add_widget(Label(text="Add an English phrase", font_size="22sp", size_hint_y=None, height=dp(48)))
        self.english = TextInput(hint_text="English sentence or word", multiline=True, size_hint_y=None, height=dp(110))
        self.translation = TextInput(hint_text="Meaning / translation", multiline=True, size_hint_y=None, height=dp(110))
        save_button = Button(text="Save and start 10 repetitions", size_hint_y=None, height=dp(52))
        back_button = Button(text="Back", size_hint_y=None, height=dp(52))
        save_button.bind(on_release=self.save_phrase)
        back_button.bind(on_release=lambda *_: setattr(self.manager, "current", "home"))
        root.add_widget(self.english)
        root.add_widget(self.translation)
        root.add_widget(save_button)
        root.add_widget(back_button)
        self.add_widget(root)

    def save_phrase(self, *_):
        if not self.english.text.strip():
            show_message("Missing phrase", "Please enter an English phrase first.")
            return
        self.store.add_phrase(self.english.text, self.translation.text)
        self.english.text = ""
        self.translation.text = ""
        show_message("Saved", "Repeat it 10 times now. It will appear again after 10 minutes.")
        self.manager.current = "home"


class ReviewScreen(Screen):
    store = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_phrase = None
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        self.title = Label(text="Review", font_size="22sp", size_hint_y=None, height=dp(48))
        self.phrase = Label(font_size="24sp")
        self.translation = Label(font_size="18sp", color=(0.75, 0.85, 1, 1))
        done_button = Button(text="I repeated it", size_hint_y=None, height=dp(52))
        back_button = Button(text="Back", size_hint_y=None, height=dp(52))
        done_button.bind(on_release=self.mark_done)
        back_button.bind(on_release=lambda *_: setattr(self.manager, "current", "home"))
        root.add_widget(self.title)
        root.add_widget(self.phrase)
        root.add_widget(self.translation)
        root.add_widget(done_button)
        root.add_widget(back_button)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        self.load_next()

    def load_next(self) -> None:
        due = self.store.due_phrases()
        self.current_phrase = due[0] if due else None
        if not self.current_phrase:
            self.title.text = "No reviews due"
            self.phrase.text = "Great job!"
            self.translation.text = "New and old phrases will appear here at their scheduled times."
            return
        self.title.text = REPETITION_PLAN[self.current_phrase.review_step][0]
        self.phrase.text = self.current_phrase.english
        self.translation.text = self.current_phrase.translation

    def mark_done(self, *_):
        if not self.current_phrase:
            return
        self.store.mark_reviewed(self.current_phrase.id)
        self.load_next()


def show_message(title: str, message: str) -> None:
    Popup(title=title, content=Label(text=message), size_hint=(0.82, 0.36)).open()


class EnglishReviewApp(App):
    def build(self):
        Window.minimum_width = dp(320)
        Window.minimum_height = dp(520)
        self.store = PhraseStore()
        self._last_due_count = 0
        manager = ScreenManager()
        for screen in (HomeScreen(name="home"), AddScreen(name="add"), ReviewScreen(name="review")):
            screen.store = self.store
            manager.add_widget(screen)
        Clock.schedule_interval(self.notify_due_reviews, 30)
        return manager

    def notify_due_reviews(self, *_):
        due = self.store.due_phrases()
        due_count = len(due)
        if due_count and due_count != self._last_due_count and self.root.current != "review":
            show_message("Review reminder", f"You have {due_count} phrase(s) ready to repeat.")
        self._last_due_count = due_count


if __name__ == "__main__":
    EnglishReviewApp().run()
