import os
import random
import threading
import pygame
import customtkinter as ctk
import speech_recognition as sr
import openai
import time
from dotenv import load_dotenv

is_playing = False 


# ---------- LOAD API KEY ----------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI()


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

mood_themes = {
    "happy": {
        "bg": "#FFF9C4", "fg": "#333333", "emoji": "😄"
    },
    "sad": {
        "bg": "#BBDEFB", "fg": "#0D47A1", "emoji": "😢"
    },
    "calm": {
        "bg": "#E0F2F1", "fg": "#004D40", "emoji": "😌"
    },
    "energetic": {
        "bg": "#FFCDD2", "fg": "#B71C1C", "emoji": "💥"
    },
    "angry": {
        "bg": "#FF8A80", "fg": "#BF360C", "emoji": "😡"
    }
}


# ---------- GUI SETUP ----------
ctk.set_appearance_mode("light")
app = ctk.CTk()
app.geometry("600x650")
app.title("🎵 Smart Mood Music Player")

widgets = []

def apply_theme(mood):
    theme = mood_themes.get(mood, {"bg": "#F7F9FC", "fg": "#2C3E50", "emoji": "🎵"})
    app.configure(fg_color=theme["bg"])

    for widget in widgets:
        try:
            widget.configure(text_color=theme["fg"])
        except:
            pass

    emoji_label.configure(text=theme["emoji"], text_color=theme["fg"])

# ---------- MOOD DETECTION ----------
def detect_mood(user_text):
    user_text = user_text.lower()
    for mood, keywords in mood_keywords.items():
        if any(word in user_text for word in keywords):
            return mood
    return "calm"

# ---------- MUSIC CONTROLS ----------
def play_music(mood):
    global is_playing
    try:
        all_songs = os.listdir(SONGS_FOLDER)
        mood_songs = [s for s in all_songs if mood in s.lower()]
        if not mood_songs:
            status_label.configure(text=f"No '{mood}' songs found.")
            return
        song = random.choice(mood_songs)
        path = os.path.join(SONGS_FOLDER, song)
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(volume_slider.get())
        pygame.mixer.music.play()
        status_label.configure(text=f"Mood: {mood.capitalize()} | Playing: {song}")
        apply_theme(mood)

        is_playing = True 

        generate_quote(mood)
        generate_lyrics(mood)

    except Exception as e:
        status_label.configure(text=f"Error playing music: {e}")


def stop_music():
    global is_playing
    is_playing = False
    pygame.mixer.music.stop()
    status_label.configure(text="Music stopped.")
    quote_label.configure(text="💡 Your motivational quote will appear here")
    lyrics_label.configure(text="🎶 Your mood-based lyrics will appear here")

def volume_changed(value):
    pygame.mixer.music.set_volume(float(value))

def play_music_text():
    user_input = mood_input.get()
    if not user_input.strip():
        status_label.configure(text="Please enter your mood or feelings.")
        return
    mood = detect_mood(user_input)
    play_music(mood)

# ---------- VOICE RECOGNITION ----------
def recognize_voice():
    try:
        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        status_label.configure(text="🎙️ Listening...")

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5)

        status_label.configure(text="🎧 Processing...")

        # Try to recognize using Google's speech recognition
        text = recognizer.recognize_google(audio)
        mood_input.delete(0, ctk.END)
        mood_input.insert(0, text)
        status_label.configure(text=f"Recognized: '{text}'")

        mood = detect_mood(text)
        play_music(mood)

    except sr.WaitTimeoutError:
        status_label.configure(text="⌛ Timeout: No speech detected.")
    except sr.UnknownValueError:
        status_label.configure(text="😕 Could not understand the audio.")
    except sr.RequestError as e:
        status_label.configure(text=f"🔌 API Error: {e}")
    except Exception as e:
        status_label.configure(text=f"⚠️ Error: {e}")


def voice_thread():
    threading.Thread(target=recognize_voice, daemon=True).start()

# ---------- AI QUOTE GENERATOR ----------
def generate_quote(mood):
    def quote_loop():
        while is_playing:
            try:
                prompt = f"Give me a short motivational or comforting quote for someone who is feeling {mood}."

                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a kind and motivational assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.8
                )

                quote = response.choices[0].message.content.strip()

                app.after(0, lambda: quote_label.configure(text=f"💡 {quote}"))

            except Exception as e:
                print("❌ Quote generation error:", e)
                app.after(0, lambda: quote_label.configure(text="💡 Couldn't fetch quote."))

            # Wait 15 seconds before next quote
            for _ in range(5):
                if not is_playing:
                    break
                time.sleep(0.5)

    threading.Thread(target=quote_loop, daemon=True).start()

# ---------- AI LYRICS GENERATOR ----------
def generate_lyrics(mood):
    def lyrics_loop():
        while is_playing:
            try:
                prompt = f"Write 2 lines of original song lyrics for someone feeling {mood}."
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=60,
                    temperature=0.8
                )
                lyrics = response.choices[0].message.content.strip()
                app.after(0, lambda: lyrics_label.configure(text=f"🎶 {lyrics}"))
            except Exception as e:
                print("Lyrics error:", e)
                app.after(0, lambda: lyrics_label.configure(text="❌ Failed to fetch lyrics."))

            # Wait 15 seconds before next lyrics
            for _ in range(5):
                if not is_playing:
                    break
                time.sleep(0.5)

    threading.Thread(target=lyrics_loop, daemon=True).start()

