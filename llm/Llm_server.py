"""
NutriTrack — Llm_server.py
Multimodal LLM Inference Server  (v3 — Ollama Edition)

Engine priority:
  1. Ollama Local  — Qwen2-VL-7B  (6-8 s CPU / <2 s GPU, zero API key)  ← PRIMARY
  2. Moondream2    — local 1.8B fallback via transformers

Nutrition data (priority):
  1. Built-in NUTRITION_DB  — 80 common / Indian foods
  2. USDA FoodData Central  — 300k+ foods (needs USDA_API_KEY)
  3. Hardcoded estimates    — 30% confidence floor

Port: 5002

Quick-start (Ollama path — recommended):
    1. Install Ollama  →  https://ollama.com/download
    2. ollama pull qwen2-vl:7b
    3. pip install flask flask-cors flask-limiter python-dotenv requests Pillow
    4. python Llm_server.py
"""

import io, os, re, sys, json, time, base64, argparse, threading, queue
import requests as http_requests
from dotenv import load_dotenv
load_dotenv()
from PIL import Image
from flask import Flask, request, jsonify

# Windows Console Unicode/Emoji support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  NUTRITION DATABASE  (80 items — Indian + global)
# ──────────────────────────────────────────────────────────────────────────────

NUTRITION_DB = {
    # ── Fruits ──
    'apple':          {'cal':95,  'pro':0.5,'carb':25, 'fat':0.3,'fiber':4.4,'sugar':19,'sodium':2,   'chol':0,  'serving':'1 medium (182g)'},
    'banana':         {'cal':105, 'pro':1.3,'carb':27, 'fat':0.4,'fiber':3.1,'sugar':14,'sodium':1,   'chol':0,  'serving':'1 medium (118g)'},
    'mango':          {'cal':99,  'pro':1.4,'carb':25, 'fat':0.6,'fiber':2.6,'sugar':22,'sodium':2,   'chol':0,  'serving':'1 cup sliced (165g)'},
    'orange':         {'cal':62,  'pro':1.2,'carb':15, 'fat':0.2,'fiber':3.1,'sugar':12,'sodium':0,   'chol':0,  'serving':'1 medium (131g)'},
    'watermelon':     {'cal':46,  'pro':0.9,'carb':12, 'fat':0.2,'fiber':0.6,'sugar':9, 'sodium':2,   'chol':0,  'serving':'2 cups diced (280g)'},
    'grapes':         {'cal':104, 'pro':1.1,'carb':27, 'fat':0.2,'fiber':1.4,'sugar':23,'sodium':3,   'chol':0,  'serving':'1 cup (151g)'},
    'strawberry':     {'cal':49,  'pro':1.0,'carb':12, 'fat':0.5,'fiber':3.0,'sugar':7, 'sodium':2,   'chol':0,  'serving':'1 cup (152g)'},
    'pineapple':      {'cal':82,  'pro':0.9,'carb':22, 'fat':0.2,'fiber':2.3,'sugar':16,'sodium':2,   'chol':0,  'serving':'1 cup chunks (165g)'},
    # ── Indian staples ──
    'biryani':        {'cal':350, 'pro':15, 'carb':48, 'fat':12, 'fiber':2,  'sugar':3, 'sodium':480, 'chol':45, 'serving':'1 plate (300g)'},
    'butter chicken': {'cal':300, 'pro':25, 'carb':12, 'fat':18, 'fiber':2,  'sugar':6, 'sodium':520, 'chol':80, 'serving':'1 bowl (200g)'},
    'chole bhature':  {'cal':550, 'pro':16, 'carb':72, 'fat':22, 'fiber':8,  'sugar':4, 'sodium':640, 'chol':0,  'serving':'1 plate (350g)'},
    'dal':            {'cal':170, 'pro':9,  'carb':22, 'fat':6,  'fiber':5,  'sugar':3, 'sodium':320, 'chol':10, 'serving':'1 bowl (200g)'},
    'dal makhani':    {'cal':198, 'pro':10, 'carb':24, 'fat':8,  'fiber':6,  'sugar':3, 'sodium':380, 'chol':20, 'serving':'1 bowl (200g)'},
    'dosa':           {'cal':168, 'pro':4,  'carb':30, 'fat':4,  'fiber':1,  'sugar':1, 'sodium':200, 'chol':0,  'serving':'1 dosa (80g)'},
    'masala dosa':    {'cal':210, 'pro':5,  'carb':36, 'fat':6,  'fiber':2,  'sugar':2, 'sodium':380, 'chol':0,  'serving':'1 dosa (120g)'},
    'idli':           {'cal':58,  'pro':2,  'carb':11, 'fat':0.4,'fiber':0.5,'sugar':0, 'sodium':120, 'chol':0,  'serving':'1 piece (39g)'},
    'sambar':         {'cal':130, 'pro':6,  'carb':20, 'fat':3,  'fiber':5,  'sugar':4, 'sodium':480, 'chol':0,  'serving':'1 bowl (200g)'},
    'uttapam':        {'cal':220, 'pro':6,  'carb':36, 'fat':6,  'fiber':3,  'sugar':3, 'sodium':380, 'chol':0,  'serving':'1 piece (120g)'},
    'roti':           {'cal':71,  'pro':2.5,'carb':14, 'fat':0.9,'fiber':1.9,'sugar':0, 'sodium':2,   'chol':0,  'serving':'1 roti (30g)'},
    'paratha':        {'cal':280, 'pro':7,  'carb':38, 'fat':11, 'fiber':3,  'sugar':1, 'sodium':320, 'chol':0,  'serving':'1 paratha (80g)'},
    'naan':           {'cal':262, 'pro':8,  'carb':45, 'fat':5,  'fiber':2,  'sugar':3, 'sodium':530, 'chol':10, 'serving':'1 naan (90g)'},
    'paneer':         {'cal':290, 'pro':18, 'carb':8,  'fat':20, 'fiber':1,  'sugar':3, 'sodium':480, 'chol':55, 'serving':'100g'},
    'paneer tikka':   {'cal':290, 'pro':18, 'carb':8,  'fat':20, 'fiber':1,  'sugar':3, 'sodium':480, 'chol':55, 'serving':'4 pieces (150g)'},
    'rajma':          {'cal':220, 'pro':12, 'carb':36, 'fat':4,  'fiber':8,  'sugar':3, 'sodium':380, 'chol':0,  'serving':'1 bowl (200g)'},
    'pav bhaji':      {'cal':320, 'pro':8,  'carb':48, 'fat':11, 'fiber':4,  'sugar':6, 'sodium':680, 'chol':20, 'serving':'1 plate (250g)'},
    'vada pav':       {'cal':280, 'pro':6,  'carb':42, 'fat':10, 'fiber':3,  'sugar':3, 'sodium':400, 'chol':0,  'serving':'1 piece (120g)'},
    'samosa':         {'cal':150, 'pro':3,  'carb':20, 'fat':7,  'fiber':2,  'sugar':1, 'sodium':240, 'chol':0,  'serving':'1 piece (60g)'},
    'poha':           {'cal':180, 'pro':4,  'carb':32, 'fat':4,  'fiber':2,  'sugar':2, 'sodium':280, 'chol':0,  'serving':'1 bowl (150g)'},
    'upma':           {'cal':200, 'pro':5,  'carb':35, 'fat':5,  'fiber':3,  'sugar':2, 'sodium':350, 'chol':0,  'serving':'1 bowl (180g)'},
    'khichdi':        {'cal':190, 'pro':8,  'carb':32, 'fat':5,  'fiber':4,  'sugar':2, 'sodium':320, 'chol':10, 'serving':'1 bowl (200g)'},
    'chicken curry':  {'cal':260, 'pro':22, 'carb':10, 'fat':16, 'fiber':2,  'sugar':4, 'sodium':500, 'chol':70, 'serving':'1 bowl (200g)'},
    'momos':          {'cal':240, 'pro':10, 'carb':30, 'fat':9,  'fiber':2,  'sugar':2, 'sodium':480, 'chol':35, 'serving':'6 pieces (150g)'},
    'kebab':          {'cal':220, 'pro':22, 'carb':8,  'fat':12, 'fiber':1,  'sugar':2, 'sodium':480, 'chol':70, 'serving':'2 skewers (100g)'},
    'lassi':          {'cal':150, 'pro':6,  'carb':22, 'fat':4,  'fiber':0,  'sugar':18,'sodium':80,  'chol':15, 'serving':'1 glass (200ml)'},
    'mango lassi':    {'cal':180, 'pro':5,  'carb':32, 'fat':4,  'fiber':1,  'sugar':28,'sodium':60,  'chol':15, 'serving':'1 glass (200ml)'},
    'gulab jamun':    {'cal':175, 'pro':3,  'carb':30, 'fat':5,  'fiber':0,  'sugar':26,'sodium':80,  'chol':20, 'serving':'2 pieces (80g)'},
    'rasgulla':       {'cal':186, 'pro':4,  'carb':38, 'fat':2,  'fiber':0,  'sugar':34,'sodium':40,  'chol':0,  'serving':'2 pieces (100g)'},
    'kheer':          {'cal':180, 'pro':5,  'carb':30, 'fat':5,  'fiber':0,  'sugar':24,'sodium':80,  'chol':20, 'serving':'1 bowl (150g)'},
    # ── Global fast food ──
    'burger':         {'cal':354, 'pro':20, 'carb':29, 'fat':17, 'fiber':1,  'sugar':6, 'sodium':497, 'chol':52, 'serving':'1 burger (150g)'},
    'hamburger':      {'cal':354, 'pro':20, 'carb':29, 'fat':17, 'fiber':1,  'sugar':6, 'sodium':497, 'chol':52, 'serving':'1 burger (150g)'},
    'french fries':   {'cal':312, 'pro':3.4,'carb':41, 'fat':15, 'fiber':3.8,'sugar':0, 'sodium':210, 'chol':0,  'serving':'medium (150g)'},
    'pizza':          {'cal':266, 'pro':11, 'carb':33, 'fat':10, 'fiber':2.3,'sugar':3.6,'sodium':640,'chol':17, 'serving':'2 slices (200g)'},
    'sandwich':       {'cal':280, 'pro':12, 'carb':36, 'fat':9,  'fiber':3,  'sugar':4, 'sodium':620, 'chol':25, 'serving':'1 sandwich (180g)'},
    'hot dog':        {'cal':290, 'pro':11, 'carb':24, 'fat':18, 'fiber':1,  'sugar':4, 'sodium':670, 'chol':45, 'serving':'1 hot dog (150g)'},
    # ── Noodles / rice dishes ──
    'fried rice':     {'cal':242, 'pro':5,  'carb':42, 'fat':6,  'fiber':1,  'sugar':2, 'sodium':600, 'chol':40, 'serving':'1 bowl (200g)'},
    'noodles':        {'cal':220, 'pro':7,  'carb':40, 'fat':4,  'fiber':2,  'sugar':2, 'sodium':400, 'chol':0,  'serving':'1 bowl (200g)'},
    'ramen':          {'cal':436, 'pro':20, 'carb':58, 'fat':14, 'fiber':3,  'sugar':4, 'sodium':1260,'chol':55, 'serving':'1 bowl (450ml)'},
    'pad thai':       {'cal':400, 'pro':18, 'carb':54, 'fat':13, 'fiber':3,  'sugar':6, 'sodium':920, 'chol':55, 'serving':'1 plate (250g)'},
    'pho':            {'cal':320, 'pro':22, 'carb':42, 'fat':5,  'fiber':2,  'sugar':3, 'sodium':1020,'chol':40, 'serving':'1 bowl (450ml)'},
    'sushi':          {'cal':200, 'pro':9,  'carb':38, 'fat':0.7,'fiber':1,  'sugar':4, 'sodium':600, 'chol':10, 'serving':'6 pieces (150g)'},
    'pasta':          {'cal':220, 'pro':8,  'carb':43, 'fat':1.3,'fiber':2.5,'sugar':1, 'sodium':6,   'chol':0,  'serving':'1 cup cooked (140g)'},
    'spaghetti':      {'cal':440, 'pro':24, 'carb':54, 'fat':14, 'fiber':4,  'sugar':8, 'sodium':580, 'chol':55, 'serving':'1 bowl (250g)'},
    'tacos':          {'cal':210, 'pro':10, 'carb':20, 'fat':10, 'fiber':3,  'sugar':2, 'sodium':380, 'chol':25, 'serving':'2 tacos (120g)'},
    # ── Breakfast ──
    'pancakes':       {'cal':370, 'pro':8,  'carb':56, 'fat':13, 'fiber':2,  'sugar':18,'sodium':540, 'chol':70, 'serving':'3 pancakes (150g)'},
    'waffles':        {'cal':290, 'pro':8,  'carb':42, 'fat':10, 'fiber':2,  'sugar':6, 'sodium':450, 'chol':95, 'serving':'1 waffle (100g)'},
    'omelette':       {'cal':154, 'pro':11, 'carb':1,  'fat':12, 'fiber':0,  'sugar':1, 'sodium':342, 'chol':373,'serving':'2-egg (120g)'},
    # ── Desserts ──
    'apple pie':      {'cal':296, 'pro':2,  'carb':43, 'fat':14, 'fiber':2,  'sugar':23,'sodium':251, 'chol':0,  'serving':'1 slice (125g)'},
    'cheesecake':     {'cal':401, 'pro':6,  'carb':36, 'fat':26, 'fiber':0,  'sugar':28,'sodium':280, 'chol':120,'serving':'1 slice (125g)'},
    'chocolate cake': {'cal':367, 'pro':5,  'carb':51, 'fat':17, 'fiber':2,  'sugar':35,'sodium':352, 'chol':55, 'serving':'1 slice (100g)'},
    'donuts':         {'cal':269, 'pro':4,  'carb':32, 'fat':15, 'fiber':1,  'sugar':11,'sodium':300, 'chol':25, 'serving':'1 donut (75g)'},
    'ice cream':      {'cal':207, 'pro':3,  'carb':24, 'fat':11, 'fiber':1,  'sugar':21,'sodium':80,  'chol':44, 'serving':'1/2 cup (66g)'},
    # ── Meat / protein ──
    'steak':          {'cal':271, 'pro':26, 'carb':0,  'fat':18, 'fiber':0,  'sugar':0, 'sodium':54,  'chol':77, 'serving':'1 steak (150g)'},
    'salad':          {'cal':100, 'pro':3,  'carb':12, 'fat':5,  'fiber':4,  'sugar':6, 'sodium':200, 'chol':0,  'serving':'1 bowl (150g)'},
    'chicken nuggets':{'cal':296, 'pro':15, 'carb':16, 'fat':18, 'fiber':0.5,'sugar':0.1,'sodium':560, 'chol':45, 'serving':'6 pieces (100g)'},
    'potato wedges':  {'cal':240, 'pro':3.5,'carb':34, 'fat':10, 'fiber':3.2,'sugar':0.5,'sodium':320, 'chol':0,  'serving':'1 portion (150g)'},
    # ── Added Foods ──
    'paneer butter masala': {'cal':320, 'pro':12, 'carb':10, 'fat':26, 'fiber':1.8, 'sugar':4, 'sodium':580, 'chol':60, 'serving':'1 bowl (200g)'},
    'aloo gobi':           {'cal':140, 'pro':3,  'carb':16, 'fat':8,  'fiber':3.5, 'sugar':3, 'sodium':420, 'chol':0,  'serving':'1 bowl (150g)'},
    'bhindi masala':       {'cal':120, 'pro':2.5,'carb':12, 'fat':7,  'fiber':3.8, 'sugar':2, 'sodium':380, 'chol':0,  'serving':'1 bowl (150g)'},
    'chicken tikka masala':{'cal':300, 'pro':24, 'carb':10, 'fat':18, 'fiber':1.5, 'sugar':5, 'sodium':620, 'chol':85, 'serving':'1 bowl (200g)'},
    'egg curry':           {'cal':220, 'pro':13, 'carb':8,  'fat':15, 'fiber':1.5, 'sugar':3, 'sodium':480, 'chol':370,'serving':'1 bowl (200g)'},
    'fish curry':          {'cal':240, 'pro':22, 'carb':8,  'fat':14, 'fiber':1.2, 'sugar':2, 'sodium':520, 'chol':60, 'serving':'1 bowl (200g)'},
    'poori bhaji':         {'cal':380, 'pro':7,  'carb':48, 'fat':18, 'fiber':4,  'sugar':2, 'sodium':560, 'chol':0,  'serving':'1 plate (2 pooris + bhaji)'},
    'curd rice':           {'cal':190, 'pro':4.5,'carb':28, 'fat':6,  'fiber':1,  'sugar':3, 'sodium':320, 'chol':10, 'serving':'1 bowl (200g)'},
    'lemon rice':          {'cal':240, 'pro':4,  'carb':44, 'fat':5,  'fiber':2,  'sugar':1, 'sodium':380, 'chol':0,  'serving':'1 bowl (200g)'},
    'tamarind rice':       {'cal':260, 'pro':4,  'carb':48, 'fat':6,  'fiber':2.2,'sugar':1, 'sodium':420, 'chol':0,  'serving':'1 bowl (200g)'},
    'pongal':              {'cal':280, 'pro':7,  'carb':42, 'fat':10, 'fiber':3,  'sugar':0, 'sodium':410, 'chol':15, 'serving':'1 plate (200g)'},
    'methi thepla':        {'cal':110, 'pro':3.5,'carb':16, 'fat':3.5,'fiber':2.2,'sugar':1, 'sodium':180, 'chol':0,  'serving':'1 piece (40g)'},
    'medu vada':           {'cal':190, 'pro':5,  'carb':22, 'fat':9,  'fiber':3,  'sugar':1, 'sodium':290, 'chol':0,  'serving':'2 pieces (80g)'},
    'dhokla':              {'cal':120, 'pro':4.5,'carb':18, 'fat':3,  'fiber':1.5,'sugar':3, 'sodium':340, 'chol':0,  'serving':'2 pieces (80g)'},
    'dal bati churma':     {'cal':580, 'pro':14, 'carb':80, 'fat':24, 'fiber':7,  'sugar':15,'sodium':680, 'chol':45, 'serving':'1 plate (350g)'},
    'paneer bhurji':       {'cal':260, 'pro':14, 'carb':6,  'fat':20, 'fiber':1.5,'sugar':2, 'sodium':420, 'chol':40, 'serving':'1 plate (150g)'},
    'malai kofta':         {'cal':340, 'pro':9,  'carb':20, 'fat':26, 'fiber':2.5,'sugar':6, 'sodium':540, 'chol':55, 'serving':'1 bowl (200g)'},
    'chicken shawarma':    {'cal':390, 'pro':26, 'carb':32, 'fat':18, 'fiber':2.5,'sugar':3, 'sodium':740, 'chol':65, 'serving':'1 wrap (200g)'},
    'fish fry':            {'cal':280, 'pro':20, 'carb':10, 'fat':18, 'fiber':0.8,'sugar':0.5,'sodium':480,'chol':55, 'serving':'1 piece (120g)'},
    'mutton curry':        {'cal':310, 'pro':24, 'carb':8,  'fat':20, 'fiber':1.5,'sugar':2, 'sodium':510, 'chol':80, 'serving':'1 bowl (200g)'},
    'jeera rice':          {'cal':180, 'pro':3.5,'carb':36, 'fat':2.5,'fiber':1,  'sugar':0.2,'sodium':220,'chol':5,  'serving':'1 bowl (150g)'},
    'boiled egg':          {'cal':78,  'pro':6.3,'carb':0.6,'fat':5.3,'fiber':0,  'sugar':0.6,'sodium':62, 'chol':186,'serving':'1 large (50g)'},
    'scrambled eggs':      {'cal':148, 'pro':10, 'carb':1.6,'fat':11, 'fiber':0,  'sugar':1.2,'sodium':240, 'chol':340,'serving':'2 large eggs (100g)'},
    'egg bhurji':          {'cal':180, 'pro':11, 'carb':4,  'fat':14, 'fiber':1,  'sugar':2, 'sodium':320, 'chol':340,'serving':'1 plate (120g)'},
    'oatmeal':             {'cal':150, 'pro':5,  'carb':27, 'fat':2.5,'fiber':4,  'sugar':1, 'sodium':120, 'chol':0,  'serving':'1 cup cooked (234g)'},
    'cornflakes':          {'cal':110, 'pro':2,  'carb':24, 'fat':0.1,'fiber':1,  'sugar':2, 'sodium':200, 'chol':0,  'serving':'1 cup (30g)'},
    'muesli':              {'cal':160, 'pro':4,  'carb':30, 'fat':3,  'fiber':4.5,'sugar':6, 'sodium':60,  'chol':0,  'serving':'1/2 cup (45g)'},
    'garlic bread':        {'cal':150, 'pro':4,  'carb':20, 'fat':6,  'fiber':1.2,'sugar':1, 'sodium':280, 'chol':5,  'serving':'1 piece (40g)'},
    'macaroni and cheese': {'cal':310, 'pro':10, 'carb':38, 'fat':13, 'fiber':1.6,'sugar':5, 'sodium':620, 'chol':30, 'serving':'1 cup (200g)'},
    'lasagna':             {'cal':336, 'pro':19, 'carb':35, 'fat':14, 'fiber':2.8,'sugar':6, 'sodium':640, 'chol':45, 'serving':'1 piece (250g)'},
    'nachos':              {'cal':306, 'pro':5,  'carb':34, 'fat':17, 'fiber':3.2,'sugar':1, 'sodium':420, 'chol':10, 'serving':'1 portion (100g)'},
    'quesadilla':          {'cal':290, 'pro':13, 'carb':28, 'fat':14, 'fiber':2.5,'sugar':2, 'sodium':580, 'chol':35, 'serving':'1 piece (150g)'},
    'chicken wings':       {'cal':290, 'pro':19, 'carb':12, 'fat':18, 'fiber':0.5,'sugar':3, 'sodium':680, 'chol':80, 'serving':'4 wings (150g)'},
    'grilled cheese sandwich': {'cal':320, 'pro':11,'carb':30,'fat':17, 'fiber':1.8,'sugar':2, 'sodium':680, 'chol':40, 'serving':'1 sandwich (120g)'},
    'french toast':        {'cal':230, 'pro':7,  'carb':28, 'fat':10, 'fiber':1.5,'sugar':9, 'sodium':310, 'chol':130,'serving':'2 slices (130g)'},
    'croissant':           {'cal':231, 'pro':4.7,'carb':26, 'fat':12, 'fiber':1.3,'sugar':5, 'sodium':322, 'chol':30, 'serving':'1 large (57g)'},
    'bagel':               {'cal':250, 'pro':10, 'carb':48, 'fat':1.5,'fiber':2.2,'sugar':6, 'sodium':380, 'chol':0,  'serving':'1 medium (85g)'},
    'hummus':              {'cal':166, 'pro':7.9,'carb':14, 'fat':9.6,'fiber':6,  'sugar':0.3,'sodium':379,'chol':0,  'serving':'1/2 cup (100g)'},
    'falafel':             {'cal':333, 'pro':13, 'carb':32, 'fat':17, 'fiber':5,  'sugar':2, 'sodium':290, 'chol':0,  'serving':'5 patties (150g)'},
    'caesar salad':        {'cal':190, 'pro':4,  'carb':8,  'fat':16, 'fiber':2.1,'sugar':1.5,'sodium':460,'chol':25, 'serving':'1 bowl (150g)'},
    'grilled chicken breast': {'cal':165, 'pro':31,'carb':0, 'fat':3.6,'fiber':0,  'sugar':0, 'sodium':74,  'chol':85, 'serving':'1 breast (100g)'},
    'tofu':                {'cal':76,  'pro':8,  'carb':1.9,'fat':4.8,'fiber':0.3,'sugar':0, 'sodium':7,   'chol':0,  'serving':'100g'},
    'boiled vegetables':   {'cal':54,  'pro':2.4,'carb':11, 'fat':0.3,'fiber':3.8,'sugar':3.5,'sodium':42,  'chol':0,  'serving':'1 cup (150g)'},
    'protein shake':       {'cal':140, 'pro':25, 'carb':3,  'fat':2,  'fiber':1,  'sugar':1, 'sodium':160, 'chol':45, 'serving':'1 scoop (35g powder)'},
    'protein bar':         {'cal':200, 'pro':20, 'carb':22, 'fat':6,  'fiber':8,  'sugar':2, 'sodium':180, 'chol':10, 'serving':'1 bar (60g)'},
    'cucumber salad':      {'cal':45,  'pro':1,  'carb':6,  'fat':2,  'fiber':1.2,'sugar':3, 'sodium':150, 'chol':0,  'serving':'1 bowl (150g)'},
    'papaya':              {'cal':43,  'pro':0.5,'carb':11, 'fat':0.3,'fiber':1.7,'sugar':8, 'sodium':8,   'chol':0,  'serving':'1 cup cubes (140g)'},
    'guava':               {'cal':68,  'pro':2.6,'carb':14, 'fat':1,  'fiber':5.4,'sugar':9, 'sodium':2,   'chol':0,  'serving':'1 medium (100g)'},
    'pomegranate':         {'cal':83,  'pro':1.7,'carb':19, 'fat':1.2,'fiber':4,  'sugar':14,'sodium':3,   'chol':0,  'serving':'100g seeds'},
    'avocado':             {'cal':160, 'pro':2,  'carb':8.5,'fat':15, 'fiber':6.7,'sugar':0.7,'sodium':7,  'chol':0,  'serving':'1/2 avocado (100g)'},
    'kiwi':                {'cal':61,  'pro':1.1,'carb':15, 'fat':0.5,'fiber':3,  'sugar':9, 'sodium':3,   'chol':0,  'serving':'1 medium (76g)'},
    'blueberry':           {'cal':57,  'pro':0.7,'carb':14, 'fat':0.3,'fiber':2.4,'sugar':10,'sodium':1,   'chol':0,  'serving':'1 cup (148g)'},
    'peach':               {'cal':59,  'pro':1.4,'carb':14, 'fat':0.4,'fiber':2.3,'sugar':13,'sodium':0,   'chol':0,  'serving':'1 medium (150g)'},
    'pear':                {'cal':101, 'pro':0.6,'carb':27, 'fat':0.3,'fiber':5.5,'sugar':17,'sodium':2,   'chol':0,  'serving':'1 medium (178g)'},
    'cherry':              {'cal':97,  'pro':1.6,'carb':25, 'fat':0.3,'fiber':3.2,'sugar':20,'sodium':0,   'chol':0,  'serving':'1 cup (154g)'},
    'almonds':             {'cal':164, 'pro':6,  'carb':6,  'fat':14, 'fiber':3.5,'sugar':1.2,'sodium':1,   'chol':0,  'serving':'1 ounce (28g)'},
    'walnuts':             {'cal':185, 'pro':4.3,'carb':3.9,'fat':18.5,'fiber':1.9,'sugar':0.7,'sodium':1, 'chol':0,  'serving':'1 ounce (28g)'},
    'cashew nuts':         {'cal':157, 'pro':5.2,'carb':8.6,'fat':12.4,'fiber':0.9,'sugar':1.7,'sodium':3, 'chol':0,  'serving':'1 ounce (28g)'},
    'peanut butter':       {'cal':188, 'pro':8,  'carb':6,  'fat':16, 'fiber':1.9,'sugar':3, 'sodium':150, 'chol':0,  'serving':'2 tbsp (32g)'},
    'green tea':           {'cal':2,   'pro':0,  'carb':0,  'fat':0,  'fiber':0,  'sugar':0, 'sodium':0,   'chol':0,  'serving':'1 cup (240ml)'},
    'black coffee':        {'cal':2,   'pro':0.3,'carb':0,  'fat':0,  'fiber':0,  'sugar':0, 'sodium':5,   'chol':0,  'serving':'1 cup (240ml)'},
    'buttermilk':          {'cal':80,  'pro':3,  'carb':4,  'fat':2.5,'fiber':0,  'sugar':4, 'sodium':320, 'chol':10, 'serving':'1 glass (200ml)'},
    'coconut water':       {'cal':44,  'pro':1.7,'carb':10.5,'fat':0.5,'fiber':2.6,'sugar':9.6,'sodium':252, 'chol':0,  'serving':'1 cup (240ml)'},
    'lemonade':            {'cal':99,  'pro':0.1,'carb':26, 'fat':0.1,'fiber':0.1,'sugar':25,'sodium':10,  'chol':0,  'serving':'1 glass (240ml)'},
    'soda':                {'cal':140, 'pro':0,  'carb':39, 'fat':0,  'fiber':0,  'sugar':39,'sodium':45,  'chol':0,  'serving':'1 can (355ml)'},
    'milk':                {'cal':122, 'pro':8,  'carb':12, 'fat':4.8,'fiber':0,  'sugar':12,'sodium':100, 'chol':20, 'serving':'1 glass (244ml)'},
    'soy milk':            {'cal':100, 'pro':7,  'carb':8,  'fat':4,  'fiber':1.5,'sugar':6, 'sodium':120, 'chol':0,  'serving':'1 glass (240ml)'},
    'almond milk':         {'cal':39,  'pro':1,  'carb':1.5,'fat':3,  'fiber':0.5,'sugar':0.1,'sodium':180,'chol':0,  'serving':'1 glass (240ml)'},
    'hot chocolate':       {'cal':190, 'pro':6,  'carb':28, 'fat':6,  'fiber':1,  'sugar':24,'sodium':140, 'chol':20, 'serving':'1 mug (240ml)'},
    'iced tea':            {'cal':90,  'pro':0,  'carb':23, 'fat':0,  'fiber':0,  'sugar':22,'sodium':10,  'chol':0,  'serving':'1 glass (240ml)'},
    'milkshake':           {'cal':350, 'pro':8,  'carb':54, 'fat':11, 'fiber':0.5,'sugar':48,'sodium':180, 'chol':40, 'serving':'1 glass (300ml)'},
    'rasmalai':            {'cal':180, 'pro':5,  'carb':22, 'fat':8,  'fiber':0,  'sugar':18,'sodium':60,  'chol':25, 'serving':'2 pieces (100g)'},
    'brownie':             {'cal':243, 'pro':3,  'carb':34, 'fat':11, 'fiber':1.5,'sugar':24,'sodium':145, 'chol':45, 'serving':'1 square (60g)'},
    'chocolate chip cookie': {'cal':148,'pro':1.6,'carb':20,'fat':7.4,'fiber':0.7,'sugar':11,'sodium':104, 'chol':10, 'serving':'1 cookie (30g)'},
    'custard':             {'cal':122, 'pro':3.6,'carb':17, 'fat':4.2,'fiber':0,  'sugar':14,'sodium':64,  'chol':80, 'serving':'1 portion (100g)'},
    'pudding':             {'cal':112, 'pro':3,  'carb':19, 'fat':2.9,'fiber':0.1,'sugar':16,'sodium':135, 'chol':10, 'serving':'1 portion (100g)'},
    # ── International Cuisine Additions ──
    'burrito':             {'cal':440, 'pro':18, 'carb':58, 'fat':15, 'fiber':7,  'sugar':3, 'sodium':820, 'chol':40, 'serving':'1 medium (200g)'},
    'enchiladas':          {'cal':380, 'pro':16, 'carb':38, 'fat':18, 'fiber':4,  'sugar':4, 'sodium':740, 'chol':50, 'serving':'2 pieces (220g)'},
    'guacamole':           {'cal':150, 'pro':2,  'carb':8,  'fat':13, 'fiber':6,  'sugar':1, 'sodium':240, 'chol':0,  'serving':'1/2 cup (100g)'},
    'fajitas':             {'cal':350, 'pro':26, 'carb':20, 'fat':19, 'fiber':3.5,'sugar':4, 'sodium':680, 'chol':70, 'serving':'1 plate (250g)'},
    'queso dip':           {'cal':180, 'pro':8,  'carb':6,  'fat':14, 'fiber':0.5,'sugar':1, 'sodium':520, 'chol':35, 'serving':'1/2 cup (100g)'},
    'risotto':             {'cal':310, 'pro':6,  'carb':45, 'fat':11, 'fiber':1,  'sugar':1, 'sodium':580, 'chol':25, 'serving':'1 bowl (200g)'},
    'gnocchi':             {'cal':250, 'pro':5,  'carb':48, 'fat':3,  'fiber':2.2,'sugar':1, 'sodium':420, 'chol':0,  'serving':'1 plate (150g)'},
    'bruschetta':          {'cal':120, 'pro':3,  'carb':16, 'fat':5,  'fiber':1.5,'sugar':2, 'sodium':220, 'chol':0,  'serving':'2 pieces (80g)'},
    'minestrone soup':     {'cal':110, 'pro':4,  'carb':18, 'fat':2.5,'fiber':4.2,'sugar':3, 'sodium':540, 'chol':0,  'serving':'1 bowl (240ml)'},
    'tiramisu':            {'cal':290, 'pro':4,  'carb':32, 'fat':16, 'fiber':0.5,'sugar':24,'sodium':110, 'chol':120,'serving':'1 piece (80g)'},
    'tempura':             {'cal':220, 'pro':8,  'carb':24, 'fat':10, 'fiber':1,  'sugar':1, 'sodium':380, 'chol':45, 'serving':'4 pieces (120g)'},
    'gyoza':               {'cal':180, 'pro':7,  'carb':22, 'fat':6,  'fiber':1.5,'sugar':1, 'sodium':480, 'chol':20, 'serving':'5 pieces (100g)'},
    'edamame':             {'cal':122, 'pro':11, 'carb':10, 'fat':5,  'fiber':5.2,'sugar':2, 'sodium':6,   'chol':0,  'serving':'1 cup (155g)'},
    'miso soup':           {'cal':45,  'pro':3,  'carb':5,  'fat':1.5,'fiber':1.2,'sugar':1, 'sodium':650, 'chol':0,  'serving':'1 bowl (240ml)'},
    'chicken teriyaki':    {'cal':340, 'pro':28, 'carb':18, 'fat':16, 'fiber':0.5,'sugar':14,'sodium':720, 'chol':80, 'serving':'1 portion (200g)'},
    'sweet and sour chicken': {'cal':380,'pro':22,'carb':48,'fat':11, 'fiber':1.5,'sugar':28,'sodium':580, 'chol':60, 'serving':'1 portion (200g)'},
    'kung pao chicken':    {'cal':350, 'pro':24, 'carb':14, 'fat':22, 'fiber':2.2,'sugar':8, 'sodium':690, 'chol':70, 'serving':'1 portion (200g)'},
    'mapo tofu':           {'cal':240, 'pro':14, 'carb':8,  'fat':17, 'fiber':1.8,'sugar':2, 'sodium':590, 'chol':25, 'serving':'1 bowl (200g)'},
    'dim sum':             {'cal':160, 'pro':8,  'carb':20, 'fat':5,  'fiber':1,  'sugar':1, 'sodium':420, 'chol':30, 'serving':'4 pieces (120g)'},
    'hot and sour soup':   {'cal':95,  'pro':5,  'carb':12, 'fat':3,  'fiber':1.5,'sugar':3, 'sodium':780, 'chol':25, 'serving':'1 bowl (240ml)'},
    'tabbouleh':           {'cal':120, 'pro':2,  'carb':14, 'fat':6,  'fiber':3.5,'sugar':1.5,'sodium':180,'chol':0,  'serving':'1 cup (150g)'},
    'baba ganoush':        {'cal':140, 'pro':2,  'carb':10, 'fat':10, 'fiber':4,  'sugar':2, 'sodium':260, 'chol':0,  'serving':'1/2 cup (100g)'},
    'greek salad':         {'cal':150, 'pro':3,  'carb':8,  'fat':12, 'fiber':2.2,'sugar':4, 'sodium':380, 'chol':15, 'serving':'1 bowl (150g)'},
    'gyro':                {'cal':480, 'pro':24, 'carb':42, 'fat':23, 'fiber':3,  'sugar':4, 'sodium':880, 'chol':65, 'serving':'1 wrap (220g)'},
    'couscous':            {'cal':176, 'pro':6,  'carb':36, 'fat':0.3,'fiber':2.2,'sugar':0.2,'sodium':5,  'chol':0,  'serving':'1 cup cooked (157g)'},
    'bbq ribs':            {'cal':420, 'pro':28, 'carb':12, 'fat':28, 'fiber':0.5,'sugar':10,'sodium':560, 'chol':95, 'serving':'3 ribs (150g)'},
    'buffalo wings':       {'cal':320, 'pro':20, 'carb':2,  'fat':26, 'fiber':0.2,'sugar':0.2,'sodium':890,'chol':90, 'serving':'4 wings (120g)'},
    'potato salad':        {'cal':240, 'pro':3,  'carb':28, 'fat':13, 'fiber':2.8,'sugar':3, 'sodium':490, 'chol':45, 'serving':'1 cup (150g)'},
    'clam chowder':        {'cal':201, 'pro':9,  'carb':20, 'fat':10, 'fiber':1.5,'sugar':2.5,'sodium':790,'chol':30, 'serving':'1 cup (240ml)'},
    'onion rings':         {'cal':280, 'pro':3,  'carb':32, 'fat':16, 'fiber':2.2,'sugar':4, 'sodium':380, 'chol':0,  'serving':'1 portion (100g)'},
    'fried chicken':       {'cal':298, 'pro':22, 'carb':12, 'fat':18, 'fiber':0.5,'sugar':0.1,'sodium':490,'chol':80, 'serving':'1 breast (140g)'},
    'baked potato':        {'cal':160, 'pro':4.3,'carb':37, 'fat':0.2,'fiber':4,  'sugar':1.5,'sodium':15, 'chol':0,  'serving':'1 medium (173g)'},
    'popcorn':             {'cal':110, 'pro':3,  'carb':22, 'fat':1.5,'fiber':4,  'sugar':0.2,'sodium':150,'chol':0,  'serving':'3 cups popped (30g)'},
}

