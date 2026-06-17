import cv2
import mediapipe as mp
import numpy as np
import math, os, time
from datetime import datetime
from PIL import Image, ImageTk, ImageOps
import tkinter as tk
from tkinter import filedialog, messagebox

# ==========================================
# 1. NEW SCIENTIFIC THERMAL PALETTES (FROM IMAGES)
# ==========================================

def create_colormap(palette_colors):
    palette = np.array(palette_colors, dtype=np.float32)
    n = len(palette)
    stops = np.linspace(0, 255, n)
    x = np.arange(256)
    cmap = np.zeros((256, 3), dtype=np.uint8)
    for ch in range(3):
        cmap[:, ch] = np.interp(x, stops, palette[:, ch]).astype(np.uint8)
    return cmap

# COOL: Inspired by the "Rainbow Eyes" reference
# Deep Blue -> Cyan -> Green -> Yellow -> Hot Pink
COOL_PALETTE_REF = [
    (10, 10, 60),    # Deep Cold
    (0, 100, 255),   # Blue
    (0, 255, 100),   # Green transition
    (255, 255, 0),   # Yellow Heat
    (255, 50, 150),  # Hot Magenta peak
]

# WARM: Inspired by the "Ironbow Dog" reference
# Black -> Purple -> Crimson -> Orange -> White
WARM_PALETTE_REF = [
    (5, 5, 10),      # Black Background
    (60, 0, 100),    # Deep Purple
    (180, 0, 40),    # Crimson
    (255, 100, 0),   # Bright Orange
    (255, 220, 100), # Golden Yellow
    (255, 255, 230)  # White Hot
]

COOL_CMAP = create_colormap(COOL_PALETTE_REF)
WARM_CMAP = create_colormap(WARM_PALETTE_REF)

