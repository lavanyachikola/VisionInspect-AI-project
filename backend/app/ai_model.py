"""
VisionInspect AI - Defect Detection Model
Loads trained CNN if available, otherwise falls back to feature-based detection.
"""

import cv2
import numpy as np
import os
import json
import time
from datetime import datetime

# Try to import TensorFlow (for trained model)
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️  TensorFlow not installed. Using feature-based fallback.")

MODEL_INFO = {
    "name": "VisionInspect CNN v2.0",
    "version": "2.0",
    "input_size": "224x224",
    "confidence_threshold": 0.55,
    "classes": ["Crack", "Dent", "Contamination", "Scratch", "Surface Defect"]
}

_trained_model = None
_classes = None
_model_load_attempted = False


def load_trained_model():
    """Load trained CNN model"""
    global _trained_model, _classes, _model_load_attempted
    
    if _model_load_attempted:
        return _trained_model, _classes
    
    _model_load_attempted = True
    
    if not TF_AVAILABLE:
        print("⚠️  TensorFlow not available")
        return None, None
    
    # Get absolute path
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base_dir, "training", "models", "defect_model.h5")
    classes_path = os.path.join(base_dir, "training", "models", "classes.json")
    
    print(f"🔍 Looking for model at: {model_path}")
    print(f"   File exists: {os.path.exists(model_path)}")
    
    if not os.path.exists(model_path):
        print(f"⚠️  No trained model at {model_path}")
        return None, None
    
    try:
        print("📦 Loading TensorFlow model...")
        _trained_model = tf.keras.models.load_model(model_path)
        with open(classes_path, 'r') as f:
            _classes = json.load(f)
        print(f"✅ Loaded trained model: {len(_classes)} classes")
        print(f"   Classes: {_classes}")
        return _trained_model, _classes
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def extract_features(image_path: str) -> dict:
    """Fallback feature extraction"""
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    height, width = img.shape[:2]
    img = cv2.resize(img, (640, 640))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    margin = int(640 * 0.15)
    gray = gray[margin:640-margin, margin:640-margin]
    img = img[margin:640-margin, margin:640-margin]
    h, w = gray.shape
    
    gray_blur = cv2.GaussianBlur(gray, (3, 3), 0)
    laplacian = cv2.Laplacian(gray_blur, cv2.CV_64F)
    edges = cv2.Canny(gray_blur, 50, 150)
    
    grid_size = 8
    cell_h, cell_w = h // grid_size, w // grid_size
    
    cell_variances = []
    cell_edge_densities = []
    cell_laplacian_vars = []
    
    for i in range(grid_size):
        for j in range(grid_size):
            y1, y2 = i*cell_h, (i+1)*cell_h
            x1, x2 = j*cell_w, (j+1)*cell_w
            cell = gray_blur[y1:y2, x1:x2]
            cell_lap = laplacian[y1:y2, x1:x2]
            cell_edges = edges[y1:y2, x1:x2]
            cell_variances.append(float(np.var(cell)))
            cell_laplacian_vars.append(float(np.var(cell_lap)))
            cell_edge_densities.append(float(np.sum(cell_edges > 0) / (cell_h * cell_w)))
    
    cell_variances = np.array(cell_variances)
    cell_edge_densities = np.array(cell_edge_densities)
    cell_laplacian_vars = np.array(cell_laplacian_vars)
    
    return {
        "edge_ratio": float(np.max(cell_edge_densities) / (np.mean(cell_edge_densities) + 0.001)),
        "lap_ratio": float(np.max(cell_laplacian_vars) / (np.mean(cell_laplacian_vars) + 1)),
        "max_lap_var": float(np.max(cell_laplacian_vars)),
        "cell_var_cv": float(np.std(cell_variances) / (np.mean(cell_variances) + 1)),
        "width": width, "height": height,
    }


def classify_defect(features: dict) -> dict:
    """Strict fallback classifier for cloud deployment"""
    scores = {}
    edge_ratio = features.get("edge_ratio", 0)
    lap_ratio = features.get("lap_ratio", 0)
    cell_var_cv = features.get("cell_var_cv", 0)
    max_lap = features.get("max_lap_var", 0)
    
    # Much lower thresholds to catch defects
    if edge_ratio > 6:
        scores["Crack"] = min(1.0, 0.6 + (edge_ratio - 6) / 10)
    if lap_ratio > 12:
        scores["Scratch"] = min(1.0, 0.6 + (lap_ratio - 12) / 20)
    if cell_var_cv > 2.5:
        scores["Dent"] = min(1.0, 0.6 + (cell_var_cv - 2.5) / 2)
    if max_lap > 250:
        scores["Surface Defect"] = min(1.0, 0.6 + (max_lap - 250) / 500)
    
    # If nothing is detected, but features are slightly abnormal, flag it
    if not scores and (edge_ratio > 4 or lap_ratio > 8):
        scores["Surface Defect"] = 0.65
        
    return {k: round(v, 2) for k, v in scores.items() if v >= 0.60}