TIPS = {
    'biryani':        'High calorie — pair with raita for balance.',
    'burger':         'High sodium. Grilled over fried saves ~30% calories.',
    'butter chicken': 'Great protein. High fat — moderate your portion.',
    'pizza':          '2 slices is one serving. Thin crust cuts calories by 30%.',
    'pho':            'Lower calorie than ramen. Great protein from broth.',
    'ramen':          'Very high sodium. Ask for light broth if eating out.',
    'french fries':   'Baked fries cut calories by ~40%. Skip extra salt.',
    'dal':            'Excellent plant protein and fiber. Very nutritious.',
    'dosa':           'Fermented — good for gut health. Low calorie without filling.',
    'salad':          'Add protein (egg/chicken/paneer) to keep you fuller longer.',
    'ice cream':      'Treat yourself — just watch portion size.',
    'steak':          'Great protein source. Opt for lean cuts when possible.',
    'chicken nuggets': 'Baked nuggets are lower in fat than fried. Enjoy with sauce in moderation.',
    'potato wedges':   'Baked wedges have skins for fiber. Keep portions balanced.',
}
DEFAULT_TIP = 'A balanced meal includes protein, complex carbs, healthy fats and vegetables.'


# ──────────────────────────────────────────────────────────────────────────────
#  USDA FOODDATA CENTRAL API
# ──────────────────────────────────────────────────────────────────────────────

