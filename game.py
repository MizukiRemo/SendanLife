import pygame
import sys
import time
import os
import cv2
import numpy as np
import threading

pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except:
    pygame.mixer.init()
pygame.mixer.set_num_channels(16)

screenInfo = pygame.display.Info()
screenW, screenH = screenInfo.current_w, screenInfo.current_h
screen = pygame.display.set_mode((screenW, screenH), pygame.FULLSCREEN)
pygame.display.set_caption("WEEEEEEEEEEEE")

gameIcon = pygame.image.load(os.path.join(os.path.dirname(__file__), "flower.png"))
pygame.display.set_icon(gameIcon)
theClock = pygame.time.Clock()

# states
MENU    = 0
SETTINGS = 1
PLAYING  = 2
PAUSED   = 3
LOADING  = 4
RESULT   = 5
currentState = MENU

# note types
NORMAL_NOTE   = 0
GLITCHED_NOTE = 1

# warning stuff
currentWarningType = 0
warningTimer = 0.0
WARNING_DURATION = 0.4

# bg video stuff
videoFrames       = []
videoFrameIdx     = 0
videoLoaded       = False
videoLoadProgress = 0.0
videoLoadStarted  = False
videoLoadThread   = None
videoFPS          = 10
pausedVideoFrame  = None
pausedVideoFrameIdx = 0
pausedVideoTime   = 0

BG_ALPHA = 30

# bpm / timing
theBPM        = 260
beatDuration  = 60 / theBPM
currentBeatT  = 0

PERFECT_WINDOW = 0.05
GREAT_WINDOW   = 0.10
GOOD_WINDOW    = 0.15

# track sizing
TRACK_PAD = 40
ZOOM_OPTIONS = [600, 900, screenW - TRACK_PAD * 2]
zoomIdx = 0

theTrackW = ZOOM_OPTIONS[zoomIdx]
theTrackH = screenH
laneW     = theTrackW // 4
noteW     = laneW - 10
noteH     = 20

defaultTrackX = (screenW - theTrackW) // 2
leftTrackX    = TRACK_PAD
rightTrackX   = screenW - theTrackW - TRACK_PAD
theTrackX     = defaultTrackX
theTrackY     = 0
targetTrackX  = defaultTrackX
TRACK_SLIDE_SPD = screenW * 4

lanesX = [theTrackX + i * laneW for i in range(4)]
judgeLineY = screenH - 120

# hidden modes
HIDE_NONE   = 0
HIDE_BOTTOM = 1
HIDE_TOP    = 2
hiddenMode  = HIDE_NONE
HIDE_COVER  = 0.2

# scoring
SCORE_PERFECT = 1000
SCORE_GREAT   = 800
SCORE_GOOD    = 500

HIT_COLOR_PERFECT  = (255, 255, 0)
HIT_COLOR_GREAT    = (255, 105, 180)
HIT_COLOR_GOOD     = (0, 255, 0)
HIT_COLOR_MISS     = (255, 0, 0)
HIT_COLOR_GLITCHED = (255, 0, 255)

# notes storage
notesByLane = {0: [], 1: [], 2: [], 3: []}
allNotes    = []

# game flags
gameRunning      = False
gameStartLogged  = False
isFlipped        = False
isInvincible     = False
isHardChart      = True
effectsOn        = True
isAutoPlay       = False
trackLost        = False

# music
musicLoaded    = False
musicPath      = None
theMusic       = None
musicStartTime = 0
musicPausedAt  = 0

# health / score
playerHP    = 500
maxHP       = 1000
noteSpeed   = 1200
myScore     = 0
totalNotes  = 0
perfectHits = 0
greatHits   = 0
goodHits    = 0
missHits    = 0
myCombo     = 0
bestCombo   = 0
lastResult  = ""

LOW_HP_THRESHOLD = 0.25

# flowers (auto-play power-up)
flowerCount    = 2
flowerAutoTime = 0.0
FLOWER_DURATION = 5.0

# effect events
effectQueue   = []
allEffects    = []
warningQueue  = []
WARN_ADVANCE  = 0.8  # show warning this many seconds before the effect hits

# recorded effects (dev tool)
recordedEffects = []

# glow per lane
laneGlow = {
    0: {"time": 0, "color": (255, 255, 255)},
    1: {"time": 0, "color": (255, 255, 255)},
    2: {"time": 0, "color": (255, 255, 255)},
    3: {"time": 0, "color": (255, 255, 255)},
}

SONG_TITLE       = "Sendan Life (katagiri remix)"
SONG_TITLE_DURATION = 3.0

loadingStartTime = 0
loadingDuration  = 1

# ── fonts ──────────────────────────────────────────────────────────────
smallFontSz  = max(24, int(screenH / 25))
medFontSz    = max(32, int(screenH / 18))
bigFontSz    = max(54, int(screenH / 11))
btnFontSz    = max(32, int(screenH / 18))

smallFont = pygame.font.SysFont(None, smallFontSz)
medFont   = pygame.font.SysFont(None, medFontSz)
bigFont   = pygame.font.SysFont(None, bigFontSz)
btnFont   = pygame.font.SysFont(None, btnFontSz)

# ── images ─────────────────────────────────────────────────────────────
flowerImg = None
remoImg   = None
bgPng     = None
bgJpg     = None
bgImg     = None        # bg2.jpg, loaded on result screen
bgImgReady = False

try:
    remoImg = pygame.image.load(os.path.join(os.path.dirname(__file__), "remo.png"))
except:
    pass

try:
    flowerImg = pygame.image.load(os.path.join(os.path.dirname(__file__), "flower.png"))
    flowerImg = pygame.transform.scale(flowerImg, (60, 60))
except:
    pass

def _loadAndFitImage(path, convert_alpha=False):
    """load an image and scale/crop it to fill the screen"""
    raw = pygame.image.load(path)
    if convert_alpha:
        raw = raw.convert_alpha()
    else:
        raw = raw.convert()
    pw, ph = raw.get_size()
    scale  = max(screenW / pw, screenH / ph)
    nw, nh = int(pw * scale), int(ph * scale)
    scaled = pygame.transform.scale(raw, (nw, nh))
    cx = (nw - screenW) // 2
    cy = (nh - screenH) // 2
    return scaled.subsurface(pygame.Rect(cx, cy, screenW, screenH)).copy()

try:
    bgPng = _loadAndFitImage(os.path.join(os.path.dirname(__file__), "bg.png"), convert_alpha=True)
except:
    pass

try:
    bgJpg = _loadAndFitImage(os.path.join(os.path.dirname(__file__), "bg.jpg"))
except:
    pass


# ── helpers ─────────────────────────────────────────────────────────────

def getJudgeY():
    return 120 if isFlipped else screenH - 120

def getNoteStartY():
    return screenH + 100 if isFlipped else -100

def getNoteY(spawnT, elapsedT):
    if isFlipped:
        return getNoteStartY() - noteSpeed * (elapsedT - spawnT)
    return getNoteStartY() + noteSpeed * (elapsedT - spawnT)


