# HeatWave Studio

> Real-time thermal visualization, gesture-driven image manipulation, and physics-based rendering — all packed into a desktop application.

HeatWave Studio is an experimental computer vision project that turns static images into interactive thermal artwork using hand tracking, procedural effects, and custom rendering pipelines.

Instead of adjusting sliders and menus, you manipulate the visual output directly through gestures, creating a more natural and immersive editing experience.

---

## What It Does

HeatWave combines computer vision, image processing, and lightweight simulation systems to create a real-time visual playground.

### Core Features

- Real-time hand tracking with MediaPipe
- Custom thermal visualization pipelines
- Dynamic color grading using scientific palettes
- Physics-driven image warping
- Motion-aware directional smearing
- Thermal bloom rendering
- Gesture-controlled effect switching
- Image import and export
- Interactive desktop interface

---

## Under the Hood

The project isn't just applying filters.

HeatWave continuously analyzes hand landmarks, calculates motion vectors, tracks gesture states, and feeds those signals into a custom rendering engine.

The pipeline includes:

- Hand pose estimation
- Velocity tracking
- Elastic deformation fields
- Spatial remapping
- Thermal color mapping
- Bloom synthesis
- Procedural visual effects

The result is an image that reacts to movement rather than button clicks.

---

## Gesture Mapping

| Gesture | Action |
|----------|---------|
| 👍 Thumbs Up | Reset |
| ✌️ Peace Sign | Cool Thermal Mode |
| 🤟 Three-Finger Gesture | Warm Thermal Mode |
| 👌 OK Sign | Physics Smear |
| 🤘 Rock Gesture | Mosaic Rendering |
| 🤏 Pinch | Split View |
| ✋ Open Palm | Depth Effect |



---

## Tech Stack

### Computer Vision
- OpenCV
- MediaPipe

### Scientific Computing
- NumPy

### GUI
- Tkinter
- Pillow

### Rendering Concepts
- Elastic Mesh Distortion
- Thermal Visualization
- Motion Vector Processing
- Bloom Effects
- Procedural Graphics

---

## Project Structure

```text
HeatWave/
│
├── hand_photo_filter.py
├── make_sample_luts.py
│
├── luts/
│   ├── cool
│   ├── cool_c2a
│   ├── warm
│   └── warm_w2b
```

---

## Getting Started

```bash
pip install -r requirements.txt
python hand_photo_filter.py
```

---

## Why I Built This

Most image filters are passive.

I wanted to explore what happens when image processing becomes interactive — where gestures, motion, and visual feedback are part of the same system.

HeatWave started as a thermal imaging experiment and gradually evolved into a gesture-controlled visual effects engine.

---

## Future Experiments

- Real-time webcam processing
- Multi-hand interactions
- GPU accelerated rendering
- Advanced fluid simulations
- Custom LUT editor
- AR integration

---

## Developer

**Suruchi Dhawan**

Building weird things with Python, computer vision, and whatever idea sounds interesting at 2 AM.

---
#  ִֶָ❍.๋࣭ ⭑⚝. ݁ ˖.˚ . ݁