def _usda_lookup(food_name: str) -> dict | None:
    """Look up nutrition from USDA FoodData Central (free API, 300k+ foods)."""
    api_key = os.getenv('USDA_API_KEY')
    if not api_key:
        return None
    try:
        resp = http_requests.get(
            'https://api.nal.usda.gov/fdc/v1/foods/search',
            params={'api_key': api_key, 'query': food_name, 'pageSize': 1,
                    'dataType': 'Survey (FNDDS)'},
            timeout=5
        )
        if resp.status_code != 200:
            return None
        foods = resp.json().get('foods', [])
        if not foods:
            return None
        f = foods[0]
        nutrients = {n['nutrientName']: n.get('value', 0) for n in f.get('foodNutrients', [])}
        return {
            'food_name':      f.get('description', food_name).strip().title(),
            'serving_size':   '100g (USDA)',
            'confidence':     80,
            'calories':       round(nutrients.get('Energy', 0)),
            'protein_g':      round(nutrients.get('Protein', 0), 1),
            'carbs_g':        round(nutrients.get('Carbohydrate, by difference', 0), 1),
            'fat_g':          round(nutrients.get('Total lipid (fat)', 0), 1),
            'fiber_g':        round(nutrients.get('Fiber, total dietary', 0), 1),
            'sugar_g':        round(nutrients.get('Sugars, total including NLEA', 0), 1),
            'sodium_mg':      round(nutrients.get('Sodium, Na', 0)),
            'cholesterol_mg': round(nutrients.get('Cholesterol', 0)),
            'source':         'usda',
        }
    except Exception as e:
        print(f'  [USDA] lookup error: {e}')
        return None