def predict_with_cnn(image_path: str):
    """Predict using trained CNN"""
    model, classes = load_trained_model()
    if model is None:
        return None
    
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        img = cv2.resize(img, (224, 224))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_array = img.astype(np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        input_details = model.get_input_details()
        output_details = model.get_output_details()
        model.set_tensor(input_details[0]['index'], img_array)
        model.invoke()
        predictions = model.get_tensor(output_details[0]['index'])[0]
        
        top_idx = int(np.argmax(predictions))
        top_class = classes[top_idx]
        confidence = float(predictions[top_idx])
        
        all_scores = {}
        for idx, cls in enumerate(classes):
            if cls != "good" and predictions[idx] >= 0.15:
                all_scores[cls] = float(predictions[idx])
        
        return {
            "predicted_class": top_class,
            "confidence": confidence,
            "all_scores": all_scores,
        }
    except Exception as e:
        print(f"CNN prediction error: {e}")
        return None


def find_defect_region(image_path: str, defect_type: str) -> dict:
    img = cv2.imread(image_path)
    if img is None:
        return None
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    mask = cv2.Canny(gray, 100, 200)
    mask = cv2.dilate(mask, np.ones((7, 7), np.uint8), iterations=3)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        if w < 10 or h < 10:
            w, h = max(20, w), max(20, h)
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = min(w, width - x)
        h = min(h, height - y)
        return {"x": int(x), "y": int(y), "width": int(w), "height": int(h),
                "center_x": int(x + w/2), "center_y": int(y + h/2)}
    
    return {"x": int(width * 0.3), "y": int(height * 0.3),
            "width": int(width * 0.4), "height": int(height * 0.4),
            "center_x": int(width * 0.5), "center_y": int(height * 0.5)}


def calculate_severity(defect_type: str, confidence: float, location: dict, total_pixels: int) -> float:
    defect_area = location["width"] * location["height"]
    size_score = min(1.0, defect_area / (total_pixels * 0.15)) * 100
    location_score = 75
    type_scores = {"Crack": 95, "Contamination": 85, "Dent": 75, "Surface Defect": 65, "Scratch": 55}
    type_score = type_scores.get(defect_type, 60)
    confidence_score = confidence * 100
    severity = (size_score * 0.30 + location_score * 0.25 +
                type_score * 0.25 + confidence_score * 0.20)
    return round(min(100, max(0, severity)), 2)


def get_severity_level(score: float) -> str:
    if score >= 80: return "Critical"
    elif score >= 60: return "High"
    elif score >= 40: return "Medium"
    return "Low"


def get_recommendation(severity_level: str, defect_detected: bool) -> str:
    if not defect_detected:
        return "Product meets quality standards."
    recs = {
        "Critical": "Reject product immediately. Trigger quality inspection.",
        "High": "Repair/Rework the product. Re-inspect after rework.",
        "Medium": "Manual inspection required. Consider rework.",
        "Low": "Minor defect. Monitor quality trend."
    }
    return recs.get(severity_level, "Manual inspection required.")


def draw_defect_result(image_path: str, defect: dict, output_path: str, severity_level: str) -> str:
    img = cv2.imread(image_path)
    if img is None:
        return None
    loc = defect["location"]
    x, y, w, h = loc["x"], loc["y"], loc["width"], loc["height"]
    colors = {"Critical": (0, 0, 255), "High": (0, 100, 255),
              "Medium": (0, 200, 255), "Low": (0, 255, 200)}
    color = colors.get(severity_level, (0, 0, 255))
    cv2.rectangle(img, (x, y), (x + w, y + h), color, 4)
    label = f"{defect['type']}: {int(defect['confidence'] * 100)}%"
    (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    cv2.rectangle(img, (x, y - 35), (x + lw + 15, y), color, -1)
    cv2.putText(img, label, (x + 5, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.imwrite(output_path, img)
    return output_path


def detect_defects(image_path: str, product_code: str = "") -> dict:
    """Main detection — tries CNN first"""
    start_time = time.time()
    
    cnn_result = predict_with_cnn(image_path)
    
    if cnn_result is not None:
        preprocessing_time = (time.time() - start_time) * 1000
        
        predicted_class = cnn_result["predicted_class"]
        confidence = cnn_result["confidence"]
        
        if predicted_class == "good" and confidence >= 0.50:
            total_time = (time.time() - start_time) * 1000
            return {
                "success": True, "defect_detected": False, "defect_type": None,
                "confidence": round(confidence, 2), "all_defects": [], "location": None,
                "severity_score": 0, "severity_level": "None", "decision": "PASSED",
                "recommendation": get_recommendation("None", False),
                "detection_time": datetime.now().isoformat(),
                "timing": {"preprocessing_ms": round(preprocessing_time, 2),
                          "inference_ms": 0, "total_ms": round(total_time, 2)},
                "model_info": MODEL_INFO, "method": "CNN"
            }
        
        if confidence >= MODEL_INFO["confidence_threshold"]:
            location = find_defect_region(image_path, predicted_class)
            img = cv2.imread(image_path)
            total_pixels = img.shape[0] * img.shape[1] if img is not None else 1
            severity = calculate_severity(predicted_class, confidence, location, total_pixels)
            severity_level = get_severity_level(severity)
            
            all_defects = [{"type": k, "confidence": round(v, 2),
                          "location": find_defect_region(image_path, k)}
                         for k, v in cnn_result["all_scores"].items() if v >= 0.15]
            
            total_time = (time.time() - start_time) * 1000
            return {
                "success": True, "defect_detected": True,
                "defect_type": predicted_class,
                "confidence": round(confidence, 2),
                "all_defects": all_defects, "location": location,
                "severity_score": severity, "severity_level": severity_level,
                "decision": "FAILED",
                "recommendation": get_recommendation(severity_level, True),
                "detection_time": datetime.now().isoformat(),
                "timing": {"preprocessing_ms": round(preprocessing_time, 2),
                          "inference_ms": 0, "total_ms": round(total_time, 2)},
                "model_info": MODEL_INFO, "method": "CNN"
            }
    
    # Fallback
    features = extract_features(image_path)
    if features is None:
        return {"success": False, "error": "Could not process image"}
    
    preprocessing_time = (time.time() - start_time) * 1000
    inference_start = time.time()
    defect_scores = classify_defect(features)
    inference_time = (time.time() - inference_start) * 1000
    
    if len(defect_scores) > 0:
        primary_type = max(defect_scores, key=defect_scores.get)
        primary_confidence = min(0.98, defect_scores[primary_type])
        
        if primary_confidence >= MODEL_INFO["confidence_threshold"]:
            location = find_defect_region(image_path, primary_type)
            total_pixels = features["width"] * features["height"]
            severity = calculate_severity(primary_type, primary_confidence, location, total_pixels)
            severity_level = get_severity_level(severity)
            
            all_defects = [{"type": k, "confidence": round(min(0.98, v), 2),
                          "location": find_defect_region(image_path, k)}
                         for k, v in defect_scores.items() if v >= MODEL_INFO["confidence_threshold"]]
            
            total_time = (time.time() - start_time) * 1000
            return {
                "success": True, "defect_detected": True,
                "defect_type": primary_type, "confidence": round(primary_confidence, 2),
                "all_defects": all_defects, "location": location,
                "severity_score": severity, "severity_level": severity_level,
                "decision": "FAILED",
                "recommendation": get_recommendation(severity_level, True),
                "detection_time": datetime.now().isoformat(),
                "timing": {"preprocessing_ms": round(preprocessing_time, 2),
                          "inference_ms": round(inference_time, 2),
                          "total_ms": round(total_time, 2)},
                "model_info": MODEL_INFO, "features": features,
                "method": "feature-based"
            }
    
    total_time = (time.time() - start_time) * 1000
    return {
        "success": True, "defect_detected": False, "defect_type": None,
        "confidence": 0, "all_defects": [], "location": None,
        "severity_score": 0, "severity_level": "None", "decision": "PASSED",
        "recommendation": get_recommendation("None", False),
        "detection_time": datetime.now().isoformat(),
        "timing": {"preprocessing_ms": round(preprocessing_time, 2),
                  "inference_ms": round(inference_time, 2),
                  "total_ms": round(total_time, 2)},
        "model_info": MODEL_INFO, "features": features,
        "method": "feature-based"
    }
