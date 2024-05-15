
import tkinter as tk
import cv2
import mediapipe as mp
import pyautogui
import psutil
import speedtest
from PIL import Image, ImageTk
import speech_recognition as sr
import pyttsx3
import pywhatkit
import datetime
import wikipedia
import webbrowser
import pyjokes
import os
import subprocess

class ZeroAssistant:
    def __init__(self):
        self.listener = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', self.voices[1].id)
        self.engine.setProperty('rate', 145)
        self.greeted = False
        self.init_gui()

    def talk(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def wish(self):
        if not self.greeted:
            hour = datetime.datetime.now().hour
            if 0 <= hour < 12:
                greeting = "Good morning!"
            elif 12 <= hour < 18:
                greeting = "Good afternoon!"
            else:
                greeting = "Good evening!"
            self.talk(f"{greeting} Hi, I'm Zero. Iam glad to meet you again sir How can I help you?")
            self.greeted = True

    def take_voice_command(self):
        try:
            with sr.Microphone() as source:
                print('Listening...')
                voice = self.listener.listen(source)
                command = self.listener.recognize_google(voice)
                command = command.lower()
                if 'zero' in command:
                    command = command.replace('zero', '')
                    print(command)
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand.")
            return ""
        except sr.RequestError:
            print("Could not request results. Please check your internet connection.")
            return ""
        return command

    def take_text_command(self):
        command = input("Enter command: ").lower()
        if 'zero' in command:
            command = command.replace('zero', '')
        return command

    def run_zero(self, command):
        if 'search' in command or 'solve' in command:
            search = command.replace('search', '').replace('solve', '').strip()
            if search:
                url = 'https://google.com/search?q=' + search
                webbrowser.open(url)
        elif 'play' in command:
            song = command.replace('play', '')
            self.talk('Playing ' + song)
            pywhatkit.playonyt(song)
        elif 'time' in command:
            time = datetime.datetime.now().strftime('%I:%M %p')
            self.talk('Current time is ' + time)
        elif 'virus' in command:
            subprocess.call("start /wait MRT.exe", shell=True)
        elif 'who is' in command:
            person = command.replace('who is', '')
            info = wikipedia.summary(person, 1)
            print(info)
            self.talk(info)
        elif 'calculator' in command:
            self.open_calculator()
        elif "notepad" in command:
            self.talk('Opening Notepad')
            npath = "C:\\Windows\\notepad.exe"
            os.startfile(npath)
        elif 'android studio' in command:
            self.talk('Opening Android Studio')
            stdpath = "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Android Studio\\Android Studio.lnk"
            os.startfile(stdpath)
        elif 'discord' in command:
            self.talk("Opening Discord")
            dcpath = "C:\\Users\\skgam\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Discord Inc\\Discord.lnk"
            os.startfile(dcpath)
        elif 'eyes virtual mouse' in command:
            self.eyes_virtual_mouse()
        elif 'virtual mouse' in command:
            self.virtual_mouse()
        elif "internet speed" in command:
            self.check_internet_speed()
        elif "how much power left" in command or "battery" in command:
            self.check_battery()
        elif 'date' in command:
            self.talk('Sorry, I have a headache')
        elif 'are you single' in command:
            self.talk('I am in a relationship with wifi')
        elif 'joke' in command:
            self.talk(pyjokes.get_joke())
        elif 'exit' in command:
            exit()
        else:
            self.talk('Please say the command again.')

    def voice_assistant(self):
        self.wish()
        while True:
            command = self.take_voice_command()
            print(command)
            self.run_zero(command)

    def text_assistant(self):
        self.wish()
        while True:
            command = self.take_text_command()
            print(command)
            self.run_zero(command)

    def start_assistant(self):
        self.greeted = False
        assistant_type = self.assistant_type_var.get()
        if assistant_type == 'voice':
            self.voice_assistant()
        elif assistant_type == 'text':
            self.text_assistant()

    def open_calculator(self):
        class Calculator(tk.Tk):
            def __init__(self):
                super().__init__()
                self.title('Calculator')
                self.resizable(False, False)
                self.create_widgets()

            def create_widgets(self):
                self.display = tk.Entry(self, width=20, font=('Arial', 16))
                self.display.grid(row=0, column=0, columnspan=4, pady=10)

                buttons = [
                    ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('/', 1, 3),
                    ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('*', 2, 3),
                    ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('-', 3, 3),
                    ('0', 4, 0), ('C', 4, 1), ('=', 4, 2), ('+', 4, 3)
                ]

                for (text, row, column) in buttons:
                    self.create_button(text, row, column)

            def create_button(self, text, row, column):
                button = tk.Button(self, text=text, width=5, height=2, font=('Arial', 16),
                                   command=lambda: self.button_click(text))
                button.grid(row=row, column=column, padx=5, pady=5)

            def button_click(self, text):
                if text == 'C':
                    self.display.delete(0, tk.END)
                elif text == '=':
                    try:
                        result = eval(self.display.get())
                        self.display.delete(0, tk.END)
                        self.display.insert(0, str(result))
                    except:
                        self.display.delete(0, tk.END)
                        self.display.insert(0, 'Error')
                else:
                    self.display.insert(tk.END, text)

        calc = Calculator()
        calc.mainloop()

    def eyes_virtual_mouse(self):
        cam = cv2.VideoCapture(0)
        face_mesh = mp.solutions.face_mesh.FaceMesh(refine             = True)
        screen_w, screen_h = pyautogui.size()
        while True:
            _, frame = cam.read()
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            output = face_mesh.process(rgb_frame)
            landmark_points = output.multi_face_landmarks
            frame_h, frame_w, _ = frame.shape
            if landmark_points:
                landmarks = landmark_points[0].landmark
                for id, landmark in enumerate(landmarks[474:478]):
                    x = int(landmark.x * frame_w)
                    y = int(landmark.y * frame_h)
                    cv2.circle(frame, (x, y), 3, (0, 255, 0))
                    if id == 1:
                        screen_x = screen_w * landmark.x
                        screen_y = screen_h * landmark.y
                        pyautogui.moveTo(screen_x, screen_y)
                left = [landmarks[145], landmarks[159]]
                for landmark in left:
                    x = int(landmark.x * frame_w)
                    y = int(landmark.y * frame_h)
                    cv2.circle(frame, (x, y), 3, (0, 255, 255))
                if (left[0].y - left[1].y) < 0.004:
                    pyautogui.click()
                    pyautogui.sleep(1)
            cv2.imshow('Eye Controlled Mouse', frame)
            key = cv2.waitKey(1)
            if key == ord('q'):
                break

        cam.release()
        cv2.destroyAllWindows()

    def virtual_mouse(self):
        cap = cv2.VideoCapture(0)
        hand_detector = mp.solutions.hands.Hands()
        drawing_utils = mp.solutions.drawing_utils
        screen_width, screen_height = pyautogui.size()
        index_y = 0

        while True:
            _, frame = cap.read()
            frame = cv2.flip(frame, 1)
            frame_height, frame_width, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            output = hand_detector.process(rgb_frame)
            hands = output.multi_hand_landmarks
            if hands:
                for hand in hands:
                    drawing_utils.draw_landmarks(frame, hand)
                    landmarks = hand.landmark
                    for id, landmark in enumerate(landmarks):
                        x = int(landmark.x * frame_width)
                        y = int(landmark.y * frame_height)
                        if id == 8:
                            cv2.circle(frame, (x, y), 10, (0, 255, 255), -1)
                            index_x = screen_width / frame_width * x
                            index_y = screen_height / frame_height * y

                        if id == 4:
                            cv2.circle(frame, (x, y), 10, (0, 255, 255), -1)
                            thumb_x = screen_width / frame_width * x
                            thumb_y = screen_height / frame_height * y
                            if abs(index_y - thumb_y) < 40:
                                pyautogui.click()
                                pyautogui.sleep(1)
                            elif abs(index_y - thumb_y) < 300:
                                pyautogui.moveTo(index_x, index_y)
            cv2.imshow('Virtual Mouse', frame)
            key = cv2.waitKey(1)
            if key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def check_internet_speed(self):
        st = speedtest.Speedtest()
        self.talk("Testing download speed...")
        download_speed = st.download() / 1000000
        self.talk(f"Download speed: {download_speed:.2f} Mbps")
        self.talk("Testing upload speed...")
        upload_speed = st.upload() / 1000000
        self.talk(f"Upload speed: {upload_speed:.2f} Mbps")

    def check_battery(self):
        battery = psutil.sensors_battery()
        if battery is not None:
            percentage = battery.percent
            self.talk(f"Our system has {percentage} percent battery")
            if percentage >= 75:
                self.talk("We have enough power to continue our work")
            elif 40 <= percentage <= 74:
                self.talk("We should connect our system to a charging point to charge our battery")
            elif 15 <= percentage <= 30:
                self.talk("We don't have enough power to work, please connect to charging")
            elif percentage <= 14:
                self.talk("We have very low power, the system will shutdown soon")
        else:
            self.talk("Battery information not available")

    def init_gui(self):
        self.root = tk.Tk()
        self.root.title("ZERO: THE VIRTUAL ASSISTANT")
        self.root.geometry("1600x1800")

        img = Image.open('zero.png')
        width, height = img.size
        new_width = 800
        new_height = int(height * (new_width / width))
        img = img.resize((new_width, new_height), resample=Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        img_label = tk.Label(self.root, image=photo)
        img_label.image = photo
        img_label.pack(side='right', padx=10)

        compText = tk.StringVar()
        userText = tk.StringVar()
        userText.set('ZERO: THE VIRTUAL ASSISTANT')

        top = tk.Message(textvariable=userText, bg='gray', fg='white')
        top.config(font=("Ariel", 50, 'bold'))
        top.pack(side='top', fill='both', expand='yes')

        self.assistant_type_var = tk.StringVar()
        self.assistant_type_var.set('voice')
        assistant_type_label = tk.Label(self.root, text='Select assistant type:', font=("Ariel", 20))
        assistant_type_label.pack(side='top', pady=10)
        assistant_type_frame = tk.Frame(self.root)
        assistant_type_frame.pack(side='top')
        voice_radio = tk.Radiobutton(assistant_type_frame, text='Voice Assistant', font=("Ariel", 16),
                                     variable=self.assistant_type_var, value='voice')
        voice_radio.pack(side='left', padx=20)
        text_radio = tk.Radiobutton(assistant_type_frame, text='Text Assistant', font=("Ariel", 16),
                                    variable=self.assistant_type_var, value='text')
        text_radio.pack(side='left', padx=20)

        start_btn = tk.Button(self.root, text='Start Assistant', font=("Arial", 20), fg="white", width=50, height=1,
                              bg='green', command=self.start_assistant)
        start_btn.pack(side='top', pady=10)

        self.root.mainloop()

if __name__ == "__main__":
    assistant = ZeroAssistant()