# ──────────────────────────────────────────────────────────────────────────────
#  SHARED HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _db_lookup(name: str, confidence: int = 90) -> dict | None:
    """Exact then substring match against NUTRITION_DB."""
    name_l = name.lower().strip()
    if name_l in NUTRITION_DB:
        d = NUTRITION_DB[name_l]
        return _db_row(name, d, confidence=95)
    best_key, best_len = None, 0
    for key in NUTRITION_DB:
        if len(key) < 3:
            continue
        if key in name_l or name_l in key:
            if len(key) > best_len:
                best_key, best_len = key, len(key)
    if best_key:
        return _db_row(name, NUTRITION_DB[best_key], confidence=confidence)
    return None

def _db_row(name: str, d: dict, confidence: int = 90) -> dict:
    return {
        'food_name':      name.strip().title(),
        'serving_size':   d['serving'],
        'confidence':     confidence,
        'calories':       d['cal'],
        'protein_g':      d['pro'],
        'carbs_g':        d['carb'],
        'fat_g':          d['fat'],
        'fiber_g':        d['fiber'],
        'sugar_g':        d['sugar'],
        'sodium_mg':      d['sodium'],
        'cholesterol_mg': d['chol'],
    }

def _fallback_item(name: str) -> dict:
    """Last-resort item with estimate flag."""
    return {
        'food_name':      name.strip().title(),
        'serving_size':   '1 serving (~150g) — estimated',
        'confidence':     30,
        'calories':       200,
        'protein_g':      8,
        'carbs_g':        25,
        'fat_g':          8,
        'fiber_g':        2,
        'sugar_g':        4,
        'sodium_mg':      300,
        'cholesterol_mg': 20,
    }

