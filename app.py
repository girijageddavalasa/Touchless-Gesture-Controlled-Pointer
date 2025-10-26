import cv2
import mediapipe as mp
import pyautogui
import math
import subprocess
import time
import threading
import speech_recognition as sr

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Get screen size
screen_width, screen_height = pyautogui.size()
pyautogui.FAILSAFE = False

smooth_factor = 5
prev_x, prev_y = 0, 0
speed_scale = 1.5
frame_width, frame_height = 640, 480

long_select_active = False
recording_active = False
keyboard_open_cooldown = 0

def count_fingers(hand_landmarks):
    fingers = {
        'thumb': False,
        'index': False,
        'middle': False,
        'ring': False,
        'pinky': False
    }
    if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x:
        fingers['thumb'] = True
    if hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y:
        fingers['index'] = True
    if hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y:
        fingers['middle'] = True
    if hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y:
        fingers['ring'] = True
    if hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y:
        fingers['pinky'] = True
    return fingers

def open_onscreen_keyboard():
    try:
        pyautogui.hotkey('winleft', 'ctrl', 'o')
        time.sleep(1)
    except Exception as e:
        print(f"Could not open on-screen keyboard: {e}")

def audio_record_and_paste():
    global recording_active
    r = sr.Recognizer()
    mic = sr.Microphone()
    print("Recording started... Speak now")
    with mic as source:
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, phrase_time_limit=5)
    try:
        text = r.recognize_google(audio)
        print(f"Recognized text: {text}")
        pyautogui.write(text)
    except Exception as e:
        print("Audio recognition failed:", e)
    recording_active = False

print("Hand Gesture Controller Started!")
print("- Index + Middle finger: Move pointer")
print("- Index finger only: Left click")
print("- Middle finger only: Right click")
print("- Three fingers (Index + Middle + Ring): Scroll down")
print("- Four fingers (Index + Middle + Ring + Pinky): Scroll up")
print("- Index + Pinky: Open on-screen keyboard")
print("- Thumb only: Press Enter")
print("- Five fingers: Long select (hold click and move)")
print("- Super finger (Pinky + Ring + Middle): Voice to text paste")
print("Press 'q' to quit")

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if keyboard_open_cooldown > 0:
        keyboard_open_cooldown -= 1

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            fingers = count_fingers(hand_landmarks)

            index_tip = hand_landmarks.landmark[8]
            x_raw = int(index_tip.x * screen_width)
            y_raw = int(index_tip.y * screen_height)

            x = int((x_raw - screen_width / 2) * speed_scale + screen_width / 2)
            y = int((y_raw - screen_height / 2) * speed_scale + screen_height / 2)

            curr_x = prev_x + (x - prev_x) / smooth_factor
            curr_y = prev_y + (y - prev_y) / smooth_factor

            fingers_up = sum(fingers.values())

            # --- ORDER MATTERS! Five fingers must be checked first ---
            if all(fingers.values()):
                if not long_select_active:
                    pyautogui.mouseDown()
                    long_select_active = True
                pyautogui.moveTo(curr_x, curr_y)
                cv2.putText(frame, "Long Select (Hold and Move)", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

            # Scroll up (check AFTER five-finger long select)
            elif fingers['index'] and fingers['middle'] and fingers['ring'] and fingers['pinky']:
                pyautogui.scroll(40)
                cv2.putText(frame, "Scroll Up", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                if long_select_active:
                    pyautogui.mouseUp()
                    long_select_active = False

            # Scroll down
            elif fingers['index'] and fingers['middle'] and fingers['ring'] and not fingers['pinky']:
                pyautogui.scroll(-40)
                cv2.putText(frame, "Scroll Down", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                if long_select_active:
                    pyautogui.mouseUp()
                    long_select_active = False

            # Move pointer
            elif fingers['index'] and fingers['middle'] and not fingers['ring'] and not fingers['pinky']:
                pyautogui.moveTo(curr_x, curr_y)
                cv2.putText(frame, "Moving Pointer", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                if long_select_active:
                    pyautogui.mouseUp()
                    long_select_active = False

            # Left click - index finger only
            elif fingers['index'] and not fingers['middle'] and not fingers['ring'] and not fingers['pinky'] and not fingers['thumb'] and keyboard_open_cooldown == 0:
                pyautogui.click(button='left')
                cv2.putText(frame, "Left Click", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.waitKey(300)
                if long_select_active:
                    pyautogui.mouseUp()
                    long_select_active = False

            # Right click - middle finger only
            elif fingers['middle'] and not fingers['index'] and not fingers['ring'] and not fingers['pinky'] and not fingers['thumb'] and keyboard_open_cooldown == 0:
                pyautogui.click(button='right')
                cv2.putText(frame, "Right Click", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 128, 0), 2)
                cv2.waitKey(300)
                if long_select_active:
                    pyautogui.mouseUp()
                    long_select_active = False

            # Open keyboard - index + pinky only
            elif fingers['index'] and fingers['pinky'] and not fingers['middle'] and not fingers['ring'] and keyboard_open_cooldown == 0:
                open_onscreen_keyboard()
                keyboard_open_cooldown = 20
                cv2.putText(frame, "Opening Keyboard", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 165, 0), 2)
                if long_select_active:
                    pyautogui.mouseUp()
                    long_select_active = False

            # Press Enter - thumb only
            elif fingers['thumb'] and not fingers['index'] and not fingers['middle'] and not fingers['ring'] and not fingers['pinky']:
                pyautogui.press('enter')
                cv2.putText(frame, "Enter Pressed", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (128, 0, 128), 2)
                cv2.waitKey(300)
                if long_select_active:
                    pyautogui.mouseUp()
                    long_select_active = False

            # Super finger: only pinky + ring + middle
            elif fingers['pinky'] and fingers['ring'] and fingers['middle'] and not fingers['index'] and not fingers['thumb']:
                if not recording_active:
                    recording_active = True
                    cv2.putText(frame, "Recording Audio", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    threading.Thread(target=audio_record_and_paste, daemon=True).start()

            else:
                if long_select_active:
                    pyautogui.mouseUp()
                    long_select_active = False

            prev_x, prev_y = curr_x, curr_y
            cv2.putText(frame, f"Fingers: {fingers_up}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow('Hand Gesture Controller', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
hands.close()
