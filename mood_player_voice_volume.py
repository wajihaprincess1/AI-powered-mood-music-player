import os
import random
import threading
import pygame
import customtkinter as ctk
import speech_recognition as sr
import openai
from dotenv import load_dotenv

# ---------- LOAD API KEY ----------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------- CONFIGURATION ----------
SONGS_FOLDER = "songs"

pygame.mixer.init()

mood_keywords = {
    "happy": ["happy", "joy", "love", "excited", "fun", "awesome"],
    "sad": ["sad", "cry", "broken", "depressed", "alone", "pain"],
    "calm": ["calm", "peace", "relax", "chill", "soothing"],
    "energetic": ["energy", "boost", "workout", "active", "power", "focus"],
    "angry": ["angry", "mad", "furious", "rage", "annoyed", "irritated"]
}

# ---------- GUI SETUP ----------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("AI Powered Mood Music Player 🎵")
app.geometry("600x600")

# ---------- MOOD DETECTION ----------
def detect_mood(user_text):
    user_text = user_text.lower()
    for mood, keywords in mood_keywords.items():
        for word in keywords:
            if word in user_text:
                return mood
    return "calm"

# ---------- MUSIC CONTROLS ----------
def play_music(mood):
    try:
        all_songs = os.listdir(SONGS_FOLDER)
        mood_songs = [s for s in all_songs if mood in s.lower()]
        if not mood_songs:
            status_label.configure(text=f"No '{mood}' songs found in folder.")
            return
        song = random.choice(mood_songs)
        path = os.path.join(SONGS_FOLDER, song)
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(volume_slider.get())
        pygame.mixer.music.play()
        status_label.configure(text=f"Mood: {mood.capitalize()} | Playing: {song}")
        generate_quote(mood)
    except Exception as e:
        status_label.configure(text=f"Error playing music: {e}")

def stop_music():
    pygame.mixer.music.stop()
    status_label.configure(text="Music stopped.")

def volume_changed(value):
    pygame.mixer.music.set_volume(float(value))

def play_music_text():
    user_input = mood_input.get()
    if not user_input.strip():
        status_label.configure(text="Please enter some mood or feeling text.")
        return
    mood = detect_mood(user_input)
    play_music(mood)

# ---------- VOICE RECOGNITION ----------
def recognize_voice():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    status_label.configure(text="🎙️ Listening... Please speak.")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        mood_input.delete(0, ctk.END)
        mood_input.insert(0, text)
        status_label.configure(text=f"Recognized Text: '{text}'")
        mood = detect_mood(text)
        play_music(mood)
    except sr.UnknownValueError:
        status_label.configure(text="Sorry, could not understand the audio.")
    except sr.RequestError as e:
        status_label.configure(text=f"Could not request results; {e}")

def voice_thread():
    threading.Thread(target=recognize_voice, daemon=True).start()

# ---------- AI QUOTE GENERATOR ----------
def generate_quote(mood):
    def worker():
        try:
            prompt = f"Give me a motivational or comforting quote related to feeling {mood}."
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=40,
                temperature=0.7,
                n=1
            )
            quote = response.choices[0].text.strip()
            def update_label():
                quote_label.configure(text=f"💡 {quote}")
            app.after(0, update_label)
        except Exception as e:
            print("Error generating quote:", e)
    threading.Thread(target=worker, daemon=True).start()

# ---------- AI CHAT WINDOW ----------
def open_chat_window():
    chat_win = ctk.CTkToplevel(app)
    chat_win.geometry("450x500")
    chat_win.title("AI Chat Assistant 🤖")

    chat_display = ctk.CTkTextbox(chat_win, width=420, height=350, state="disabled", corner_radius=10)
    chat_display.pack(pady=10, padx=10)

    user_msg_entry = ctk.CTkEntry(chat_win, width=350, placeholder_text="Share your feelings or chat...")
    user_msg_entry.pack(side="left", padx=(10,5), pady=10)

    def send_message():
        user_msg = user_msg_entry.get().strip()
        if not user_msg:
            return
        chat_display.configure(state="normal")
        chat_display.insert("end", f"You: {user_msg}\n")
        chat_display.configure(state="disabled")
        user_msg_entry.delete(0, ctk.END)
        chat_display.see("end")

        def get_ai_response():
            try:
                response_obj = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a kind and empathetic AI assistant."},
                        {"role": "user", "content": user_msg}
                    ],
                    max_tokens=100,
                    temperature=0.8
                )
                response = response_obj.choices[0].message.content.strip()
                chat_display.configure(state="normal")
                chat_display.insert("end", f"AI: {response}\n\n")
                chat_display.configure(state="disabled")
                chat_display.see("end")
            except Exception as e:
                chat_display.configure(state="normal")
                chat_display.insert("end", "AI: Sorry, something went wrong.\n\n")
                chat_display.configure(state="disabled")
                chat_display.see("end")
                print("Chat error:", e)

        threading.Thread(target=get_ai_response, daemon=True).start()

    send_btn = ctk.CTkButton(chat_win, text="Send", command=send_message)
    send_btn.pack(side="left", padx=(0,10), pady=10)

# ---------- GUI ----------
title_label = ctk.CTkLabel(app, text="🎧 AI Mood Music Player", font=ctk.CTkFont(size=24, weight="bold"))
title_label.pack(pady=15)

mood_input = ctk.CTkEntry(app, width=400, placeholder_text="Type your mood or feelings here...")
mood_input.pack(pady=10)

buttons_frame = ctk.CTkFrame(app)
buttons_frame.pack(pady=10)

play_button = ctk.CTkButton(buttons_frame, text="▶️ Play Music", command=play_music_text)
play_button.grid(row=0, column=0, padx=10, pady=5)

voice_button = ctk.CTkButton(buttons_frame, text="🎙️ Speak Mood", command=voice_thread)
voice_button.grid(row=0, column=1, padx=10, pady=5)

stop_button = ctk.CTkButton(buttons_frame, text="⏹️ Stop Music", command=stop_music)
stop_button.grid(row=0, column=2, padx=10, pady=5)

volume_label = ctk.CTkLabel(app, text="Volume")
volume_label.pack(pady=(15,0))
volume_slider = ctk.CTkSlider(app, from_=0, to=1, number_of_steps=20, command=volume_changed)
volume_slider.set(0.5)
volume_slider.pack(pady=5)

quote_label = ctk.CTkLabel(app, text="💡 Your motivational quote will appear here", font=ctk.CTkFont(size=14))
quote_label.pack(pady=10)

chat_button = ctk.CTkButton(app, text="💬 Open AI Chat Assistant", command=open_chat_window)
chat_button.pack(pady=20)

status_label = ctk.CTkLabel(app, text="Welcome! Type or speak your mood to play music.", font=ctk.CTkFont(size=12))
status_label.pack(pady=10)

app.mainloop()