def _tip(food_name: str) -> str:
    n = food_name.lower()
    return next((v for k, v in TIPS.items() if k in n or n in k), DEFAULT_TIP)


# ──────────────────────────────────────────────────────────────────────────────
#  PIPE-RESPONSE PARSER  (shared by Groq + Ollama engines)
# ──────────────────────────────────────────────────────────────────────────────

def _parse_pipe_response(text: str) -> list:
    """
    Parse lines like:
        Chicken Biryani|350|15|48|12|2|3|480|45|1 plate (300g)
    Returns list of item dicts. Falls back to DB lookup for any unparseable line.
    """
    items = []
    for line in text.strip().split('\n'):
        line = line.strip().lstrip('- •*0123456789.)').strip()
        if not line or 'NOT_FOOD' in line.upper():
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 5:
            try:
                def _n(v, default=0.0):
                    return float(re.sub(r'[^0-9.]', '', v or '') or default)
                item = {
                    'food_name':      parts[0].strip().title(),
                    'calories':       round(_n(parts[1], 0)),
                    'protein_g':      round(_n(parts[2], 0), 1),
                    'carbs_g':        round(_n(parts[3], 0), 1),
                    'fat_g':          round(_n(parts[4], 0), 1),
                    'fiber_g':        round(_n(parts[5], 2), 1) if len(parts) > 5 else 2.0,
                    'sugar_g':        round(_n(parts[6], 3), 1) if len(parts) > 6 else 3.0,
                    'sodium_mg':      round(_n(parts[7], 300))  if len(parts) > 7 else 300,
                    'cholesterol_mg': round(_n(parts[8], 20))   if len(parts) > 8 else 20,
                    'serving_size':   parts[9].strip()          if len(parts) > 9 else '1 serving',
                    'confidence':     88,
                }
                if item['calories'] > 0:
                    items.append(item)
            except (ValueError, IndexError):
                continue
    # If structured parse failed, try DB lookup for any food-like words
    if not items:
        words = re.findall(r'[A-Za-z][a-z]+(?:\s+[a-z]+){0,3}', text)
        seen = set()
        for w in words[:6]:
            w = w.strip().lower()
            if len(w) < 3 or w in seen:
                continue
            seen.add(w)
            hit = _db_lookup(w)
            if hit:
                items.append(hit)
    return items[:9]


# ──────────────────────────────────────────────────────────────────────────────
#  IMAGE RESIZE HELPER  (server-side — faster CPU inference)
# ──────────────────────────────────────────────────────────────────────────────

