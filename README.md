# Smart Pantry 🥫
Designed and prototyped in 36 hours for Starkhacks

## What it does
Smart Pantry is an AI-powered inventory management system. When the pantry door is opened, a camera automatically captures an image of the shelf, which is processed by Gemini to identify inventory. This is stored and is used to recommend recipes and keep track of products that are going bad.

## How we built it
The core of the system is a Rubik Pi C6490P running a Flask web server on Ubuntu. We integrated a MIPI CSI ribbon camera using a to handle image capture. For the "thinking" phase, we utilized Google Cloud Vertex AI and the gemini-2.5-flash-lite model for analysis. An ESP32 micro-controller relays door status and controls LEDs.
