import os
import cv2
import numpy as np
import glob

def remove_background(input_dir, output_dir):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all jpg images in input directory
    image_paths = sorted(glob.glob(os.path.join(input_dir, "*.jpg")))
    
    if not image_paths:
        print(f"No images found in {input_dir}")
        return
        
    print(f"Found {len(image_paths)} images. Processing background removal...")
    
    for idx, img_path in enumerate(image_paths):
        # Load image
        img = cv2.imread(img_path)
        if img is None:
            print(f"Error loading {img_path}")
            continue
            
        # Convert BGR to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Define range of green color in HSV
        # Green Hue is typically around 60 (30 to 90 range in OpenCV's 0-180 scale)
        lower_green = np.array([35, 30, 30])
        upper_green = np.array([85, 255, 255])
        
        # Threshold the HSV image to get only green colors
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Invert the mask to get non-green parts (the flower)
        mask_inv = cv2.bitwise_not(mask)
        
        # Perform some morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_inv = cv2.morphologyEx(mask_inv, cv2.MORPH_CLOSE, kernel)
        mask_inv = cv2.morphologyEx(mask_inv, cv2.MORPH_OPEN, kernel)
        
        # Smooth the mask edges slightly
        mask_inv = cv2.GaussianBlur(mask_inv, (3, 3), 0)
        
        # Split channels and add Alpha channel
        b, g, r = cv2.split(img)
        rgba = [b, g, r, mask_inv]
        dst = cv2.merge(rgba, 4)
        
        # Save as PNG to support transparency
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        out_path = os.path.join(output_dir, f"{base_name}.png")
        cv2.imwrite(out_path, dst)
        
    print(f"Completed! Processed images are saved in {output_dir}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, "kare")
    output_folder = os.path.join(script_dir, "kare_bg")
    remove_background(input_folder, output_folder)