def _resize_image_b64(b64: str, max_px: int = 512) -> str:
    """
    Resize a base64 JPEG to max_px on the longest side.
    Smaller image = fewer vision tokens = 2-3x faster on CPU.
    Falls back to original if PIL is not installed.
    """
    try:
        from PIL import Image as _PILImage
        import io as _io
        data   = base64.b64decode(b64)
        img    = _PILImage.open(_io.BytesIO(data)).convert('RGB')
        w, h   = img.size
        if max(w, h) > max_px:
            scale  = max_px / max(w, h)
            img    = img.resize((int(w * scale), int(h * scale)), _PILImage.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return b64   # PIL not available — use original

# Strict prompt — reduces hallucinations and phantom items
VISION_PROMPT = (
    "Look carefully at this image. List ONLY the food items you can clearly and confidently see.\n"
    "Rules:\n"
    "- DO NOT list food you are guessing or inferring — only what is visibly present.\n"
    "- Use specific names (e.g. 'Chicken Wing' not 'Fried Chicken', 'White Rice' not 'Rice').\n"
    "- If NO food visible: reply NOT_FOOD\n"
    "For each clearly visible food, output exactly one line:\n"
    "FoodName|calories|protein_g|carbs_g|fat_g|fiber_g|sugar_g|sodium_mg|cholesterol_mg|serving_size\n"
    "Output ONLY the data lines. No explanation. Max 5 items."
)


# ──────────────────────────────────────────────────────────────────────────────
#  ENGINE 0 — CLIP ZERO-SHOT FOOD CLASSIFIER  (3-7 s CPU, no API key)
#
#  Uses openai/clip-vit-base-patch32 with zero-shot-image-classification.
#  We provide our own candidate food labels — ALL foods from NUTRITION_DB
#  plus extra Indian, Asian and global foods.
#  No fixed category limit — works for any food we name!
# ──────────────────────────────────────────────────────────────────────────────

# ── Full candidate food list (what CLIP will score the image against) ────────
# These ARE the NUTRITION_DB keys + extra aliases/variants
_CLIP_CANDIDATES = [
    # ── Indian staples ────────────────────────────────────────────────────────
    'biryani', 'chicken biryani', 'vegetable biryani', 'mutton biryani',
    'butter chicken', 'chicken curry', 'dal', 'dal makhani',
    'chole bhature', 'chana masala', 'rajma', 'kadai paneer',
    'paneer tikka', 'palak paneer', 'shahi paneer',
    'masala dosa', 'dosa', 'idli', 'sambar', 'uttapam',
    'roti', 'chapati', 'paratha', 'naan', 'puri',
    'samosa', 'pav bhaji', 'vada pav', 'poha', 'upma', 'khichdi',
    'momos', 'kebab', 'tandoori chicken',
    # ── Indian sweets & drinks ────────────────────────────────────────────────
    'gulab jamun', 'rasgulla', 'kheer', 'halwa', 'jalebi',
    'kulfi', 'lassi', 'mango lassi', 'chai', 'masala chai',
    'dhokla', 'pakora', 'bhajji', 'pani puri',
    # ── Global fast food ─────────────────────────────────────────────────────
    'pizza', 'burger', 'hamburger', 'cheeseburger',
    'hot dog', 'french fries', 'tacos', 'sandwich',
    'chicken nuggets', 'potato wedges',
    # ── Asian ────────────────────────────────────────────────────────────────
    'sushi', 'ramen', 'noodles', 'fried rice', 'pad thai', 'pho',
    'dumplings', 'spring rolls', 'bibimbap', 'baklava',
    # ── Western / global ─────────────────────────────────────────────────────
    'pasta', 'spaghetti', 'steak', 'salad', 'omelette', 'waffles',
    'pancakes', 'cheesecake', 'chocolate cake', 'apple pie',
    'donuts', 'ice cream', 'sushi roll',
    # ── Fruits ───────────────────────────────────────────────────────────────
    'apple', 'banana', 'mango', 'orange', 'strawberry',
    'pineapple', 'grapes', 'watermelon',
    # ── Beverages ────────────────────────────────────────────────────────────
    'coffee', 'juice', 'smoothie',
    # ── Added Foods ──────────────────────────────────────────────────────────
    'paneer butter masala', 'aloo gobi', 'bhindi masala', 'chicken tikka masala',
    'egg curry', 'fish curry', 'poori bhaji', 'curd rice', 'lemon rice',
    'tamarind rice', 'pongal', 'methi thepla', 'medu vada', 'dhokla',
    'dal bati churma', 'paneer bhurji', 'malai kofta', 'chicken shawarma',
    'fish fry', 'mutton curry', 'jeera rice', 'boiled egg', 'scrambled eggs',
    'egg bhurji', 'oatmeal', 'cornflakes', 'muesli', 'garlic bread',
    'macaroni and cheese', 'lasagna', 'nachos', 'quesadilla', 'chicken wings',
    'grilled cheese sandwich', 'french toast', 'croissant', 'bagel', 'hummus',
    'falafel', 'caesar salad', 'grilled chicken breast', 'tofu',
    'boiled vegetables', 'protein shake', 'protein bar', 'cucumber salad',
    'papaya', 'guava', 'pomegranate', 'avocado', 'kiwi', 'blueberry',
    'peach', 'pear', 'cherry', 'almonds', 'walnuts', 'cashew nuts',
    'peanut butter', 'green tea', 'black coffee', 'buttermilk', 'coconut water',
    'lemonade', 'soda', 'milk', 'soy milk', 'almond milk', 'hot chocolate',
    'iced tea', 'milkshake', 'rasmalai', 'brownie', 'chocolate chip cookie',
    'custard', 'pudding',
    # ── International Cuisine Additions ──
    'burrito', 'enchiladas', 'guacamole', 'fajitas', 'queso dip',
    'risotto', 'gnocchi', 'bruschetta', 'minestrone soup', 'tiramisu',
    'tempura', 'gyoza', 'edamame', 'miso soup', 'chicken teriyaki',
    'sweet and sour chicken', 'kung pao chicken', 'mapo tofu', 'dim sum',
    'hot and sour soup', 'tabbouleh', 'baba ganoush', 'greek salad',
    'gyro', 'couscous', 'bbq ribs', 'buffalo wings', 'potato salad',
    'clam chowder', 'onion rings', 'fried chicken', 'baked potato',
    'popcorn',
]

# Map candidate label → exact NUTRITION_DB key (for labels that differ)
_CLIP_DB_MAP = {
    'chicken biryani':   'biryani',
    'vegetable biryani': 'biryani',
    'mutton biryani':    'biryani',
    'chana masala':      'chole bhature',
    'kadai paneer':      'paneer tikka',
    'palak paneer':      'paneer tikka',
    'shahi paneer':      'paneer tikka',
    'chapati':           'roti',
    'puri':              'roti',
    'tandoori chicken':  'chicken curry',
    'halwa':             'kheer',
    'jalebi':            'gulab jamun',
    'kulfi':             'ice cream',
    'masala chai':       'lassi',
    'chai':              'lassi',
    'mango lassi':       'mango lassi',
    'dhokla':            'idli',
    'pakora':            'samosa',
    'bhajji':            'samosa',
    'pani puri':         'samosa',
    'hamburger':         'burger',
    'cheeseburger':      'burger',
    'dumplings':         'momos',
    'spring rolls':      'momos',
    'bibimbap':          'fried rice',
    'baklava':           'gulab jamun',
    'spaghetti':         'spaghetti',
    'omelette':          'omelette',
    'cheesecake':        'cheesecake',
    'chocolate cake':    'chocolate cake',
    'apple pie':         'apple pie',
    'donuts':            'donuts',
    'sushi roll':        'sushi',
    'coffee':            'lassi',
    'juice':             'lassi',
    'smoothie':          'lassi',
    'chicken nuggets':   'chicken nuggets',
    'potato wedges':     'potato wedges',
    'nuggets':           'chicken nuggets',
}


def _scale_confidence(score: float, is_top: bool = False) -> int:
    """Scale raw CLIP softmax score to a user-friendly percentage (0-100)."""
    if is_top:
        if score >= 0.40:
            return min(99, int(92 + (score - 0.40) * 11.6)) # 92% to 99%
        elif score >= 0.15:
            return min(99, int(80 + (score - 0.15) * 48)) # 80% to 92%
        elif score >= 0.05:
            return min(99, int(60 + (score - 0.05) * 200)) # 60% to 80%
        else:
            return min(99, int(max(30, score * 100 * 6)))
    else:
        if score >= 0.25:
            return min(99, int(80 + (score - 0.25) * 25))
        elif score >= 0.08:
            return min(99, int(60 + (score - 0.08) * 117))
        else:
            return min(99, int(max(20, score * 100 * 4)))


def _scale_siglip_confidence(score: float, is_top: bool = False) -> int:
    """Scale raw SigLIP Sigmoid score to a user-friendly percentage (0-100)."""
    if is_top:
        if score >= 0.020:
            return min(99, int(90 + (score - 0.020) * 110))
        elif score >= 0.005:
            return min(99, int(70 + (score - 0.005) * 1333))
        elif score >= 0.001:
            return min(99, int(45 + (score - 0.001) * 6250))
        else:
            return min(99, int(max(30, score * 1000 * 30)))
    else:
        if score >= 0.015:
            return min(99, int(85 + (score - 0.015) * 140))
        elif score >= 0.004:
            return min(99, int(65 + (score - 0.004) * 1818))
        elif score >= 0.0008:
            return min(99, int(40 + (score - 0.0008) * 7812))
        else:
            return min(99, int(max(20, score * 1000 * 25)))


class ViTFoodEngine:
    """
    CLIP zero-shot food classifier — covers ALL foods we define as candidates.

    Uses openai/clip-vit-base-patch32 (zero-shot-image-classification).
    Candidate list includes 100+ foods: biryani, dal, dosa, idli, butter
    chicken, chole bhature, paneer, samosa, pav bhaji, ramen, pizza, burger…

    No fixed categories. Add any food to _CLIP_CANDIDATES to support it.
    ~600 MB model, 3-7 s CPU inference.
    """

    CLIP_MODEL  = 'google/siglip-base-patch16-224'
    FOOD101_MDL = 'nateraw/food'   # fast first-pass: confirms image is food

    def __init__(self):
        self.pipe_clip   = None
        self.pipe_food101 = None
        self.loaded      = False
        self._load()

    def _load(self):
        from transformers import pipeline as hf_pipeline

        # ── Load SigLIP (primary — zero-shot, covers all our foods) ────────────
        print('  [FoodAI] loading SigLIP zero-shot classifier...')
        try:
            self.pipe_clip = hf_pipeline(
                'zero-shot-image-classification',
                model=self.CLIP_MODEL,
            )
            self.loaded = True
            print(f'  [FoodAI] SigLIP ready — {len(_CLIP_CANDIDATES)} food candidates')
        except Exception as e:
            print(f'  [FoodAI] SigLIP failed: {e}')

        # ── Load Food-101 (fast fallback / food-presence check) ──────────────
        print('  [FoodAI] loading nateraw/food (fast fallback)...')
        try:
            self.pipe_food101 = hf_pipeline(
                'image-classification', model=self.FOOD101_MDL, top_k=5)
            if not self.loaded:
                self.loaded = True
            print('  [FoodAI] Food-101 fallback ready')
        except Exception as e:
            print(f'  [FoodAI] Food-101 fallback failed: {e}')

    def _db_name(self, label: str) -> str:
        """Resolve CLIP candidate label to NUTRITION_DB key."""
        label_l = label.lower().strip()
        if label_l in _CLIP_DB_MAP:
            return _CLIP_DB_MAP[label_l]
        # Direct DB match
        if label_l in NUTRITION_DB:
            return label_l
        return label_l

    def predict(self, image_b64: str) -> dict:
        t0 = time.time()
        if not self.loaded:
            raise RuntimeError('Food classifier not loaded')

        raw = base64.b64decode(image_b64.split(',', 1)[1] if ',' in image_b64 else image_b64)
        img = Image.open(io.BytesIO(raw)).convert('RGB')

        # ── SigLIP zero-shot food check ────────────────────────────────────────
        if self.pipe_clip:
            food_check = self.pipe_clip(img, candidate_labels=["a photo of food", "a photo of something that is not food"])
            is_food_label = food_check[0]['label']
            is_food_score = food_check[0]['score']
            print(f"  [SigLIP] food check: {is_food_label} ({is_food_score*100:.1f}%)")
            # Lowered threshold 0.60 → 0.45 so hands, body parts, objects are rejected more strictly
            if is_food_label == "a photo of something that is not food" and is_food_score > 0.45:
                return _not_food('SigLIP/siglip-base-patch16-224', 'image_classifier', int((time.time() - t0) * 1000))

            # ── SigLIP zero-shot: score ALL candidate foods against image ──────────
            clip_results = self.pipe_clip(img, candidate_labels=_CLIP_CANDIDATES, hypothesis_template="a photo of {}")
            elapsed = int((time.time() - t0) * 1000)
            print(f'  [SigLIP] {elapsed}ms — top5: '
                  f'{[(r["label"], round(r["score"]*100,1)) for r in clip_results[:5]]}')

            top_score = clip_results[0]['score']

            # Minimum food confidence floor — if even the best food label scores
            # below this threshold, nothing food-like was meaningfully identified.
            # SigLIP sigmoid scores are typically >0.005 for a clear food match.
            MIN_FOOD_SCORE = 0.002
            if top_score < MIN_FOOD_SCORE:
                print(f'  [SigLIP] top food score {top_score:.5f} below floor {MIN_FOOD_SCORE} → not_food')
                return _not_food('SigLIP/siglip-base-patch16-224', 'image_classifier', elapsed)

            found, seen = [], set()

            for r in clip_results:
                score = r['score']
                if len(found) > 0:
                    # Apply a relative and absolute threshold to secondary items
                    # Increased relative threshold from 0.03 to 0.20 and absolute floor from 0.0005 to 0.002
                    # to prevent low-probability background noise and false positives from being reported.
                    if score < max(top_score * 0.20, 0.002):
                        break
                db_name = self._db_name(r['label'])
                if db_name not in seen:
                    seen.add(db_name)
                    # Scale raw score to user-friendly confidence
                    confidence = _scale_siglip_confidence(score, is_top=(len(found) == 0))
                    found.append((db_name, confidence))
                if len(found) >= 5:
                    break

            print(f'  [SigLIP] selected {len(found)}: {[(f[0], f[1]) for f in found]}')

            if found:
                items = []
                for food_name, confidence in found:
                    hit = _db_lookup(food_name) or _usda_lookup(food_name) or _fallback_item(food_name)
                    hit['confidence'] = confidence
                    items.append(hit)
                return _ok_response(items, 'SigLIP/siglip-base-patch16-224', 'image_classifier', elapsed)

        # ── Fallback: Food-101 classifier ────────────────────────────────────
        if self.pipe_food101:
            preds = self.pipe_food101(img)
            elapsed = int((time.time() - t0) * 1000)
            print(f'  [Food101-fallback] {elapsed}ms — {[(p["label"], round(p["score"]*100,1)) for p in preds[:3]]}')
            top = preds[0]['score']
            found, seen = [], set()
            for p in preds:
                if p['score'] < max(top * 0.15, 0.08):
                    break
                name = p['label'].replace('_', ' ')
                if name not in seen:
                    seen.add(name)
                    confidence = _scale_confidence(p['score'], is_top=(len(found) == 0))
                    found.append((name, confidence))
                if len(found) >= 5:
                    break
            if found:
                items = []
                for food_name, confidence in found:
                    hit = _db_lookup(food_name) or _usda_lookup(food_name) or _fallback_item(food_name)
                    hit['confidence'] = confidence
                    items.append(hit)
                return _ok_response(items, 'Food101/nateraw-food', 'image_classifier', elapsed)


class GroqEngine:
    """Groq cloud vision model — Llama-4-Scout (2-3 s, needs GROQ_API_KEY)."""

    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        self.model   = 'meta-llama/llama-4-scout-17b-16e-instruct'
        self.loaded  = bool(self.api_key)
        status = '✅ enabled' if self.loaded else '❌ no GROQ_API_KEY'
        print(f'  [Groq]  cloud vision {status}')

    def predict(self, image_b64: str) -> dict:
        t0 = time.time()
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]

        resp = http_requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {self.api_key}',
                     'Content-Type':  'application/json'},
            json={
                'model': self.model,
                'messages': [{'role': 'user', 'content': [
                    {'type': 'text',      'text': VISION_PROMPT},
                    {'type': 'image_url', 'image_url': {
                        'url': f'data:image/jpeg;base64,{image_b64}'}}
                ]}],
                'max_tokens': 1024,
                'temperature': 0.1,
            },
            timeout=30
        )
        if resp.status_code != 200:
            err = resp.json().get('error', {}).get('message', resp.text[:200])
            raise RuntimeError(f'Groq API {resp.status_code}: {err}')

        answer  = resp.json()['choices'][0]['message']['content'].strip()
        elapsed = int((time.time() - t0) * 1000)
        print(f'  [Groq]  {elapsed}ms — {answer[:80]}')

        if 'NOT_FOOD' in answer.upper():
            return _not_food(f'Groq/{self.model}', 'cloud_llm', elapsed)

        items = _parse_pipe_response(answer)
        if not items:
            return _not_food(f'Groq/{self.model}', 'cloud_llm', elapsed,
                             tip='Could not parse food. Try a clearer photo.')

        return _ok_response(items, f'Groq/{self.model}', 'cloud_llm', elapsed)


