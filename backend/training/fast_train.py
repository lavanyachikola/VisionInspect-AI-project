"""
Fast CNN training - preloads all images into memory
Takes 5-10 minutes instead of 60.
"""
import os, json, time, numpy as np, tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from tensorflow.keras.optimizers import Adam

# Config
IMG_SIZE = 224
BATCH_SIZE = 16
EPOCHS = 5
MAX_PER_FOLDER = 15  # 15 images per folder = ~30 seconds of loading

CLASSES = ["good", "Crack", "Dent", "Contamination", "Scratch", "Surface Defect"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

MVTEC_MAP = {
    "bottle": {"good": "good", "broken_large": "Crack", "broken_small": "Crack", "contamination": "Contamination"},
    "cable": {"good": "good", "bent_wire": "Dent", "cut_inner_insulation": "Scratch", "cut_outer_insulation": "Scratch"},
    "capsule": {"good": "good", "crack": "Crack", "scratch": "Scratch", "faulty_imprint": "Surface Defect"},
    "carpet": {"good": "good", "hole": "Crack", "cut": "Scratch", "color": "Contamination"},
    "grid": {"good": "good", "broken": "Crack", "glue": "Contamination"},
    "leather": {"good": "good", "cut": "Scratch", "fold": "Dent", "glue": "Contamination"},
    "metal_nut": {"good": "good", "scratch": "Scratch", "bent": "Dent", "flip": "Surface Defect"},
    "pill": {"good": "good", "crack": "Crack", "contamination": "Contamination", "scratch": "Scratch"},
    "screw": {"good": "good", "scratch_head": "Scratch", "scratch_neck": "Scratch"},
    "tile": {"good": "good", "crack": "Crack", "oil": "Contamination", "rough": "Surface Defect"},
    "wood": {"good": "good", "hole": "Crack", "scratch": "Scratch"},
    "zipper": {"good": "good", "broken_teeth": "Crack", "rough": "Surface Defect"},
}


def collect():
    data = []
    for cat, submap in MVTEC_MAP.items():
        for folder, cls in submap.items():
            if folder == "good":
                path = f"../dataset/{cat}/train/good"
            else:
                path = f"../dataset/{cat}/test/{folder}"
            if not os.path.exists(path):
                continue
            files = [f for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg'))][:MAX_PER_FOLDER]
            for f in files:
                data.append((os.path.join(path, f), cls))
    return data


print("=" * 60)
print("VisionInspect AI — FAST CNN Training")
print("=" * 60)

print("\n[1/4] Collecting dataset...")
data = collect()
print(f"  Total: {len(data)} images")

print("\n[2/4] Preloading into memory (this takes 1-2 minutes)...")
X = []
y = []
start = time.time()
for i, (path, cls) in enumerate(data):
    try:
        img = load_img(path, target_size=(IMG_SIZE, IMG_SIZE))
        arr = img_to_array(img) / 255.0
        X.append(arr)
        y.append(tf.keras.utils.to_categorical(CLASS_TO_IDX[cls], len(CLASSES)))
    except:
        continue
    if (i + 1) % 50 == 0:
        print(f"  Loaded {i+1}/{len(data)} ({time.time()-start:.0f}s)")

X = np.array(X, dtype=np.float32)
y = np.array(y, dtype=np.float32)
print(f"  ✅ Loaded {len(X)} images in {time.time()-start:.0f}s")

# Split
np.random.seed(42)
idx = np.random.permutation(len(X))
X, y = X[idx], y[idx]
split = int(len(X) * 0.85)
X_train, y_train = X[:split], y[:split]
X_val, y_val = X[split:], y[split:]
print(f"  Train: {len(X_train)}, Val: {len(X_val)}")

print("\n[3/4] Building model...")
base = MobileNetV2(input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights='imagenet')
base.trainable = False
x = GlobalAveragePooling2D()(base.output)
x = Dense(128, activation='relu')(x)
x = Dropout(0.3)(x)
out = Dense(len(CLASSES), activation='softmax')(x)
model = Model(base.input, out)
model.compile(optimizer=Adam(1e-3), loss='categorical_crossentropy', metrics=['accuracy'])
print(f"  Params: {model.count_params():,}")

print("\n[4/4] Training...")
os.makedirs("training/models", exist_ok=True)
model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    verbose=1
)

model.save("training/models/defect_model.h5")
with open("training/models/classes.json", "w") as f:
    json.dump(CLASSES, f)

print(f"\n✅ Model saved!")
print(f"   Path: training/models/defect_model.h5")
print(f"   Size: {os.path.getsize('training/models/defect_model.h5')/(1024*1024):.1f} MB")
print(f"   Classes: {len(CLASSES)}")
