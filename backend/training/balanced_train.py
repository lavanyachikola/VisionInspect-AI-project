"""
Balanced CNN training - fixes class imbalance.
"""
import os, json, time, numpy as np, tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping

IMG_SIZE = 224
BATCH_SIZE = 16
EPOCHS = 10
SAMPLES_PER_CLASS = 250

CLASSES = ["good", "Crack", "Dent", "Contamination", "Scratch", "Surface Defect"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

MVTEC_MAP = {
    "bottle": {"good": "good", "broken_large": "Crack", "broken_small": "Crack", "contamination": "Contamination"},
    "cable": {"good": "good", "bent_wire": "Dent", "cut_inner_insulation": "Scratch", "cut_outer_insulation": "Scratch",
              "missing_cable": "Surface Defect", "missing_wire": "Surface Defect", "poke_insulation": "Dent"},
    "capsule": {"good": "good", "crack": "Crack", "faulty_imprint": "Surface Defect", "poke": "Dent",
                "scratch": "Scratch", "squeeze": "Dent"},
    "carpet": {"good": "good", "color": "Contamination", "cut": "Scratch", "hole": "Crack",
               "metal_contamination": "Contamination", "thread": "Surface Defect"},
    "grid": {"good": "good", "broken": "Crack", "glue": "Contamination",
             "metal_contamination": "Contamination", "thread": "Surface Defect"},
    "hazelnut": {"good": "good", "crack": "Crack", "cut": "Scratch", "hole": "Crack", "print": "Surface Defect"},
    "leather": {"good": "good", "color": "Contamination", "cut": "Scratch", "fold": "Dent",
                "glue": "Contamination", "poke": "Dent"},
    "metal_nut": {"good": "good", "bent": "Dent", "color": "Contamination", "flip": "Surface Defect",
                  "scratch": "Scratch"},
    "pill": {"good": "good", "color": "Contamination", "combined": "Surface Defect",
             "contamination": "Contamination", "crack": "Crack", "faulty_imprint": "Surface Defect",
             "pill_type": "Surface Defect", "scratch": "Scratch"},
    "screw": {"good": "good", "manipulated_front": "Dent", "scratch_head": "Scratch",
              "scratch_neck": "Scratch", "thread_side": "Surface Defect", "thread_top": "Surface Defect"},
    "tile": {"good": "good", "crack": "Crack", "glue_strip": "Contamination", "gray_stroke": "Contamination",
             "oil": "Contamination", "rough": "Surface Defect"},
    "toothbrush": {"good": "good", "defective": "Surface Defect"},
    "transistor": {"good": "good", "bent_lead": "Dent", "cut_lead": "Crack", "damaged_case": "Crack",
                   "misplaced": "Surface Defect"},
    "wood": {"good": "good", "color": "Contamination", "combined": "Surface Defect", "hole": "Crack",
             "liquid": "Contamination", "scratch": "Scratch"},
    "zipper": {"good": "good", "broken_teeth": "Crack", "fabric_border": "Surface Defect",
               "fabric_interior": "Surface Defect", "rough": "Surface Defect", "split_teeth": "Crack",
               "squeezed_teeth": "Dent"}
}


def collect_balanced():
    by_class = {c: [] for c in CLASSES}
    
    for cat, submap in MVTEC_MAP.items():
        for folder, cls in submap.items():
            paths = []
            if folder == "good":
                paths.append(f"../dataset/{cat}/train/good")
                paths.append(f"../dataset/{cat}/test/good")
            else:
                paths.append(f"../dataset/{cat}/test/{folder}")
            
            for path in paths:
                if not os.path.exists(path):
                    continue
                files = [f for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg'))]
                for f in files:
                    by_class[cls].append(os.path.join(path, f))
    
    data = []
    print("\nClass counts (before balancing):")
    for cls in CLASSES:
        print(f"  {cls}: {len(by_class[cls])}")
    
    print(f"\nLimiting to {SAMPLES_PER_CLASS} per class...")
    for cls in CLASSES:
        np.random.shuffle(by_class[cls])
        selected = by_class[cls][:SAMPLES_PER_CLASS]
        for path in selected:
            data.append((path, cls))
    
    print(f"Total balanced: {len(data)}")
    return data


print("=" * 60)
print("VisionInspect AI — Balanced CNN Training")
print("=" * 60)

print("\n[1/4] Collecting balanced dataset...")
np.random.seed(42)
data = collect_balanced()

print("\n[2/4] Preloading images (1-2 min)...")
X, y = [], []
start = time.time()
for i, (path, cls) in enumerate(data):
    try:
        img = load_img(path, target_size=(IMG_SIZE, IMG_SIZE))
        arr = img_to_array(img) / 255.0
        X.append(arr)
        y.append(tf.keras.utils.to_categorical(CLASS_TO_IDX[cls], len(CLASSES)))
    except:
        continue
    if (i + 1) % 200 == 0:
        print(f"  Loaded {i+1}/{len(data)} ({time.time()-start:.0f}s)")

X = np.array(X, dtype=np.float32)
y = np.array(y, dtype=np.float32)
print(f"  ✅ Loaded {len(X)} images")

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
x = Dense(256, activation='relu')(x)
x = Dropout(0.4)(x)
x = Dense(128, activation='relu')(x)
x = Dropout(0.3)(x)
out = Dense(len(CLASSES), activation='softmax')(x)
model = Model(base.input, out)
model.compile(optimizer=Adam(5e-4), loss='categorical_crossentropy', metrics=['accuracy'])

print("\n[4/4] Training...")
os.makedirs("training/models", exist_ok=True)

callbacks = [EarlyStopping(patience=3, restore_best_weights=True, monitor='val_accuracy')]

history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    callbacks=callbacks,
    verbose=1
)

model.save("training/models/defect_model.h5")
with open("training/models/classes.json", "w") as f:
    json.dump(CLASSES, f)

print(f"\n✅ Model saved!")
print(f"   Final val_accuracy: {max(history.history['val_accuracy']):.4f}")
print(f"   Size: {os.path.getsize('training/models/defect_model.h5')/(1024*1024):.1f} MB")