# ──────────────────────────────────────────────────────────────────────────────
#  ENGINE 2 — OLLAMA  (Qwen2-VL-7B, 6-8 s CPU / <2 s GPU, zero API key)
# ──────────────────────────────────────────────────────────────────────────────

class OllamaEngine:
    """
    Local Ollama inference — Qwen2-VL-7B multimodal model.
    No API key. No HuggingFace token. No internet after first pull.

    Setup (one time):
        1. Install Ollama → https://ollama.com/download
        2. ollama pull qwen2-vl:7b
        3. ollama serve   (auto-starts on most systems)
    """

    DEFAULT_MODEL = 'llava-phi3'

    def __init__(self):
        self.base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model    = os.getenv('OLLAMA_MODEL', self.DEFAULT_MODEL)
        self.loaded   = self._check()

    def _check(self) -> bool:
        """Ping Ollama and verify the model is pulled."""
        try:
            r = http_requests.get(f'{self.base_url}/api/tags', timeout=3)
            if r.status_code != 200:
                print(f'  [Ollama] server not responding (status {r.status_code})')
                return False
            models = [m['name'] for m in r.json().get('models', [])]
            # Accept exact match or prefix match (e.g. qwen2-vl:7b == qwen2-vl:7b-instruct-q4_K_M)
            model_base = self.model.split(':')[0]
            found = any(model_base in m for m in models)
            if found:
                matched = next(m for m in models if model_base in m)
                print(f'  [Ollama] ✅ model ready → {matched}')
                return True
            else:
                print(f'  [Ollama] ⚠️  model "{self.model}" not pulled yet.')
                print(f'  [Ollama]    Run: ollama pull {self.model}')
                print(f'  [Ollama]    Available: {models}')
                return False
        except Exception as e:
            print(f'  [Ollama] ❌ not running ({e})')
            print( '  [Ollama]    Install: https://ollama.com/download')
            print(f'  [Ollama]    Then:    ollama pull {self.model}')
            return False

    def _ollama_ask(self, image_b64: str, prompt: str, num_predict: int = 80) -> str:
        """Send a single prompt+image to Ollama and return the text response."""
        resp = http_requests.post(
            f'{self.base_url}/api/generate',
            json={
                'model':      self.model,
                'prompt':     prompt,
                'images':     [image_b64],
                'stream':     False,
                'keep_alive': -1,
                'options': {
                    'temperature': 0.1,
                    'num_predict': num_predict,
                    'num_thread':  os.cpu_count() or 4,
                }
            },
            timeout=720
        )
        if resp.status_code != 200:
            raise RuntimeError(f'Ollama API {resp.status_code}: {resp.text[:200]}')
        return resp.json().get('response', '').strip()

    def _predict_moondream(self, image_b64: str) -> dict:
        """
        Moondream-specific single-step inference for speed.
        Identify foods separated by commas. If no food, reply NOT_FOOD.
        """
        t0 = time.time()

        food_list_raw = self._ollama_ask(
            image_b64,
            'Identify any food or drink items in this image. List them separated by commas. '
            'If no food or drink is visible, reply with NOT_FOOD.',
            num_predict=60
        )
        elapsed = int((time.time() - t0) * 1000)
        print(f'  [Ollama/moondream] {elapsed}ms — {food_list_raw!r}')

        if not food_list_raw.strip() or 'NOT_FOOD' in food_list_raw.upper():
            return _not_food(f'Ollama/{self.model}', 'local_llm', elapsed)

        raw_foods = [p.strip().lower() for p in food_list_raw.split(',')]
        raw_foods = [f for f in raw_foods if 2 < len(f) < 60][:5]
        if not raw_foods:
            raw_foods = [food_list_raw.strip()[:60]]

        items = []
        for food in raw_foods:
            hit = _db_lookup(food) or _usda_lookup(food) or _fallback_item(food)
            items.append(hit)

        if not items:
            return _not_food(f'Ollama/{self.model}', 'local_llm', elapsed)

        return _ok_response(items, f'Ollama/{self.model}', 'local_llm', elapsed)

    def predict(self, image_b64: str) -> dict:
        t0 = time.time()
        # Strip data-URL prefix
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]

        # Resize image — smaller = fewer vision tokens = faster on CPU
        image_b64 = _resize_image_b64(image_b64, max_px=256)

        # Moondream (1.7B) cannot follow complex pipe-format prompts reliably.
        # Use a simpler two-step approach for it.
        if 'moondream' in self.model.lower():
            return self._predict_moondream(image_b64)

        # ── Larger models (llava-phi3, qwen2-vl, etc.) — structured pipe format ──
        resp = http_requests.post(
            f'{self.base_url}/api/generate',
            json={
                'model':      self.model,
                'prompt':     VISION_PROMPT,
                'images':     [image_b64],
                'stream':     False,
                'keep_alive': -1,
                'options': {
                    'temperature': 0.1,
                    'num_predict': 150,
                    'num_thread':  os.cpu_count() or 4,
                }
            },
            timeout=720   # 12 min — cold start on CPU loads model first
        )
        if resp.status_code != 200:
            raise RuntimeError(f'Ollama API {resp.status_code}: {resp.text[:200]}')

        answer  = resp.json().get('response', '').strip()
        elapsed = int((time.time() - t0) * 1000)
        print(f'  [Ollama] {elapsed}ms — {answer[:80]}')

        if 'NOT_FOOD' in answer.upper():
            return _not_food(f'Ollama/{self.model}', 'local_llm', elapsed)

        items = _parse_pipe_response(answer)
        if not items:
            return _not_food(f'Ollama/{self.model}', 'local_llm', elapsed,
                             tip='Could not parse food. Try a clearer photo.')

        return _ok_response(items, f'Ollama/{self.model}', 'local_llm', elapsed)


# ──────────────────────────────────────────────────────────────────────────────
#  ENGINE 3 — MOONDREAM2  (transformers fallback, 15-30 s CPU)
# ──────────────────────────────────────────────────────────────────────────────

def _install_pyvips_stub():
    """
    pyvips compatibility stub for moondream2 (imported lazily — only when
    MoondreamEngine._load() is called, so numpy is not required otherwise).
    """
    if 'pyvips' in sys.modules:
        return
    import types as _types
    import numpy as _np          # only needed for Moondream fallback
    from PIL import Image as _PILImage

    class _VipsImage:
        def __init__(self, arr):
            self._arr = _np.asarray(arr, dtype=_np.uint8)

        @property
        def width(self):  return self._arr.shape[1]
        @property
        def height(self): return self._arr.shape[0]

        @classmethod
        def new_from_array(cls, arr, **kwargs):
            return cls(_np.asarray(arr, dtype=_np.uint8))

        def resize(self, hscale, vscale=None, **kwargs):
            if vscale is None:
                vscale = hscale
            new_w = max(1, int(round(self.width  * hscale)))
            new_h = max(1, int(round(self.height * vscale)))
            pil = _PILImage.fromarray(self._arr).resize(
                (new_w, new_h), _PILImage.BICUBIC)
            return _VipsImage(_np.asarray(pil, dtype=_np.uint8))

        def numpy(self):
            return self._arr.copy()

        def __array__(self, dtype=None):
            return self._arr if dtype is None else self._arr.astype(dtype)

    _stub = _types.ModuleType('pyvips')
    _stub.Image = _VipsImage
    sys.modules['pyvips'] = _stub


