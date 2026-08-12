import os
import cv2
import numpy as np

def extract_frames(video_path, output_dir, target_count=150, duration_sec=5):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return
    
    # Get total frames and fps
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate frames in first 5 seconds
    frames_in_5_sec = int(fps * duration_sec)
    # Clip to total frames if the video is shorter than 5 seconds
    frames_to_consider = min(frames_in_5_sec, total_frames)
    
    # Generate 100 evenly spaced frame indices
    frame_indices = np.linspace(0, frames_to_consider - 1, target_count, dtype=int)
    
    print(f"FPS: {fps}, Total Frames: {total_frames}")
    print(f"Extracting {target_count} frames from the first {duration_sec} seconds...")
    
    saved_count = 0
    for idx, frame_idx in enumerate(frame_indices):
        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            print(f"Warning: Could not read frame at index {frame_idx}")
            continue
        
        # Save frame
        out_path = os.path.join(output_dir, f"kare_{idx+1:03d}.jpg")
        cv2.imwrite(out_path, frame)
        saved_count += 1
        
    cap.release()
    print(f"Completed! Saved {saved_count} frames to {output_dir}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_file = os.path.join(script_dir, "growing_flower.mp4")
    output_folder = os.path.join(script_dir, "kare")
    extract_frames(video_file, output_folder)