# ---------- AI CHAT WINDOW ----------
def open_chat_window():
    chat_win = ctk.CTkToplevel(app)
    chat_win.geometry("480x520")
    chat_win.title("AI Chat Assistant 🤖")
    chat_win.configure(padx=25, pady=20)

    # Title label for the chat window
    title = ctk.CTkLabel(chat_win, text="AI Chat Assistant 🤖", font=ctk.CTkFont(size=22, weight="bold"))
    title.pack(pady=(0, 15))

    # Chat display area
    chat_display = ctk.CTkTextbox(chat_win, width=440, height=380, state="disabled", corner_radius=15, fg_color="#eaeaea", text_color="#222")
    chat_display.pack(pady=(0, 20))

    # Input frame with entry and send button side-by-side
    input_frame = ctk.CTkFrame(chat_win, fg_color="transparent")
    input_frame.pack(fill="x")

    user_msg_entry = ctk.CTkEntry(input_frame, placeholder_text="Type your message here...", font=ctk.CTkFont(size=16))
    user_msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=5, ipady=8)

    send_btn = ctk.CTkButton(input_frame, text="Send", width=90, font=ctk.CTkFont(size=16, weight="bold"))
    send_btn.pack(side="left", pady=5)

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
                response_obj = client.chat.completions.create(
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
                chat_display.insert("end", f"AI: Sorry, something went wrong.\n\n⚠️ Error: {e}\n\n")
                chat_display.configure(state="disabled")
                chat_display.see("end")

        threading.Thread(target=get_ai_response, daemon=True).start()

    send_btn.configure(command=send_message)
    user_msg_entry.bind("<Return>", lambda event: send_message())

# ---------- GUI WIDGETS ----------
ctk.set_appearance_mode("light")
app = ctk.CTk()
app.geometry("620x700")
app.title("🎵 Smart Mood Music Player")

# Set app background color for calm default
app.configure(fg_color="#F7F9FC")

widgets.clear()  # Clear widget list if rerunning

# ---- Fonts ----
title_font = ctk.CTkFont(size=28, weight="bold")
label_font = ctk.CTkFont(size=16, weight="bold")
text_font = ctk.CTkFont(size=14)
button_font = ctk.CTkFont(size=16, weight="bold")
small_font = ctk.CTkFont(size=12)

# ---- Title ----
title_label = ctk.CTkLabel(app, text="🎧 Smart Mood Music Player", font=title_font, text_color="#34495E")
title_label.pack(pady=(25, 20))
widgets.append(title_label)

emoji_label = ctk.CTkLabel(app, text="🎵", font=ctk.CTkFont(size=48))
emoji_label.pack(pady=(0, 10))
widgets.append(emoji_label)


# ---- Mood Input ----
mood_input = ctk.CTkEntry(app, width=450, placeholder_text="Type your mood or feeling...", font=text_font)
mood_input.pack(pady=(0, 20))
widgets.append(mood_input)

# Centered buttons frame with background and rounded corners
buttons_frame = ctk.CTkFrame(app, fg_color="#ECF0F1", corner_radius=15)
buttons_frame.pack(pady=(0, 25), padx=20)

play_button = ctk.CTkButton(buttons_frame, text="▶️ Play", command=play_music_text)
play_button.pack(side="left", padx=15, pady=15, expand=True)
widgets.append(play_button)

voice_button = ctk.CTkButton(buttons_frame, text="🎙️ Voice", command=voice_thread)
voice_button.pack(side="left", padx=15, pady=15, expand=True)
widgets.append(voice_button)

stop_button = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_music)
stop_button.pack(side="left", padx=15, pady=15, expand=True)
widgets.append(stop_button)

# ---- Volume Control ----
volume_frame = ctk.CTkFrame(app, fg_color="#ECF0F1", corner_radius=15)
volume_frame.pack(pady=(0, 25), padx=20, fill="x")

volume_label = ctk.CTkLabel(volume_frame, text="Volume", font=label_font, text_color="#34495E")
volume_label.pack(side="left", padx=15, pady=10)

volume_slider = ctk.CTkSlider(volume_frame, from_=0, to=1, number_of_steps=20, command=volume_changed)
volume_slider.set(0.5)
volume_slider.pack(side="left", fill="x", expand=True, padx=(0, 15), pady=10)
widgets.append(volume_slider)
widgets.append(volume_label)

# ---- Quote Card ----
quote_frame = ctk.CTkFrame(app, fg_color="#D6EAF8", corner_radius=20, border_width=1, border_color="#85C1E9")
quote_frame.pack(padx=30, pady=(0, 15), fill="x")

quote_label = ctk.CTkLabel(quote_frame, text="💡 Your motivational quote will appear here", font=text_font, wraplength=530)
quote_label.pack(padx=15, pady=20)
widgets.append(quote_label)

# ---- Lyrics Card ----
lyrics_frame = ctk.CTkFrame(app, fg_color="#FCF3CF", corner_radius=20, border_width=1, border_color="#F7DC6F")
lyrics_frame.pack(padx=30, pady=(0, 30), fill="x")

lyrics_label = ctk.CTkLabel(lyrics_frame, text="🎶 Your mood-based lyrics will appear here", font=text_font, wraplength=530)
lyrics_label.pack(padx=15, pady=20)
widgets.append(lyrics_label)

# ---- Chat Button ----
chat_button = ctk.CTkButton(app, text="💬 Open AI Chat", command=open_chat_window, font=button_font, width=200)
chat_button.pack(pady=(0, 30))
widgets.append(chat_button)

# ---- Status Bar ----
status_label = ctk.CTkLabel(app, text="Welcome! Share your mood to play music.", font=small_font, text_color="#7F8C8D")
status_label.pack(side="bottom", pady=10)
widgets.append(status_label)

app.mainloop()