class MoondreamEngine:
    """Local Moondream2 1.8B VLM via transformers (last-resort fallback)."""

    MODEL_ID = 'vikhyatk/moondream2'
    REVISION  = '2025-01-09'
    _MAX_SIDE = 378

    def __init__(self):
        self.model    = None
        self.backend  = None
        self.loaded   = False
        self._hf_token = os.getenv('HF_TOKEN') or os.getenv('HUGGING_FACE_HUB_TOKEN')
        self._load()

    def _load(self):
        print('  [Moondream] loading...')
        _install_pyvips_stub()   # lazily inject pyvips stub before transformers import
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch.nn as _nn
            from transformers.modeling_utils import PreTrainedModel as _PTM
            _orig = _PTM.__dict__.get('__getattr__')
            _nn_ga = _nn.Module.__getattr__
            def _compat(self, name):
                if name == 'all_tied_weights_keys':
                    return {}
                if _orig:
                    return _orig(self, name)
                return _nn_ga(self, name)
            _PTM.__getattr__ = _compat
        except ImportError as e:
            print(f'  [Moondream] transformers not installed: {e}')
            return

        tok_kw = {'token': self._hf_token} if self._hf_token else {}
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.MODEL_ID, revision=self.REVISION,
                trust_remote_code=True, **tok_kw)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_ID, revision=self.REVISION,
                trust_remote_code=True, torch_dtype='auto',
                low_cpu_mem_usage=True, **tok_kw)
            self.model.eval()
            try:
                import torch
                torch.set_num_threads(os.cpu_count() or 4)
            except Exception:
                pass
            self.backend = 'transformers'
            self.loaded  = True
            print('  [Moondream] ✅ loaded via transformers')
        except Exception as e:
            print(f'  [Moondream] ❌ load failed: {e}')
            if '401' in str(e):
                self._auth_error = str(e)

    def _decode(self, b64: str) -> Image.Image:
        if ',' in b64:
            b64 = b64.split(',', 1)[1]
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
        if max(img.width, img.height) > self._MAX_SIDE:
            ratio = self._MAX_SIDE / max(img.width, img.height)
            img = img.resize(
                (max(1, int(img.width*ratio)), max(1, int(img.height*ratio))),
                Image.LANCZOS)
        return img

    def _ask(self, enc, prompt: str, max_tokens: int = 80) -> str:
        return self.model.answer_question(
            enc, prompt, self.tokenizer,
            num_beams=1, max_new_tokens=max_tokens).strip()

    def predict(self, image_b64: str) -> dict:
        t0 = time.time()
        if not self.loaded:
            return _not_food('Moondream2 (1.8B)', 'error',
                             int((time.time()-t0)*1000),
                             tip='Moondream model not loaded. Install transformers+torch.')
        img = self._decode(image_b64)
        enc = self.model.encode_image(img)

        # Step 1 — is there food?
        is_food = self._ask(enc, 'Is there food or a meal visible? Answer yes or no.', 5)
        if is_food.lower().startswith('no'):
            return _not_food('Moondream2 (1.8B)', 'multimodal_llm',
                             int((time.time()-t0)*1000))

        # Step 2 — what foods?
        food_list_raw = self._ask(
            enc,
            'What food or foods are in this image? '
            'List them separated by commas. Be specific. Maximum 5 foods.',
            60)

        elapsed = int((time.time() - t0) * 1000)
        print(f'  [Moondream] {elapsed}ms — {food_list_raw!r}')

        if not food_list_raw.strip():
            return _not_food('Moondream2 (1.8B)', 'multimodal_llm', elapsed)

        raw_foods = [p.strip().lower() for p in food_list_raw.split(',')]
        raw_foods = [f for f in raw_foods if 2 < len(f) < 60][:5]
        if not raw_foods:
            raw_foods = [food_list_raw.strip()[:60]]

        items = []
        for food in raw_foods:
            hit = _db_lookup(food) or _usda_lookup(food) or _fallback_item(food)
            items.append(hit)

        if not items:
            return _not_food('Moondream2 (1.8B)', 'multimodal_llm', elapsed)

        return _ok_response(items, 'Moondream2 (1.8B)', 'multimodal_llm', elapsed)


# ──────────────────────────────────────────────────────────────────────────────
#  RESPONSE BUILDERS
# ──────────────────────────────────────────────────────────────────────────────

def _not_food(model: str, mode: str, elapsed: int, tip: str = '') -> dict:
    return {
        'description': 'not_food',
        'items': [],
        'tips':  tip or 'No food detected. Please scan a food item.',
        '_meta': {'model': model, 'mode': mode, 'latency_ms': elapsed,
                  'top9': [], 'multi_food': False, 'rejected': True},
    }

def _ok_response(items: list, model: str, mode: str, elapsed: int) -> dict:
    # Enrich items: fill missing nutrition from DB/USDA
    enriched = []
    for it in items:
        if it.get('calories', 0) == 0:
            hit = _db_lookup(it['food_name']) or _usda_lookup(it['food_name'])
            if hit:
                it = hit
        enriched.append(it)

    desc = (f"{len(enriched)} foods: {', '.join(i['food_name'] for i in enriched)}"
            if len(enriched) > 1 else
            f"{enriched[0]['food_name']} ({enriched[0].get('confidence', 88)}% confidence)")

    return {
        'description': desc,
        'items':       enriched,
        'tips':        _tip(enriched[0]['food_name']),
        '_meta': {
            'model':      model,
            'mode':       mode,
            'latency_ms': elapsed,
            'top9':       [(i['food_name'], i.get('confidence', 88)) for i in enriched[:9]],
            'multi_food': len(enriched) > 1,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
#  FLASK APP
# ──────────────────────────────────────────────────────────────────────────────

app    = Flask(__name__)
engine = None   # set in __main__

# Rate limiting
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(get_remote_address, app=app,
                      default_limits=['200 per hour'],
                      storage_uri='memory://')
    print('  Rate limiter: active (200 req/hr)')
except ImportError:
    class _NoopLimiter:
        def limit(self, *a, **kw):
            def d(f): return f
            return d
    limiter = _NoopLimiter()


@app.before_request
def _preflight():
    if request.method == 'OPTIONS':
        r = app.make_response('')
        r.headers.update({
            'Access-Control-Allow-Origin':  '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        })
        return r, 204

@app.after_request
def _cors(response):
    response.headers.update({
        'Access-Control-Allow-Origin':  '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    })
    return response


@app.route('/api/health', methods=['GET'])
def health():
    active = type(engine).__name__ if engine else 'none'
    return jsonify({
        'status':  'ok',
        'service': 'NutriTrack AI Server (v3)',
        'engine':  active,
        'loaded':  getattr(engine, 'loaded', False),
        'port':    5002,
    })


@app.route('/api/llm/status', methods=['GET'])
def status():
    return jsonify({
        'loaded':  getattr(engine, 'loaded', False),
        'engine':  type(engine).__name__ if engine else 'none',
        'model':   getattr(engine, 'model', 'unknown'),
        'api_key': 'not required (Ollama/Moondream)',
    })


@app.route('/api/ai/analyze',  methods=['POST'])
@app.route('/api/llm/analyze', methods=['POST'])
@limiter.limit('30 per minute')
def analyze():
    data  = request.get_json() or {}
    image = data.get('image', '')
    if not image:
        return jsonify({'error': 'No image provided'}), 400
    if not engine:
        return jsonify({'error': 'No AI engine loaded'}), 503
    if not getattr(engine, 'loaded', False):
        return jsonify({'error': 'AI engine not ready'}), 503
    try:
        return jsonify(engine.predict(image))
    except Exception as e:
        print(f'  [Engine] error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/analyze/stream', methods=['POST'])
@app.route('/api/llm/analyze/stream', methods=['POST'])
@limiter.limit('30 per minute')
def analyze_stream():
    """
    SSE streaming endpoint — runs inference in a background thread and sends
    keep-alive 'thinking' heartbeats every 10 s to prevent HF's 60-second
    gateway timeout from killing the long-running moondream inference.

    Event stream format:
        data: {"status": "thinking"}   ← heartbeat every 10 s
        data: {"result": {...}}         ← final answer
        data: {"error": "..."}          ← on failure
    """
    from flask import Response, stream_with_context

    data  = request.get_json() or {}
    image = data.get('image', '')
    if not image:
        return jsonify({'error': 'No image provided'}), 400
    if not engine:
        return jsonify({'error': 'No AI engine loaded'}), 503
    if not getattr(engine, 'loaded', False):
        return jsonify({'error': 'AI engine not ready'}), 503

    result_q = queue.Queue()

    def _run():
        try:
            result_q.put(('ok', engine.predict(image)))
        except Exception as exc:
            result_q.put(('err', str(exc)))

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    def _generate():
        while True:
            try:
                status, payload = result_q.get(timeout=10)
                if status == 'ok':
                    yield f'data: {json.dumps({"result": payload})}\n\n'
                else:
                    yield f'data: {json.dumps({"error": payload})}\n\n'
                return
            except queue.Empty:
                # Still thinking — send a heartbeat so HF doesn't close the conn
                yield f'data: {json.dumps({"status": "thinking"})}\n\n'

    return Response(
        stream_with_context(_generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',   # disable nginx buffering on HF
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',         default='0.0.0.0')
    ap.add_argument('--port',         default=5002, type=int)
    ap.add_argument('--engine',       default='auto',
                    choices=['auto', 'vit', 'ollama', 'moondream'],
                    help='Force a specific engine (default: auto = ViT -> Ollama -> Moondream)')
    ap.add_argument('--ollama-model', default=None,
                    help='Override Ollama model name (default: moondream)')
    args = ap.parse_args()

    print()
    print('=' * 62)
    print('  NutriTrack — AI Food Analysis Server  (Ollama Edition)')
    print('=' * 62)

    if args.ollama_model:
        os.environ['OLLAMA_MODEL'] = args.ollama_model

    if args.engine == 'vit':
        engine = ViTFoodEngine()
        if not engine.loaded:
            print('  Failed to load ViT. Check transformers install.')
    elif args.engine == 'ollama':
        engine = OllamaEngine()
        if not engine.loaded:
            print('  Ollama not ready. Run: ollama pull moondream')
    elif args.engine == 'moondream':
        engine = MoondreamEngine()
    else:
        # AUTO priority: ViT (fast, 2-5s) -> Ollama -> Moondream
        print('  Trying ViT food classifier (fast, no API)...')
        vit = ViTFoodEngine()
        if vit.loaded:
            engine = vit
            print('  Engine: ViT/vit-base-patch16-224 (2-5 s CPU, no API)')
        else:
            print('  ViT failed — trying Ollama...')
            ollama = OllamaEngine()
            if ollama.loaded:
                engine = ollama
                print(f'  Engine: Ollama / {os.getenv("OLLAMA_MODEL","moondream")} (slow on CPU)')
            else:
                print('  Ollama not available — trying Moondream2 fallback...')
                md = MoondreamEngine()
                engine = md
                if md.loaded:
                    print('  Engine: Moondream2 (1.8B, ~25 s CPU)')
                else:
                    print('  No engine loaded.')
                    print('  Fix: pip install transformers torch')

    usda = '✅ enabled' if os.getenv('USDA_API_KEY') else '⚠️  optional — set USDA_API_KEY for 300k+ food lookup'
    print(f'  USDA API : {usda}')
    print()
    print('=' * 62)
    print(f'  Ready → http://localhost:{args.port}/api/ai/analyze')
    print('=' * 62)
    print()

    app.run(host=args.host, port=args.port, debug=False)