import cv2
import mediapipe as mp
import numpy as np
import random

# ---------------- INIT ----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.8,
    min_tracking_confidence=0.85
)

mp_draw = mp.solutions.drawing_utils

# 🔥 FIXED CAMERA INIT
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Camera not detected")
    exit()

cap.set(3, 1280)
cap.set(4, 720)

cv2.namedWindow("ANIME BATTLE MODE", cv2.WINDOW_NORMAL)

tip_ids = [4, 8, 12, 16, 20]

prev_positions = [0, 0]
cooldowns = [0, 0]
charge = [0, 0]
lightning_timer = [0, 0]

projectiles = []
fire_particles = []

# ---------------- SMOOTH ----------------
def smooth(prev, curr, alpha=0.7):
    return int(prev * alpha + curr * (1 - alpha))

# ---------------- FIRE ----------------
def spawn_fire(x, y):
    for _ in range(8):
        fire_particles.append([
            x + random.randint(-10, 10),
            y,
            random.randint(-2, 2),
            random.randint(-8, -3),
            random.randint(5, 12)
        ])

def update_fire(frame):
    global fire_particles
    new_particles = []

    for p in fire_particles:
        p[0] += p[2]
        p[1] += p[3]
        p[4] -= 1

        if p[4] > 0:
            new_particles.append(p)

            intensity = p[4]
            color = (0, min(255, 100 + intensity*12), 255)

            cv2.circle(frame, (p[0], p[1]), p[4], color, -1)

    fire_particles = new_particles

# ---------------- LIGHTNING ----------------
def draw_lightning(frame, x, y):
    points = [(x, y)]

    for _ in range(12):
        nx = points[-1][0] + random.randint(-25, 25)
        ny = points[-1][1] - random.randint(20, 40)
        points.append((nx, ny))

    overlay = frame.copy()

    for i in range(len(points)-1):
        cv2.line(overlay, points[i], points[i+1], (255,255,255), 5)

    overlay = cv2.GaussianBlur(overlay, (21,21), 0)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    for i in range(len(points)-1):
        cv2.line(frame, points[i], points[i+1], (255,255,0), 2)

    for _ in range(3):
        bx, by = random.choice(points)
        for _ in range(4):
            nx = bx + random.randint(-15, 15)
            ny = by - random.randint(10, 25)
            cv2.line(frame, (bx, by), (nx, ny), (255,255,255), 1)
            bx, by = nx, ny

# ---------------- EXPLOSION ----------------
def explosion(frame, x, y):
    overlay = frame.copy()

    for i in range(1, 10):
        radius = i * 12
        cv2.circle(overlay, (x, y), radius, (0,255,255), 2)

    overlay = cv2.GaussianBlur(overlay, (31,31), 0)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

# ---------------- PROJECTILES ----------------
def spawn_projectile(x, y, kind, direction):
    projectiles.append([x, y, direction, kind])

def update_projectiles(frame):
    global projectiles
    new_list = []

    for p in projectiles:
        p[0] += p[2]

        if p[3] == "FIRE":
            cv2.circle(frame, (p[0], p[1]), 20, (0,0,255), -1)
        else:
            draw_lightning(frame, p[0], p[1])

        if p[0] < 50 or p[0] > frame.shape[1]-50:

            # camera shake
            shake_x = random.randint(-8, 8)
            shake_y = random.randint(-8, 8)
            frame[:] = np.roll(frame, shift=shake_x, axis=1)
            frame[:] = np.roll(frame, shift=shake_y, axis=0)

            explosion(frame, p[0], p[1])
        else:
            new_list.append(p)

    projectiles = new_list

# ---------------- MAIN LOOP ----------------
while True:
    success, img = cap.read()

    if not success:
        print("⚠️ Frame not captured")
        continue   # 🔥 don't break → keep trying

    img = cv2.flip(img, 1)
    h, w, _ = img.shape

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:

            lm_list = []
            for lm in hand_landmarks.landmark:
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append((cx, cy))

            fingers = []
            fingers.append(1 if lm_list[4][0] > lm_list[3][0] else 0)

            for i in range(1,5):
                fingers.append(1 if lm_list[tip_ids[i]][1] < lm_list[tip_ids[i]-2][1] else 0)

            total = fingers.count(1)

            gesture = "NONE"
            if total <= 1:
                gesture = "FIRE"
            elif total == 5:
                gesture = "LIGHTNING"

            cx, cy = lm_list[9]
            player = 0 if cx < w//2 else 1

            cx = smooth(prev_positions[player], cx)

            if gesture != "NONE":
                charge[player] += 1
            else:
                charge[player] = 0

            if 5 < charge[player] < 15:
                overlay = img.copy()
                cv2.circle(overlay, (cx, cy), 60 + charge[player]*2, (255,255,0), -1)
                overlay = cv2.GaussianBlur(overlay, (51,51), 0)
                cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)

            if player == 0 and gesture == "FIRE":
                spawn_fire(cx, cy)

                if charge[player] > 15 and cooldowns[player] == 0:
                    spawn_projectile(cx, cy, "FIRE", 20)
                    cooldowns[player] = 20
                    charge[player] = 0

            if player == 1 and gesture == "LIGHTNING":

                if charge[player] > 15 and cooldowns[player] == 0:
                    lightning_timer[player] = 2
                    spawn_projectile(cx, cy, "LIGHTNING", -25)
                    cooldowns[player] = 25
                    charge[player] = 0

            if lightning_timer[player] > 0:
                draw_lightning(img, cx, cy)

                flash = np.full_like(img, 255)
                cv2.addWeighted(flash, 0.5, img, 0.5, 0, img)

                lightning_timer[player] -= 1

            prev_positions[player] = cx

            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    for i in range(2):
        if cooldowns[i] > 0:
            cooldowns[i] -= 1

    update_fire(img)
    update_projectiles(img)

    cv2.putText(img, "LEFT: FIRE 🔥", (30,50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

    cv2.putText(img, "RIGHT: LIGHTNING ⚡", (w-320,50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

    cv2.imshow("ANIME BATTLE MODE", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()