def apply_thermal_bloom(image, sigma=15, strength=0.4):
    """Subtle infrared glow for high-heat areas."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, mask = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY)
    mask_3d = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
    bloom = cv2.GaussianBlur(mask_3d, (0, 0), sigma)
    return cv2.addWeighted(image, 1.0, bloom, strength, 0)

# ==========================================
# 2. PHYSICS & VECTOR SMEAR ENGINE
# ==========================================

class SmoothPhysics:
    def __init__(self):
        self.f_sep = 0.0
        self.vx = 0.0 
        self.vy = 0.0
        self.prev_pos = None
        self.alpha = 0.15 

    def update(self, lm):
        # Finger Separation (Thumb to Pinky)
        p1 = np.array([lm[4].x, lm[4].y])
        p2 = np.array([lm[20].x, lm[20].y])
        self.f_sep = self.f_sep * (1 - self.alpha) + np.linalg.norm(p1 - p2) * self.alpha
        
        # Velocity Tracking (Wrist movement)
        curr_pos = np.array([lm[0].x, lm[0].y])
        if self.prev_pos is not None:
            # Scale velocity for visual impact
            self.vx = self.vx * 0.7 + (curr_pos[0] - self.prev_pos[0]) * 350
            self.vy = self.vy * 0.7 + (curr_pos[1] - self.prev_pos[1]) * 350
        self.prev_pos = curr_pos

        return {
            "sep": np.clip(self.f_sep * 2.5, 0, 1),
            "vx": self.vx, "vy": self.vy,
            "mag": math.sqrt(self.vx**2 + self.vy**2)
        }

class ElasticField:
    """Persistent mesh that follows hand trajectory."""
    def __init__(self, h, w):
        self.h, self.w = h, w
        self.map_x = np.zeros((h, w), dtype=np.float32)
        self.map_y = np.zeros((h, w), dtype=np.float32)
        self.stiffness = np.ones((h, w), dtype=np.float32)

    def update_stiffness(self, gray):
        edges = cv2.Canny(gray, 50, 150)
        edges = cv2.GaussianBlur(edges.astype(np.float32), (15, 15), 0)
        # Identity protection: edges move 80% less than flat zones
        self.stiffness = 1.0 - np.clip(edges / (edges.max() + 1e-5), 0, 0.8)

    def apply_directional_smear(self, phys, fluidity):
        # Force = (Hand Direction) * (Hand Spread) * (Heat Intensity)
        force_x = phys['vx'] * phys['sep'] * 15
        force_y = phys['vy'] * phys['sep'] * 15
        self.map_x += force_x * fluidity * self.stiffness
        self.map_y += force_y * fluidity * self.stiffness

    def heal(self, rate=0.9):
        self.map_x *= rate
        self.map_y *= rate

    def get_warp(self):
        gx, gy = np.meshgrid(np.arange(self.w), np.arange(self.h))
        return (gx + self.map_x).astype(np.float32), (gy + self.map_y).astype(np.float32)

# ==========================================
# 3. HEATWAVE STUDIO MAIN APP
# ==========================================

class HeatWaveStudio:
    def __init__(self, root):
        self.root = root
        root.title("HeatWave Studio | Scientific Thermal HUD")
        root.geometry("1180x780")
        root.configure(bg="#050508")

        # State
        self.orig_pil = None
        self.palette_mode = 'ORIGINAL'
        self.struct_mode = 'NORMAL'
        self.physics = SmoothPhysics()
        self.elastic = None
        self.tracking = False
        self.cap = None

        # UI Architecture
        self.img_panel = tk.Label(root, bg="#020205", bd=0)
        self.img_panel.place(x=20, y=20, width=880, height=640)
        
        self._setup_sidebar()
        self.mp_hands = mp.solutions.hands.Hands(min_detection_confidence=0.8, min_tracking_confidence=0.8)

    def _setup_sidebar(self):
        sx = 920
        tk.Label(self.root, text="HEATWAVE STUDIO", bg="#050508", fg="#00d4ff", font=("Impact", 16)).place(x=sx, y=20)
        
        btn_c = {"bg":"#12121e", "fg":"#8899aa", "activebackground":"#1a1a2e", "bd":0, "font":("Arial", 10)}
        tk.Button(self.root, text="Load Image", command=self.load_image, **btn_c).place(x=sx, y=70, width=230, height=45)
        self.cam_btn = tk.Button(self.root, text="Start Tracker", command=self.toggle_tracking, **btn_c)
        self.cam_btn.place(x=sx, y=125, width=230, height=45)
        tk.Button(self.root, text="Save PNG", command=self.save_image, **btn_c).place(x=sx, y=180, width=230, height=45)

        tk.Label(self.root, text="LIVE HUD FEED", bg="#050508", fg="#445566", font=("Arial", 8)).place(x=sx, y=245)
        self.hud_view = tk.Label(self.root, bg="#000", bd=1, relief="solid")
        self.hud_view.place(x=sx, y=265, width=230, height=170)

        guide = "Thumbs Up : Reset (Original)\nPeace Sign : Cool (Rainbow Scale)\n3-Finger Spread : Warm (Ironbow Scale)\nOK Sign : Smear (Drag Image)\nRock On : Mosaic (Halftone)\nPinch : Split Screen\nHand Spread : Depth Field"
        tk.Label(self.root, text=guide, bg="#1D1D32", fg="#7fc29d", justify="left", font=("Arial", 9)).place(x=sx, y=455)

    def load_image(self):
        path = filedialog.askopenfilename()
        if path:
            self.orig_pil = Image.open(path).convert('RGB')
            w, h = self.orig_pil.size
            scale = min(880/w, 640/h, 1.0)
            tw, th = int(w*scale), int(h*scale)
            self.elastic = ElasticField(th, tw)
            self.elastic.update_stiffness(np.array(ImageOps.grayscale(self.orig_pil.resize((tw, th)))))
            self.palette_mode = 'ORIGINAL'
            self._render()

    def toggle_tracking(self):
        if not self.tracking:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.tracking = True
                self.cam_btn.config(text="Stop Tracker", fg="#00ffcc")
                self._run()
        else:
            self.tracking = False
            self.cap.release()
            self.cam_btn.config(text="Start Tracker", fg="#8899aa")

    def _run(self):
        if not self.tracking: return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.mp_hands.process(rgb)
            if res.multi_hand_landmarks:
                lm = res.multi_hand_landmarks[0]
                metrics = self.physics.update(lm.landmark)
                self._map_gestures(lm.landmark)
                self._render(metrics)
                mp.solutions.drawing_utils.draw_landmarks(frame, lm, mp.solutions.hands.HAND_CONNECTIONS)
            else:
                self._render()
            
            # Update HUD
            hud = cv2.resize(frame, (230, 170))
            hud_tk = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(hud, cv2.COLOR_BGR2RGB)))
            self.hud_view.imgtk = hud_tk
            self.hud_view.configure(image=hud_tk)
        self.root.after(10, self._run)

    def _map_gestures(self, lm):
        # Finger detection
        idx = lm[8].y < lm[6].y
        mid = lm[12].y < lm[10].y
        rng = lm[16].y < lm[14].y
        pnk = lm[20].y < lm[18].y
        pinch = np.linalg.norm(np.array([lm[4].x, lm[4].y]) - np.array([lm[8].x, lm[8].y]))

        if lm[4].y < lm[3].y and lm[4].y < lm[5].y and not idx: # Thumb Reset
            self.palette_mode = 'ORIGINAL'; self.struct_mode = 'NORMAL'
        elif idx and mid and not rng and not pnk: # V-Cool
            self.palette_mode = 'COOL'
        elif idx and mid and pnk and not rng: # W-Warm
            self.palette_mode = 'WARM'
        elif pinch < 0.05 and mid and rng and pnk: # OK-Smear
            self.struct_mode = 'SMEAR'
        elif idx and pnk and not mid and not rng: # Rock-Mosaic
            self.struct_mode = 'MOSAIC'
        elif idx and mid and rng and not pnk: # 3-Finger-Split
            self.struct_mode = 'SPLIT'
        elif all([idx, mid, rng, pnk]): # Palm-Depth
            self.struct_mode = 'DEPTH'

    def _render(self, m=None):
        if self.orig_pil is None: return
        w, h = self.orig_pil.size
        scale = min(880/w, 640/h, 1.0)
        img_np = np.array(self.orig_pil.resize((int(w*scale), int(h*scale)), Image.LANCZOS))
        
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        if self.palette_mode == 'ORIGINAL':
            proc = img_np
            fluid = np.ones_like(gray, dtype=np.float32) * 0.4
        else:
            cmap = COOL_CMAP if self.palette_mode == 'COOL' else WARM_CMAP
            proc = cmap[cv2.createCLAHE(clipLimit=3.0).apply(gray)]
            fluid = gray.astype(np.float32) / 255.0

        if self.elastic:
            if m:
                # Directions Smear follows Hand Vector
                if self.struct_mode == 'SMEAR' and m['mag'] > 0.1:
                    self.elastic.apply_directional_smear(m, fluid)
                    self.elastic.heal(0.98) # Slow return
                else:
                    self.elastic.heal(0.88)
            else:
                self.elastic.heal(0.82)

            mx, my = self.elastic.get_warp()
            proc = cv2.remap(proc, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

            # Extra structure logic
            if m:
                if self.struct_mode == 'MOSAIC':
                    proc = self._mosaic(proc, m)
                elif self.struct_mode == 'SPLIT':
                    proc = self._split(proc, m)
                elif self.struct_mode == 'DEPTH':
                    proc = self._depth(proc, m)
            
            proc = apply_thermal_bloom(proc, sigma=5+int((m['mag'] if m else 0)*0.5))

        tk_img = ImageTk.PhotoImage(Image.fromarray(proc))
        self.img_panel.imgtk = tk_img
        self.img_panel.configure(image=tk_img)

    def _mosaic(self, img, m):
        h, w = img.shape[:2]
        d = int(6 + m['sep'] * 18)
        res = np.zeros_like(img)
        for y in range(0, h-d, d):
            for x in range(0, w-d, d):
                c = np.mean(img[y:y+d, x:x+d], axis=(0,1)).astype(np.uint8)
                cv2.circle(res, (x+d//2, y+d//2), int(d*0.44), c.tolist(), -1, cv2.LINE_AA)
        return res

    def _split(self, img, m):
        h, w = img.shape[:2]
        gap = int(m['sep'] * (w * 0.4))
        res = np.zeros_like(img)
        res[:, :w//2-gap//2] = img[:, :w//2-gap//2]
        res[:, w//2+gap//2:] = img[:, w//2+gap//2:]
        return res

    def _depth(self, img, m):
        h, w = img.shape[:2]
        out = img.copy()
        for i in range(1, 4):
            s = 1.0 - (i * 0.1 * (m['sep'] + 0.5))
            layer = cv2.resize(img, (int(w*s), int(h*s)))
            y, x = (h-layer.shape[0])//2, (w-layer.shape[1])//2
            cv2.addWeighted(out[y:y+layer.shape[0], x:x+layer.shape[1]], 0.7, layer, 0.3, 0, out[y:y+layer.shape[0], x:x+layer.shape[1]])
        return out

    def save_image(self):
        if self.img_panel.imgtk:
            path = filedialog.asksaveasfilename(defaultextension=".png")
            if path:
                Image.fromarray(np.array(self.img_panel.imgtk)).save(path)
                messagebox.showinfo("Export", "Thermal art saved.")

if __name__ == "__main__":
    root = tk.Tk()
    HeatWaveStudio(root)
    root.mainloop()