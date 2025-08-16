import os, tempfile, math
import numpy as np
import cv2
import mediapipe as mp
from moviepy.editor import VideoFileClip
import librosa

mp_pose = mp.solutions.pose

def _extract_audio_to_wav(video_path, sr=22050):
    # Extract audio as wav into temp file using moviepy
    tmp_wav = tempfile.mktemp(suffix=".wav")
    clip = VideoFileClip(video_path)
    if clip.audio is None:
        raise ValueError("No audio track found in video.")
    clip.audio.write_audiofile(tmp_wav, fps=sr, verbose=False, logger=None)
    clip.close()
    return tmp_wav

def _get_audio_onsets(wav_path, sr=22050):
    y, sr = librosa.load(wav_path, sr=sr, mono=True)
    # Onset detection (simple energy-based)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True, units='frames')
    onsets_sec = librosa.frames_to_time(onset_frames, sr=sr).tolist()
    return onsets_sec

def _get_motion_peaks(video_path, sample_stride=2):
    # Returns list of (t_sec, height_norm) where height_norm is normalized wrist vertical amplitude
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)
    t = 0
    heights = []
    times = []
    left_wrist_y = []
    right_wrist_y = []
    shoulder_span = []

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        if frame_idx % sample_stride != 0:
            frame_idx += 1
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = pose.process(rgb)
        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark
            # y coordinates are normalized [0,1] from top (0) to bottom (1)
            lw = lm[mp_pose.PoseLandmark.LEFT_WRIST.value].y
            rw = lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y
            ls = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x
            rs = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x
            span = abs(rs - ls) + 1e-6
            left_wrist_y.append(lw)
            right_wrist_y.append(rw)
            shoulder_span.append(span)
            times.append(frame_idx / fps)
        frame_idx += 1

    cap.release()
    pose.close()

    if len(times) < 5:
        return []

    # Choose the more active hand (larger variance)
    lw = np.array(left_wrist_y)
    rw = np.array(right_wrist_y)
    active = lw if np.nanstd(lw) > np.nanstd(rw) else rw

    # Smooth
    active_smooth = _smooth(active, win=7)
    # Compute velocity (negative peaks ~ downstrokes if camera is vertical; we use peaks of -velocity)
    vel = np.gradient(active_smooth)
    # Find peaks in -vel (downward speed)
    peaks_idx = _find_peaks(-vel, thresh=np.percentile(-vel, 80))
    times_np = np.array(times)
    span_np = np.array(shoulder_span)
    # Estimate stroke amplitude around each peak as local range in a window
    peaks = []
    for idx in peaks_idx:
        t0 = times_np[idx]
        w0, w1 = max(0, idx-5), min(len(active_smooth)-1, idx+5)
        local = active_smooth[w0:w1]
        if len(local) < 3:
            continue
        amp = float(np.max(local) - np.min(local))
        # normalize by shoulder span median (proxy for scale)
        norm = float(amp / (np.median(span_np[w0:w1]) + 1e-6))
        peaks.append((t0, norm))

    return peaks

def _smooth(x, win=5):
    if len(x) < win: return x
    k = np.ones(win) / win
    return np.convolve(x, k, mode='same')

def _find_peaks(x, thresh):
    # simple peak detection
    idxs = []
    for i in range(1, len(x)-1):
        if x[i] > x[i-1] and x[i] > x[i+1] and x[i] >= thresh:
            idxs.append(i)
    return idxs

def analyze_video(video_path: str):
    # 1) audio onsets
    wav = _extract_audio_to_wav(video_path)
    onsets = _get_audio_onsets(wav)
    try:
        os.remove(wav)
    except Exception:
        pass

    # 2) motion peaks
    peaks = _get_motion_peaks(video_path)

    # 3) align: for each audio onset, find nearest motion peak
    per_hit = []
    j = 0
    for onset in onsets:
        # find nearest peak time
        best = None
        while j < len(peaks) and peaks[j][0] < onset:
            j += 1
        cand = []
        if j < len(peaks): cand.append(peaks[j])
        if j > 0: cand.append(peaks[j-1])
        if not cand: continue
        cand_sorted = sorted(cand, key=lambda p: abs(p[0]-onset))
        t_peak, h_norm = cand_sorted[0]
        offset_ms = (t_peak - onset) * 1000.0
        per_hit.append({
            "audio_onset_s": float(onset),
            "motion_peak_s": float(t_peak),
            "offset_ms": float(offset_ms),
            "height_norm": float(h_norm)
        })

    # 4) summary metrics
    if per_hit:
        offsets = np.array([h["offset_ms"] for h in per_hit])
        heights = np.array([h["height_norm"] for h in per_hit])
        summary = {
            "avg_offset_ms": float(np.mean(offsets)),
            "offset_std_ms": float(np.std(offsets)),
            "median_height_norm": float(np.median(heights)),
            "height_consistency": float(np.std(heights)),
            "num_hits": int(len(per_hit))
        }
    else:
        summary = {
            "avg_offset_ms": None,
            "offset_std_ms": None,
            "median_height_norm": None,
            "height_consistency": None,
            "num_hits": 0
        }

    return {"per_hit": per_hit, "summary": summary}