def recalcSpawnTimes():
    """figure out when each note should appear based on current speed/flip"""
    dist     = abs(getJudgeY() - getNoteStartY())
    fallTime = dist / noteSpeed if noteSpeed > 0 else 0
    for note in allNotes:
        note["spawnTime"] = note["hitTime"] - fallTime


def updateTrackLayout():
    """called whenever zoom changes — recalc all the track measurements"""
    global theTrackW, laneW, noteW
    global defaultTrackX, leftTrackX, rightTrackX, targetTrackX
    theTrackW     = ZOOM_OPTIONS[zoomIdx]
    laneW         = theTrackW // 4
    noteW         = laneW - 10
    defaultTrackX = (screenW - theTrackW) // 2
    leftTrackX    = TRACK_PAD
    rightTrackX   = screenW - theTrackW - TRACK_PAD
    targetTrackX  = defaultTrackX
    moveTrackTo(theTrackX)


def moveTrackTo(newX):
    global theTrackX, lanesX
    theTrackX = newX
    lanesX    = [theTrackX + i * laneW for i in range(4)]


# ── video loading (runs in background thread) ────────────────────────────

def _videoLoadThread():
    global videoFrames, videoLoaded, videoFPS, videoLoadProgress

    videoLoadProgress = 0.0
    videoFrames = []

    try:
        vidPath = os.path.join(os.path.dirname(__file__), "bga.mp4")
        if not os.path.exists(vidPath):
            print("bga.mp4 not found, skipping video")
            videoLoaded = False
            videoLoadProgress = 1.0
            return

        cap = cv2.VideoCapture(vidPath)
        if not cap.isOpened():
            videoLoaded = False
            videoLoadProgress = 1.0
            return

        origFPS      = cap.get(cv2.CAP_PROP_FPS)
        totalFrames  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        skipEvery    = max(1, int(origFPS / 10))
        expectedOut  = max(1, totalFrames // skipEvery)
        outW, outH   = 960, 540

        frameNum   = 0
        loadedSoFar = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frameNum % skipEvery == 0:
                frame = cv2.resize(frame, (outW, outH))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = np.transpose(frame, (1, 0, 2))
                videoFrames.append(pygame.surfarray.make_surface(frame))
                loadedSoFar += 1
                videoLoadProgress = min(0.99, loadedSoFar / expectedOut)
            frameNum += 1

        cap.release()
        videoFPS          = 10
        videoLoaded       = True
        videoLoadProgress = 1.0
        print(f"Video loaded: {loadedSoFar} frames @ {outW}x{outH}")

    except Exception as e:
        print(f"Video load failed: {e}")
        videoLoaded       = False
        videoLoadProgress = 1.0


def startLoadingVideo():
    global videoLoadStarted, videoLoadThread
    if videoLoadStarted:
        return
    videoLoadStarted = True
    videoLoadThread  = threading.Thread(target=_videoLoadThread, daemon=True)
    videoLoadThread.start()


# ── music ──────────────────────────────────────────────────────────────

def loadMusic():
    global musicLoaded, musicPath, theMusic
    if musicLoaded:
        return
    try:
        p = os.path.join(os.path.dirname(__file__), "audio.mp3")
        if os.path.exists(p):
            theMusic    = pygame.mixer.Sound(p)
            musicPath   = p
            musicLoaded = True
    except:
        pass

def playMusic():
    global musicStartTime
    if musicLoaded and theMusic:
        theMusic.play()
        musicStartTime = time.time()

def stopMusic():
    if theMusic:
        try: theMusic.stop()
        except: pass

def pauseMusic():
    try: pygame.mixer.pause()
    except: pass

def resumeMusic():
    try: pygame.mixer.unpause()
    except: pass


# ── hit sound ──────────────────────────────────────────────────────────

hitSound   = None
hitChannel = pygame.mixer.Channel(1)
try:
    hitPath = os.path.join(os.path.dirname(__file__), "hit.wav")
    if os.path.exists(hitPath):
        hitSound = pygame.mixer.Sound(hitPath)
        hitSound.set_volume(0.8)
except:
    pass

def playHitSound():
    if hitSound:
        try: hitChannel.play(hitSound)
        except: pass


# ── background image (result screen) ───────────────────────────────────

def loadResultBg():
    global bgImg, bgImgReady
    if bgImgReady:
        return
    try:
        p = os.path.join(os.path.dirname(__file__), "bg2.jpg")
        if os.path.exists(p):
            bgImg      = _loadAndFitImage(p)
            bgImgReady = True
    except:
        pass


# ── chart loading ───────────────────────────────────────────────────────

def loadChart():
    global notesByLane, allNotes
    notesByLane = {0: [], 1: [], 2: [], 3: []}
    allNotes    = []

    chartFile = "chart_2.txt" if isHardChart else "chart_1.txt"
    chartPath = os.path.join(os.path.dirname(__file__), chartFile)

    if not os.path.exists(chartPath):
        print(f"Chart not found: {chartFile}")
        return

    try:
        laneMap = {64: 0, 192: 1, 320: 2, 448: 3}
        with open(chartPath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) < 3:
                    continue
                lanePos = int(parts[0])
                timeMs  = int(parts[2].rstrip(';'))
                if lanePos not in laneMap:
                    continue

                lane = laneMap[lanePos]
                import random
                ntype = GLITCHED_NOTE if random.random() < 0.05 else NORMAL_NOTE

                note = {
                    "lane":      lane,
                    "y":         getNoteStartY(),
                    "hitTime":   timeMs / 1000.0,
                    "spawnTime": None,
                    "spawned":   False,
                    "type":      ntype,
                }
                notesByLane[lane].append(note)
                allNotes.append(note)

        for lane in notesByLane.values():
            lane.sort(key=lambda n: n["hitTime"])
        allNotes.sort(key=lambda n: n["hitTime"])

    except Exception as e:
        print(f"Chart load error: {e}")


# ── effect loading ──────────────────────────────────────────────────────

def loadEffects():
    global effectQueue, allEffects, warningQueue

    allEffects = []
    fxFile = "effect_2.txt" if isHardChart else "effect_1.txt"
    fxPath = os.path.join(os.path.dirname(__file__), fxFile)

    if not os.path.exists(fxPath):
        effectQueue  = []
        warningQueue = []
        return

    try:
        with open(fxPath, 'r', encoding='utf-8') as f:
            for line in f:
                for entry in line.strip().split(';'):
                    entry = entry.strip()
                    if not entry:
                        continue
                    parts = entry.split(',')
                    if len(parts) == 2:
                        ms  = int(parts[0].strip())
                        typ = int(parts[1].strip())
                        allEffects.append((ms / 1000.0, typ))

        allEffects.sort(key=lambda e: e[0])
        effectQueue  = list(allEffects)
        warningQueue = [(t - WARN_ADVANCE, typ) for t, typ in allEffects if t - WARN_ADVANCE > 0]
        warningQueue.sort(key=lambda e: e[0])
        print(f"Loaded {len(allEffects)} effects")

    except Exception as e:
        print(f"Effect load error: {e}")
        effectQueue  = []
        warningQueue = []


def applyEffect(typ):
    """actually do the effect — flip, slide, hide, zoom, etc."""
    global hiddenMode, isFlipped, targetTrackX, zoomIdx, currentWarningType
    currentWarningType = typ

    if typ == 1:
        hiddenMode = HIDE_TOP
    elif typ == 2:
        hiddenMode = HIDE_BOTTOM
    elif typ == 3:
        targetTrackX = leftTrackX
    elif typ == 4:
        # reset everything back to normal
        targetTrackX = defaultTrackX
        isFlipped    = False
        hiddenMode   = HIDE_NONE
    elif typ == 5:
        targetTrackX = rightTrackX
    elif typ == 6:
        isFlipped = not isFlipped
        recalcSpawnTimes()
    elif typ == 7:
        zoomIdx = (zoomIdx + 1) % len(ZOOM_OPTIONS)
        updateTrackLayout()
        targetTrackX = defaultTrackX


# ── judging hits ────────────────────────────────────────────────────────

def judgeHit(lane, isAuto=False):
    global lastResult, myCombo, bestCombo, playerHP, myScore
    global totalNotes, perfectHits, greatHits, goodHits, missHits

    laneNotes = notesByLane[lane]
    if not laneNotes:
        laneGlow[lane]["time"]  = 0.3
        laneGlow[lane]["color"] = (255, 255, 255)
        return

    best     = None
    bestDiff = float('inf')

    for note in laneNotes:
        if not note["spawned"]:
            continue
        noteScreenY  = theTrackY + note["y"]
        distToJudge  = getJudgeY() - noteScreenY
        timeToJudge  = (-distToJudge if isFlipped else distToJudge) / noteSpeed if noteSpeed > 0 else float('inf')

        if timeToJudge > GOOD_WINDOW:
            continue  # too early, not yet
        if abs(timeToJudge) < bestDiff:
            bestDiff = abs(timeToJudge)
            best     = note

    if best is None:
        laneGlow[lane]["time"]  = 0.3
        laneGlow[lane]["color"] = (255, 255, 255)
        return

    isGlitched  = best.get("type") == GLITCHED_NOTE
    scoreMult   = 5 if isGlitched else 1
    hpMult      = 5 if isGlitched else 1
    glowColor   = HIT_COLOR_GLITCHED if isGlitched else None

    def _finishHit(resultLabel, scoreAmt, hpPenalty, comboContinues):
        nonlocal glowColor
        global lastResult, myCombo, bestCombo, playerHP, myScore
        global totalNotes, perfectHits, greatHits, goodHits
        lastResult = resultLabel
        myScore   += scoreAmt * scoreMult
        if not isInvincible and hpPenalty > 0:
            playerHP = max(0, playerHP - hpPenalty * hpMult)
        if comboContinues:
            myCombo  += 1
            bestCombo = max(bestCombo, myCombo)
        else:
            myCombo = 0
        totalNotes += 1
        if resultLabel == "Perfect":  perfectHits += 1
        elif resultLabel == "Great":  greatHits   += 1
        elif resultLabel == "Good":   goodHits     += 1
        notesByLane[lane].remove(best)
        allNotes.remove(best)
        laneGlow[lane]["time"]  = 0.3
        laneGlow[lane]["color"] = glowColor if glowColor else {
            "Perfect": HIT_COLOR_PERFECT,
            "Great":   HIT_COLOR_GREAT,
            "Good":    HIT_COLOR_GOOD,
        }[resultLabel]
        playHitSound()

    if bestDiff <= PERFECT_WINDOW:
        _finishHit("Perfect", SCORE_PERFECT, 0,  True)
    elif bestDiff <= GREAT_WINDOW:
        _finishHit("Great",   SCORE_GREAT,   5,  True)
    elif bestDiff <= GOOD_WINDOW:
        _finishHit("Good",    SCORE_GOOD,    10, False)


# ── recorded effects (dev recording tool) ──────────────────────────────

def recordEffect(etype):
    if gameRunning and musicStartTime > 0:
        ms = int((time.time() - musicStartTime) * 1000)
        recordedEffects.append((ms, etype))
        print(f"[REC] {ms}ms → type {etype}")

def saveRecordedEffects():
    if not recordedEffects:
        return
    outPath = os.path.join(os.path.dirname(__file__), "output.txt")
    try:
        with open(outPath, 'w', encoding='utf-8') as f:
            for ms, typ in recordedEffects:
                f.write(f"{ms},{typ};\n")
        print(f"[REC] saved {len(recordedEffects)} entries → {outPath}")
    except Exception as e:
        print(f"[REC] save failed: {e}")


# ── reset ───────────────────────────────────────────────────────────────

def resetGame():
    global playerHP, maxHP, noteSpeed, myScore, totalNotes
    global perfectHits, greatHits, goodHits, missHits
    global myCombo, bestCombo, notesByLane, allNotes
    global lastResult, currentBeatT, gameStartLogged, trackLost, isFlipped
    global warningTimer, targetTrackX, zoomIdx, hiddenMode
    global effectQueue, warningQueue, recordedEffects
    global flowerCount, flowerAutoTime

    playerHP      = 500
    maxHP         = 500
    noteSpeed     = initialNoteSpeed
    myScore       = 0
    totalNotes    = 0
    perfectHits   = 0
    greatHits     = 0
    goodHits      = 0
    missHits      = 0
    myCombo       = 0
    bestCombo     = 0
    trackLost     = False
    isFlipped     = False
    warningTimer  = 0.0
    zoomIdx       = 0
    hiddenMode    = HIDE_NONE
    effectQueue   = list(allEffects)
    warningQueue  = [(t - WARN_ADVANCE, typ) for t, typ in allEffects if t - WARN_ADVANCE > 0]
    warningQueue.sort(key=lambda e: e[0])
    targetTrackX  = defaultTrackX
    updateTrackLayout()
    moveTrackTo(defaultTrackX)
    notesByLane   = {0: [], 1: [], 2: [], 3: []}
    allNotes      = []
    lastResult    = ""
    currentBeatT  = 0
    gameStartLogged = False
    recordedEffects = []
    flowerCount    = 2
    flowerAutoTime = 0.0
    for i in range(4):
        laneGlow[i]["time"]  = 0
        laneGlow[i]["color"] = (255, 255, 255)
    # clean up draw_game stash
    for attr in ("debugPrinted", "noteDebugPrinted", "clearTime"):
        if hasattr(drawGame, attr):
            delattr(drawGame, attr)


# ── drawing helpers ─────────────────────────────────────────────────────

def drawGlow(surface, x, y, w, h, color, ratio):
    if ratio <= 0:
        return
    cx, cy    = x + w // 2, y + h // 2
    maxExpand = int(40 * ratio)
    for i in range(3, 0, -1):
        expand = int(maxExpand * i / 3)
        alpha  = int(100 * ratio * (0.5 - i / 6))
        if alpha > 0:
            r = pygame.Rect(cx - w//2 - expand, cy - h//2 - expand, w + 2*expand, h + 2*expand)
            pygame.draw.rect(surface, (*color, alpha), r)
    pygame.draw.rect(surface, (*color, int(255 * ratio)), pygame.Rect(x, y, w, h))


def drawWarningTriangle(surface, ratio, etype=0):
    if ratio <= 0:
        return
    cx   = theTrackX + theTrackW // 2
    cy   = screenH // 2
    size = int(min(screenW, screenH) * 0.05)
    a    = int(255 * ratio)

    tri = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
    pts = [
        (size,             int(size * 0.1)),
        (int(size * 0.05), int(size * 1.85)),
        (int(size * 1.95), int(size * 1.85)),
    ]
    pygame.draw.polygon(tri, (220, 30, 30, a), pts)
    pygame.draw.polygon(tri, (255, 255, 255, min(255, a + 40)), pts, 4)

    exFont = pygame.font.SysFont(None, int(size * 1.2))
    exSurf = exFont.render("!", True, (255, 255, 255))
    exSurf.set_alpha(a)
    tri.blit(exSurf, exSurf.get_rect(center=(size, int(size * 1.1))))
    surface.blit(tri, (cx - size, cy - size))

    # draw the directional arrow/cross hint
    tmp         = pygame.Surface((screenW, screenH), pygame.SRCALPHA)
    arrowColor  = (255, 255, 255, a)
    crossColor  = (255, 60, 60, a)

    def arrow(ox, oy, direction):
        s = size
        dirs = {
            'left':  [(ox, oy), (ox+s, oy-s//2), (ox+s, oy+s//2)],
            'right': [(ox, oy-s//2), (ox, oy+s//2), (ox+s, oy)],
            'up':    [(ox, oy), (ox-s//2, oy+s), (ox+s//2, oy+s)],
            'down':  [(ox, oy+s), (ox-s//2, oy), (ox+s//2, oy)],
        }
        pygame.draw.polygon(tmp, arrowColor, dirs[direction])

    def cross(ox, oy):
        s = size // 2
        pygame.draw.line(tmp, crossColor, (ox-s, oy-s), (ox+s, oy+s), 5)
        pygame.draw.line(tmp, crossColor, (ox+s, oy-s), (ox-s, oy+s), 5)

    lx = cx - size * 3
    rx = cx + size * 2
    ay = cy - size * 2
    by = cy + size * 2

    if   etype == 1: arrow(cx, ay-30, 'up');   cross(cx, ay-20)
    elif etype == 2: arrow(cx, by, 'down');    cross(cx, by+10)
    elif etype == 3: arrow(lx, cy, 'left')
    elif etype == 4: arrow(cx, by, 'down')
    elif etype == 5: arrow(rx, cy, 'right')
    elif etype == 6: arrow(cx, ay-30, 'up')
    elif etype == 7:
        arrow(lx, cy, 'left'); arrow(rx, cy, 'right')
        arrow(cx, ay-30, 'up'); arrow(cx, by, 'down')

    surface.blit(tmp, (0, 0))


def drawSongTitle(surface, elapsed):
    if elapsed < 0 or elapsed > SONG_TITLE_DURATION:
        return
    fadeIn = 0.5;  fadeOut = 0.5
    dispT  = SONG_TITLE_DURATION - fadeIn - fadeOut
    if elapsed < fadeIn:
        ratio = elapsed / fadeIn
    elif elapsed < fadeIn + dispT:
        ratio = 1.0
    else:
        ratio = (SONG_TITLE_DURATION - elapsed) / fadeOut

    tf   = pygame.font.SysFont(None, int(bigFontSz * 0.8))
    surf = tf.render(SONG_TITLE, True, (100, 200, 255))
    surf.set_alpha(int(255 * ratio))
    surface.blit(surf, surf.get_rect(center=(screenW // 2, screenH // 2)))


def drawTrackBase(surface):
    """draw the dark track background + lane dividers"""
    trackSurf = pygame.Surface((theTrackW, theTrackH))
    trackSurf.fill((20, 20, 20))
    for i in range(4):
        pygame.draw.rect(trackSurf, (50, 50, 50), (i * laneW, 0, laneW, theTrackH))
    trackSurf.set_alpha(127)
    surface.blit(trackSurf, (theTrackX, theTrackY))


def drawHealthBar(surface):
    bw = 12
    bx = theTrackX - bw - 20
    pygame.draw.rect(surface, (100, 100, 100), (bx, 0, bw, screenH), 2)
    ratio = playerHP / maxHP
    fillH = int(ratio * screenH)
    pygame.draw.rect(surface, (0, 255, 0), (bx, screenH - fillH, bw, fillH))


def drawHUD(surface):
    # accuracy top-right
    if totalNotes > 0:
        acc = (perfectHits * 1.0 + greatHits * 0.8 + goodHits * 0.5) / totalNotes * 100
    else:
        acc = 0
    accSurf = smallFont.render(f"Accuracy: {acc:.1f}%", True, (255, 255, 255))
    surface.blit(accSurf, (screenW - accSurf.get_width() - int(screenW * 0.02), int(screenH * 0.02)))

    # score top-left
    scoreSurf = smallFont.render(f"Score: {myScore}", True, (255, 255, 0))
    surface.blit(scoreSurf, (int(screenW * 0.02), int(screenH * 0.02)))

    # combo
    comboSurf = medFont.render(f"{myCombo} Combo", True, (255, 255, 0))
    surface.blit(comboSurf, (theTrackX + theTrackW // 2 - comboSurf.get_width() // 2, theTrackY + 80))

    # last hit result
    rcolor = {
        "Perfect": HIT_COLOR_PERFECT,
        "Great":   HIT_COLOR_GREAT,
        "Good":    HIT_COLOR_GOOD,
    }.get(lastResult, HIT_COLOR_MISS)
    rSurf = smallFont.render(lastResult, True, rcolor)
    surface.blit(rSurf, (theTrackX + theTrackW // 2 - rSurf.get_width() // 2, theTrackY + 30))


# ── screen drawing ──────────────────────────────────────────────────────

def drawMenu():
    screen.fill((30, 30, 30))
    if bgPng: screen.blit(bgPng, (0, 0))
    if bgJpg: screen.blit(bgJpg, (0, 0))

    t1 = bigFont.render("Sendan Life", True, (0, 200, 255))
    t2 = bigFont.render("From -Vitreous Flower And Destroy The World-", True, (0, 200, 255))
    screen.blit(t1, t1.get_rect(center=(screenW // 2, screenH // 4)))
    screen.blit(t2, t2.get_rect(center=(screenW // 2, screenH // 4 + bigFontSz + 10)))

    btnStart.draw(screen)
    if remoImg:
        screen.blit(remoImg, (screenW//2 - remoImg.get_width()//2, screenH - remoImg.get_height()))


def drawSettings():
    screen.fill((30, 30, 30))
    if bgPng: screen.blit(bgPng, (0, 0))
    if bgJpg: screen.blit(bgJpg, (0, 0))

    titleSurf = medFont.render("Settings", True, (0, 200, 255))
    screen.blit(titleSurf, titleSurf.get_rect(center=(screenW // 2, screenH // 10)))

    yp = screenH // 5
    secFont = pygame.font.SysFont(None, int(smallFontSz * 1.2))

    screen.blit(secFont.render("Judgement Timing:", True, (0, 255, 100)), (int(screenW * 0.1), yp))
    yp += smallFontSz + 20

    for line in [
        f"PERFECT: +/-{int(PERFECT_WINDOW*1000)}ms (Yellow)",
        f"GREAT:   +/-{int(GREAT_WINDOW*1000)}ms (Pink)",
        f"GOOD:    +/-{int(GOOD_WINDOW*1000)}ms (Green)",
        f"MISS:    Beyond range (Red)",
    ]:
        screen.blit(smallFont.render(line, True, (200, 200, 200)), (int(screenW * 0.15), yp))
        yp += smallFontSz + 10

    yp += 10
    screen.blit(secFont.render("Key Bindings:", True, (0, 255, 100)), (int(screenW * 0.1), yp))
    yp += smallFontSz + 20

    for line in [
        "Lane 1: D", "Lane 2: F", "Lane 3: J", "Lane 4: K",
        "Space: Consume 1 Flower To Enable",
        "             Auto-Play For 5 Seconds",
        "ESC: Pause/Resume/Menu",
    ]:
        screen.blit(smallFont.render(line, True, (200, 200, 200)), (int(screenW * 0.15), yp))
        yp += smallFontSz + 10

    # right column
    rx = int(screenW * 0.60)
    pygame.draw.line(screen, (80, 80, 80), (rx - 30, int(screenH * 0.15)), (rx - 30, int(screenH * 0.90)), 2)
    screen.blit(secFont.render("Options:", True, (0, 255, 100)), (rx, int(screenH * 0.15)))

    toggleAutoPlay.draw(screen)
    toggleHP.draw(screen)
    toggleChart.draw(screen)
    toggleEffects.draw(screen)

    # video loading bar
    bx = int(screenW * 0.02) + btnW + 20
    by = screenH - btnH // 2 - 14 - int(screenH * 0.02)
    bw = screenW - (bx) * 2

    if videoLoadProgress < 1.0:
        statusTxt   = f"ViOS being rebuilt... {int(videoLoadProgress * 100)}%"
        statusColor = (200, 200, 100)
    elif videoLoaded:
        statusTxt   = f"Video ready  ({len(videoFrames)} frames)"
        statusColor = (100, 255, 100)
    else:
        statusTxt   = "Video not found (bga.mp4)"
        statusColor = (200, 100, 100)

    screen.blit(smallFont.render(statusTxt, True, statusColor), (bx, by - smallFontSz - 6))
    pygame.draw.rect(screen, (60, 60, 60), (bx, by, bw, 28), border_radius=6)
    fillW = int(bw * videoLoadProgress)
    if fillW > 0:
        fc = (0, 200, 100) if videoLoadProgress >= 1.0 else (0, 150, 220)
        pygame.draw.rect(screen, fc, (bx, by, fillW, 28), border_radius=6)
    pygame.draw.rect(screen, (160, 160, 160), (bx, by, bw, 28), 2, border_radius=6)

    btnStartGame.disabled = videoLoadProgress < 1.0
    btnBack.draw(screen)
    btnStartGame.draw(screen)


def drawGame():
    screen.fill((30, 30, 30))

    # background video
    if videoLoaded and videoFrames:
        if gameRunning and musicStartTime > 0:
            elapsed   = time.time() - musicStartTime
            frameIdx  = int(elapsed * videoFPS) % len(videoFrames)
        else:
            frameIdx = 0
        try:
            frame = videoFrames[frameIdx].copy()
            frame = pygame.transform.scale(frame, (screenW, screenH))
            frame.set_alpha(BG_ALPHA)
            screen.blit(frame, (0, 0))
        except:
            pass

    drawTrackBase(screen)
    drawHealthBar(screen)
    drawHUD(screen)

    # judge line markers
    for lx in lanesX:
        pygame.draw.rect(screen, (255, 255, 255),
                         pygame.Rect(lx + 5, getJudgeY() - noteH // 2, noteW, noteH), 2)

    # notes
    jy = getJudgeY()
    for note in allNotes:
        nx  = lanesX[note["lane"]] + 5
        ny  = theTrackY + note["y"]
        col = HIT_COLOR_GLITCHED if note["type"] == GLITCHED_NOTE else (0, 200, 255)

        # hidden mode fading
        alpha = 255
        if hiddenMode == HIDE_BOTTOM:
            fadePx = int(screenH * 0.12)
            if not isFlipped:
                coverEnd   = jy * 0.20
                fadeEnd    = jy - coverEnd
                fadeStart  = fadeEnd - fadePx
                if ny >= fadeEnd:   alpha = 0
                elif ny >= fadeStart: alpha = int(255 * (1.0 - (ny - fadeStart) / fadePx))
            else:
                coverStart = jy + (screenH - jy) * 0.20
                fadeEnd    = coverStart + fadePx
                if ny <= coverStart: alpha = 0
                elif ny <= fadeEnd:  alpha = int(255 * (ny - coverStart) / fadePx)

        elif hiddenMode == HIDE_TOP:
            fadePx = int(screenH * 0.12)
            if not isFlipped:
                coverPx   = jy * 0.20
                fadeStart = coverPx
                fadeEnd   = coverPx + fadePx
                if ny <= fadeStart:  alpha = 0
                elif ny <= fadeEnd:  alpha = int(255 * (ny - fadeStart) / fadePx)
            else:
                coverEnd  = screenH - (screenH - jy) * 0.20
                fadeStart = coverEnd - fadePx
                if ny >= coverEnd:   alpha = 0
                elif ny >= fadeStart: alpha = int(255 * (1.0 - (ny - fadeStart) / fadePx))

        alpha = max(0, min(255, alpha))
        if alpha == 0:
            continue
        if alpha < 255:
            s = pygame.Surface((noteW, noteH), pygame.SRCALPHA)
            s.fill((*col, alpha))
            screen.blit(s, (nx, ny))
        else:
            pygame.draw.rect(screen, col, (nx, ny, noteW, noteH))

    # lane glow
    dtMs = theClock.get_time()
    for lane in range(4):
        if laneGlow[lane]["time"] > 0:
            lx    = lanesX[lane] + 5
            ly    = getJudgeY() - noteH // 2
            ratio = laneGlow[lane]["time"] / 0.3
            drawGlow(screen, lx, ly, noteW, noteH, laneGlow[lane]["color"], ratio)
            laneGlow[lane]["time"] -= dtMs / 1000

    # low HP vignette
    if not isInvincible and playerHP / maxHP < LOW_HP_THRESHOLD:
        pulse     = abs((time.time() % 1.2) - 0.6) / 0.6
        hpRatio   = (playerHP / maxHP) / LOW_HP_THRESHOLD
        intensity = (1.0 - hpRatio) * 0.6 + pulse * 0.4
        vignette  = pygame.Surface((screenW, screenH), pygame.SRCALPHA)
        for i in range(80):
            t     = i / 80
            a     = int(200 * intensity * (1.0 - t) ** 1.5)
            inset = int(t * min(screenW, screenH) * 0.38)
            r     = pygame.Rect(inset, inset, screenW - inset*2, screenH - inset*2)
            if r.width > 0 and r.height > 0:
                pygame.draw.rect(vignette, (200, 0, 0, a), r, 3)
        screen.blit(vignette, (0, 0))

    # warning flash
    if warningTimer > 0:
        ratio = min(1.0, warningTimer / (WARNING_DURATION * 0.3))
        drawWarningTriangle(screen, ratio * 0.30, currentWarningType)

    # flower icons (power-up charges)
    if flowerImg:
        for i in range(flowerCount):
            screen.blit(flowerImg, (int(screenW * 0.02) + i * 70, screenH - 80))
        for i in range(flowerCount, 2):
            dim = flowerImg.copy()
            dim.set_alpha(60)
            screen.blit(dim, (int(screenW * 0.02) + i * 70, screenH - 80))

    # auto-play countdown timer
    if flowerAutoTime > 0:
        tf   = pygame.font.SysFont(None, int(screenH * 0.12))
        surf = tf.render(f"{flowerAutoTime:.2f}", True, (255, 50, 50))
        screen.blit(surf, surf.get_rect(center=(screenW // 2, screenH // 2)))

    # mode label bottom-right
    modeLabel  = "INVINCIBLE" if isInvincible else "NORMAL"
    modeColor  = (255, 200, 0) if isInvincible else (150, 150, 150)
    chartLabel = "Destroyed" if isHardChart else "Vitreous"
    modeSurf   = smallFont.render(f"HP: {modeLabel}  Difficulty: {chartLabel}", True, modeColor)
    screen.blit(modeSurf, (screenW - modeSurf.get_width() - int(screenW * 0.02),
                            screenH - smallFontSz - int(screenH * 0.02)))


def drawPause():
    screen.fill((30, 30, 30))

    if pausedVideoFrame:
        frm = pygame.transform.scale(pausedVideoFrame, (screenW, screenH))
        frm.set_alpha(BG_ALPHA)
        screen.blit(frm, (0, 0))

    drawTrackBase(screen)
    drawHealthBar(screen)
    drawHUD(screen)

    for lx in lanesX:
        pygame.draw.rect(screen, (255, 255, 255),
                         pygame.Rect(lx + 5, judgeLineY - noteH // 2, noteW, noteH), 2)

    for note in allNotes:
        col = HIT_COLOR_GLITCHED if note["type"] == GLITCHED_NOTE else (0, 200, 255)
        pygame.draw.rect(screen, col,
                         (lanesX[note["lane"]] + 5, theTrackY + note["y"], noteW, noteH))

    # dim overlay
    overlay = pygame.Surface((screenW, screenH))
    overlay.set_alpha(128)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    pauseTitle = bigFont.render("PAUSED", True, (255, 200, 0))
    screen.blit(pauseTitle, pauseTitle.get_rect(center=(screenW // 2, screenH // 4)))

    btnResume.draw(screen)
    btnPauseRestart.draw(screen)
    btnPauseMenu.draw(screen)

    recSurf = smallFont.render(f"[REC] {len(recordedEffects)} effects recorded so far", True, (180, 255, 180))
    screen.blit(recSurf, (int(screenW * 0.02), int(screenH * 0.95)))


def drawResult():
    screen.fill((30, 30, 30))
    if not trackLost:
        loadResultBg()
    if bgImgReady and bgImg:
        bg = bgImg.copy()
        bg.set_alpha(120)
        screen.blit(bg, (0, 0))

    titleText  = "TRACK LOST" if trackLost else "RESULTS"
    titleColor = (255, 60, 60) if trackLost else (255, 200, 0)
    titleSurf  = bigFont.render(titleText, True, titleColor)
    screen.blit(titleSurf, titleSurf.get_rect(center=(screenW // 2, int(screenH * 0.08))))

    # accuracy / grade
    if totalNotes > 0:
        acc = (perfectHits * 1.0 + greatHits * 0.8 + goodHits * 0.5) / totalNotes * 100
    else:
        acc = 0

    if trackLost:
        grade, gradeColor = "F", (255, 80, 80)
    elif acc == 100:  grade, gradeColor = "AP",  (255, 215, 0)
    elif acc >= 95:   grade, gradeColor = "SSS", (255, 215, 0)
    elif acc >= 93:   grade, gradeColor = "SS",  (255, 215, 0)
    elif acc >= 90:   grade, gradeColor = "S",   (255, 215, 0)
    elif acc >= 85:   grade, gradeColor = "A",   (0, 220, 100)
    elif acc >= 80:   grade, gradeColor = "B",   (0, 200, 255)
    elif acc >= 70:   grade, gradeColor = "C",   (200, 200, 200)
    else:             grade, gradeColor = "F",   (255, 80, 80)

    gradeFont = pygame.font.SysFont(None, int(bigFontSz * 2.2))
    gradeSurf = gradeFont.render(grade, True, gradeColor)
    screen.blit(gradeSurf, gradeSurf.get_rect(center=(int(screenW * 0.78), int(screenH * 0.42))))

    yp = int(screenH * 0.18)
    for line in [
        (f"PERFECT: {perfectHits}", (200, 200, 200), smallFont),
        (f"GREAT:   {greatHits}",   (200, 200, 200), smallFont),
        (f"GOOD:    {goodHits}",    (200, 200, 200), smallFont),
        (f"MISS:    {missHits}",    (200, 200, 200), smallFont),
        ("", None, smallFont),
        (f"Max Combo: {bestCombo}",  (255, 160, 50),  medFont),
        (f"Accuracy: {acc:.1f}%",   (255, 255, 0),   medFont),
        (f"Score: {myScore}",       (0, 200, 255),   medFont),
    ]:
        txt, col, fnt = line
        if txt and col:
            s = fnt.render(txt, True, col)
            screen.blit(s, s.get_rect(center=(int(screenW * 0.35), yp)))
        yp += smallFontSz + 15

    btnResultRestart.draw(screen)
    btnResultMenu.draw(screen)

    tf   = pygame.font.SysFont(None, int(bigFontSz * 0.6))
    surf = tf.render(SONG_TITLE, True, (100, 200, 255))
    screen.blit(surf, surf.get_rect(center=(screenW // 2, int(screenH * 0.95))))


# ── buttons / UI elements ───────────────────────────────────────────────

class Button:
    def __init__(self, x, y, w, h, label, color, textColor):
        self.rect      = pygame.Rect(x, y, w, h)
        self.label     = label
        self.color     = color
        self.textColor = textColor
        self.hovered   = False
        self.disabled  = False

    def draw(self, surface):
        if self.disabled:
            bg  = (60, 60, 60)
            tc  = (120, 120, 120)
            bc  = (80, 80, 80)
        else:
            bg  = tuple(min(c + 30, 255) for c in self.color) if self.hovered else self.color
            tc  = self.textColor
            bc  = (255, 255, 255)
        pygame.draw.rect(surface, bg, self.rect)
        pygame.draw.rect(surface, bc, self.rect, 3)
        s = btnFont.render(self.label, True, tc)
        surface.blit(s, s.get_rect(center=self.rect.center))

    def isClicked(self, pos):
        return not self.disabled and self.rect.collidepoint(pos)

    def updateHover(self, pos):
        self.hovered = not self.disabled and self.rect.collidepoint(pos)


class ToggleButton:
    def __init__(self, x, y, w, h, label, optA, optB, startState=False):
        self.rect   = pygame.Rect(x, y, w, h)
        self.label  = label
        self.optA   = optA
        self.optB   = optB
        self.state  = startState  # False = A, True = B

    def draw(self, surface):
        surface.blit(smallFont.render(self.label, True, (200, 200, 200)),
                     (self.rect.x, self.rect.y - 35))
        hw     = self.rect.width // 2
        leftR  = pygame.Rect(self.rect.x,      self.rect.y, hw, self.rect.height)
        rightR = pygame.Rect(self.rect.x + hw, self.rect.y, hw, self.rect.height)
        pygame.draw.rect(surface, (0, 150, 200)  if not self.state else (50, 50, 50), leftR,  border_radius=8)
        pygame.draw.rect(surface, (200, 80, 0)   if self.state     else (50, 50, 50), rightR, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=8)
        surface.blit(btnFont.render(self.optA, True, (255,255,255)), btnFont.render(self.optA, True, (255,255,255)).get_rect(center=leftR.center))
        surface.blit(btnFont.render(self.optB, True, (255,255,255)), btnFont.render(self.optB, True, (255,255,255)).get_rect(center=rightR.center))

    def handleClick(self, pos):
        if not self.rect.collidepoint(pos):
            return False
        hw     = self.rect.width // 2
        leftR  = pygame.Rect(self.rect.x, self.rect.y, hw, self.rect.height)
        self.state = not leftR.collidepoint(pos)
        return True


class Slider:
    def __init__(self, x, y, w, h, minV, maxV, initV, label):
        self.rect     = pygame.Rect(x, y, w, h)
        self.minV     = minV
        self.maxV     = maxV
        self.value    = initV
        self.label    = label
        self.trackX   = x + 10
        self.trackW   = w - 20
        self.trackY   = y + h // 2
        self.dragging = False
        self.knobR    = 8

    def draw(self, surface):
        surface.blit(smallFont.render(f"{self.label}: {self.value}", True, (255,255,255)),
                     (self.rect.x, self.rect.y - 30))
        pygame.draw.line(surface, (100,100,100),
                         (self.trackX, self.trackY), (self.trackX + self.trackW, self.trackY), 3)
        kx = self.trackX + (self.value - self.minV) / (self.maxV - self.minV) * self.trackW
        pygame.draw.circle(surface, (0, 200, 255), (int(kx), self.trackY), self.knobR)

    def update(self, pos):
        if self.dragging:
            kx = max(self.trackX, min(pos[0], self.trackX + self.trackW))
            self.value = int(self.minV + (kx - self.trackX) / self.trackW * (self.maxV - self.minV))

    def onMouseDown(self, pos):
        kx = self.trackX + (self.value - self.minV) / (self.maxV - self.minV) * self.trackW
        if abs(pos[0] - kx) < 20 and abs(pos[1] - self.trackY) < 20:
            self.dragging = True

    def onMouseUp(self):
        self.dragging = False


# ── button instances ────────────────────────────────────────────────────

btnW = max(150, int(screenW * 0.3))
btnH = max(50,  int(screenH * 0.08))

btnStart        = Button(screenW//2 - btnW//2, screenH//2 - btnH - 20, btnW, btnH, "START",    (0, 150, 200),  (255,255,255))
btnSettings     = Button(screenW//2 - btnW//2, screenH//2 + 20,         btnW, btnH, "SETTINGS", (50, 150, 150), (255,255,255))
btnBack         = Button(int(screenW*0.02), screenH - btnH - int(screenH*0.02), btnW, btnH, "BACK", (150,50,50), (255,255,255))
btnStartGame    = Button(screenW - btnW - int(screenW*0.02), screenH - btnH - int(screenH*0.02), btnW, btnH, "START", (0,150,200), (255,255,255))

btnResume       = Button(screenW//2 - btnW//2, screenH//2 - 100, btnW, btnH, "RESUME",  (0, 200, 100),  (255,255,255))
btnPauseRestart = Button(screenW//2 - btnW//2, screenH//2,       btnW, btnH, "RESTART", (200, 100, 0),  (255,255,255))
btnPauseMenu    = Button(screenW//2 - btnW//2, screenH//2 + 100, btnW, btnH, "MENU",    (150, 50, 50),  (255,255,255))

btnResultRestart = Button(screenW//2 - btnW//2, screenH//2 + 100, btnW, btnH, "RESTART", (200,100,0),  (255,255,255))
btnResultMenu    = Button(screenW//2 - btnW//2, screenH//2 + 200, btnW, btnH, "MENU",    (150,50,50),  (255,255,255))

# ── settings toggles ────────────────────────────────────────────────────

toggleW = max(260, int(screenW * 0.28))
toggleH = max(50,  int(screenH * 0.07))
toggleX = int(screenW * 0.60)

toggleAutoPlay = ToggleButton(toggleX, int(screenH*0.22), toggleW, toggleH, "Auto Play",   "OFF", "ON",       False)
toggleHP       = ToggleButton(toggleX, int(screenH*0.40), toggleW, toggleH, "HP",          "Normal", "Invincible", False)
toggleChart    = ToggleButton(toggleX, int(screenH*0.58), toggleW, toggleH, "Difficulty",  "Vitreous", "Destroyed",  True)
toggleEffects  = ToggleButton(toggleX, int(screenH*0.72), toggleW, toggleH, "Virus",       "OFF", "ON",       True)

# ── sliders ─────────────────────────────────────────────────────────────

sliderW = max(300, int(screenW * 0.4))
initialNoteSpeed = max(200, min(2000, int((screenH - 120) / beatDuration)))

hpSlider    = Slider(screenW//2 - sliderW//2, int(screenH*0.35), sliderW, 50, 100,  1000, 500,              "Health")
speedSlider = Slider(screenW//2 - sliderW//2, int(screenH*0.55), sliderW, 50, 200,  2000, initialNoteSpeed, "Speed")

noteSpeed = initialNoteSpeed  # set actual game speed from initial


# ── main loop ───────────────────────────────────────────────────────────

while True:
    dt       = theClock.tick(60) / 1000
    mousePos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            saveRecordedEffects()
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if currentState == PLAYING:
                    pauseMusic()
                    if videoLoaded and videoFrames:
                        elapsed = time.time() - musicStartTime
                        pausedVideoTime  = elapsed
                        pausedVideoFrameIdx = int(elapsed * videoFPS) % len(videoFrames)
                        pausedVideoFrame = videoFrames[pausedVideoFrameIdx].copy()
                    musicPausedAt = time.time()
                    currentState  = PAUSED
                elif currentState == PAUSED:
                    resumeMusic()
                    musicStartTime   = time.time() - pausedVideoTime
                    pausedVideoFrame = None
                    currentState     = PLAYING
                else:
                    saveRecordedEffects()
                    pygame.quit()
                    sys.exit()

            if currentState == PLAYING:
                if event.key == pygame.K_d: judgeHit(0)
                if event.key == pygame.K_f: judgeHit(1)
                if event.key == pygame.K_j: judgeHit(2)
                if event.key == pygame.K_k: judgeHit(3)
                if event.key == pygame.K_SPACE:
                    if flowerCount > 0 and flowerAutoTime <= 0:
                        flowerCount    -= 1
                        flowerAutoTime  = FLOWER_DURATION

        if event.type == pygame.MOUSEBUTTONDOWN:
            if currentState == MENU:
                if btnStart.isClicked(mousePos):
                    currentState = SETTINGS
                    startLoadingVideo()
                if btnSettings.isClicked(mousePos):
                    currentState = SETTINGS
                    startLoadingVideo()

            elif currentState == SETTINGS:
                if toggleAutoPlay.handleClick(mousePos): isAutoPlay   = toggleAutoPlay.state
                if toggleHP.handleClick(mousePos):       isInvincible = toggleHP.state
                if toggleChart.handleClick(mousePos):    isHardChart  = toggleChart.state
                if toggleEffects.handleClick(mousePos):  effectsOn    = toggleEffects.state

                if btnBack.isClicked(mousePos):
                    stopMusic()
                    currentState = MENU

                if btnStartGame.isClicked(mousePos):
                    resetGame()
                    loadChart()
                    loadEffects()
                    loadMusic()
                    startLoadingVideo()
                    playMusic()
                    gameRunning  = True
                    currentState = PLAYING

            elif currentState == PAUSED:
                if btnResume.isClicked(mousePos):
                    resumeMusic()
                    musicStartTime   = time.time() - pausedVideoTime
                    pausedVideoFrame = None
                    currentState     = PLAYING
                if btnPauseRestart.isClicked(mousePos):
                    pausedVideoFrame = None
                    pausedVideoTime  = 0
                    stopMusic()
                    resetGame(); loadChart(); loadEffects(); loadMusic()
                    playMusic()
                    gameRunning  = True
                    currentState = PLAYING
                if btnPauseMenu.isClicked(mousePos):
                    pausedVideoFrame = None
                    pausedVideoTime  = 0
                    stopMusic()
                    saveRecordedEffects()
                    gameRunning  = False
                    currentState = MENU

            elif currentState == RESULT:
                if btnResultRestart.isClicked(mousePos):
                    stopMusic()
                    resetGame(); loadChart(); loadEffects(); loadMusic()
                    playMusic()
                    gameRunning  = True
                    currentState = PLAYING
                if btnResultMenu.isClicked(mousePos):
                    stopMusic()
                    saveRecordedEffects()
                    gameRunning  = False
                    currentState = MENU

    # ── per-state update + draw ─────────────────────────────────────────

    if currentState == MENU:
        btnStart.updateHover(mousePos)
        btnSettings.updateHover(mousePos)
        drawMenu()

    elif currentState == SETTINGS:
        btnBack.updateHover(mousePos)
        btnStartGame.updateHover(mousePos)
        drawSettings()

    elif currentState == PLAYING:
        if gameRunning and musicStartTime > 0:
            elapsed = time.time() - musicStartTime

            if not gameStartLogged:
                gameStartLogged = True
                recalcSpawnTimes()

            # spawn / move notes, check for misses
            for note in allNotes[:]:
                if note["spawnTime"] <= elapsed and not note["spawned"]:
                    note["spawned"] = True
                if note["spawned"]:
                    note["y"] = getNoteY(note["spawnTime"], elapsed)

                nyScreen    = theTrackY + note["y"]
                distToJudge = getJudgeY() - nyScreen
                timeToJudge = (-distToJudge if isFlipped else distToJudge) / noteSpeed if noteSpeed > 0 else float('inf')

                # auto-hit
                if (isAutoPlay or flowerAutoTime > 0) and abs(timeToJudge) <= PERFECT_WINDOW:
                    judgeHit(note["lane"], isAuto=True)
                    continue

                # miss
                if timeToJudge < -GOOD_WINDOW:
                    lastResult = "Miss"
                    myCombo    = 0
                    lane       = note["lane"]
                    if not isInvincible:
                        dmg = 100 if note["type"] == GLITCHED_NOTE else 20
                        playerHP = max(0, playerHP - dmg)
                        laneGlow[lane]["color"] = HIT_COLOR_GLITCHED if note["type"] == GLITCHED_NOTE else HIT_COLOR_MISS
                    else:
                        laneGlow[lane]["color"] = HIT_COLOR_MISS
                    missHits        += 1
                    totalNotes      += 1
                    laneGlow[lane]["time"] = 0.3
                    notesByLane[lane].remove(note)
                    allNotes.remove(note)

            # death check
            if not isInvincible and playerHP <= 0:
                stopMusic()
                saveRecordedEffects()
                trackLost    = True
                currentState = RESULT

            # effects / warnings
            if effectsOn:
                while warningQueue and warningQueue[0][0] <= elapsed:
                    _, wtyp = warningQueue.pop(0)
                    warningTimer      = WARNING_DURATION
                    currentWarningType = wtyp
                while effectQueue and effectQueue[0][0] <= elapsed:
                    _, typ = effectQueue.pop(0)
                    applyEffect(typ)
            else:
                while warningQueue and warningQueue[0][0] <= elapsed:
                    warningQueue.pop(0)
                while effectQueue and effectQueue[0][0] <= elapsed:
                    effectQueue.pop(0)

        # all notes cleared — wait 3 sec then show result
        if not allNotes and gameRunning and musicStartTime > 0:
            if not hasattr(drawGame, "clearTime"):
                drawGame.clearTime = time.time()
            elif time.time() - drawGame.clearTime >= 3.0:
                saveRecordedEffects()
                del drawGame.clearTime
                currentState = RESULT

        # slide track horizontally
        if theTrackX != targetTrackX:
            diff  = targetTrackX - theTrackX
            step  = TRACK_SLIDE_SPD * dt
            if abs(diff) <= step:
                moveTrackTo(targetTrackX)
            else:
                moveTrackTo(theTrackX + step * (1 if diff > 0 else -1))

        if warningTimer > 0:
            warningTimer = max(0.0, warningTimer - dt)
        if flowerAutoTime > 0:
            flowerAutoTime = max(0.0, flowerAutoTime - dt)

        drawGame()

    elif currentState == PAUSED:
        btnResume.updateHover(mousePos)
        btnPauseRestart.updateHover(mousePos)
        btnPauseMenu.updateHover(mousePos)
        drawPause()

    elif currentState == RESULT:
        btnResultRestart.updateHover(mousePos)
        btnResultMenu.updateHover(mousePos)
        drawResult()

    pygame.display.flip()