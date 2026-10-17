"""
VisionInspect AI - CNN Training Script
Trains a MobileNetV2-based defect classifier on MVTec AD dataset.

Usage:
    python training/train_model.py
"""

import os
import sys
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

# ==================== CONFIG ====================
IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 30
LEARNING_RATE = 1e-4
DATASET_PATH = "../dataset"
MODEL_SAVE_PATH = "models/defect_model.h5"
CLASSES_FILE = "models/classes.json"

# Defect classes to train on
DEFECT_CLASSES = ["Crack", "Dent", "Contamination", "Scratch", "Surface Defect"]

# MVTec category → our defect class mapping
MVTEC_TO_DEFECT = {
    "bottle": {
        "good": None,
        "broken_large": "Crack",
        "broken_small": "Crack",
        "contamination": "Contamination"
    },
    "cable": {
        "good": None,
        "bent_wire": "Dent",
        "cut_inner_insulation": "Scratch",
        "cut_outer_insulation": "Scratch",
        "missing_cable": "Surface Defect",
        "missing_wire": "Surface Defect",
        "poke_insulation": "Dent"
    },
    "capsule": {
        "good": None,
        "crack": "Crack",
        "faulty_imprint": "Surface Defect",
        "poke": "Dent",
        "scratch": "Scratch",
        "squeeze": "Dent"
    },
    "carpet": {
        "good": None,
        "color": "Contamination",
        "cut": "Scratch",
        "hole": "Crack",
        "metal_contamination": "Contamination",
        "thread": "Surface Defect"
    },
    "grid": {
        "good": None,
        "broken": "Crack",
        "glue": "Contamination",
        "metal_contamination": "Contamination",
        "thread": "Surface Defect"
    },
    "leather": {
        "good": None,
        "color": "Contamination",
        "cut": "Scratch",
        "fold": "Dent",
        "glue": "Contamination",
        "poke": "Dent"
    },
    "metal_nut": {
        "good": None,
        "bent": "Dent",
        "color": "Contamination",
        "flip": "Surface Defect",
        "scratch": "Scratch"
    },
    "pill": {
        "good": None,
        "color": "Contamination",
        "combined": "Surface Defect",
        "contamination": "Contamination",
        "crack": "Crack",
        "faulty_imprint": "Surface Defect",
        "pill_type": "Surface Defect",
        "scratch": "Scratch"
    },
    "screw": {
        "good": None,
        "manipulated_front": "Dent",
        "scratch_head": "Scratch",
        "scratch_neck": "Scratch",
        "thread_side": "Surface Defect",
        "thread_top": "Surface Defect"
    },
    "tile": {
        "good": None,
        "crack": "Crack",
        "glue_strip": "Contamination",
        "gray_stroke": "Contamination",
        "oil": "Contamination",
        "rough": "Surface Defect"
    },
    "toothbrush": {
        "good": None,
        "defective": "Surface Defect"
    },
    "transistor": {
        "good": None,
        "bent_lead": "Dent",
        "cut_lead": "Crack",
        "damaged_case": "Crack",
        "misplaced": "Surface Defect"
    },
    "wood": {
        "good": None,
        "color": "Contamination",
        "combined": "Surface Defect",
        "hole": "Crack",
        "liquid": "Contamination",
        "scratch": "Scratch"
    },
    "zipper": {
        "good": None,
        "broken_teeth": "Crack",
        "fabric_border": "Surface Defect",
        "fabric_interior": "Surface Defect",
        "rough": "Surface Defect",
        "split_teeth": "Crack",
        "squeezed_teeth": "Dent"
    }
}


def build_dataset_index():
    """Build a list of (image_path, class_label) tuples"""
    print("\n[1/6] Building dataset index...")
    
    data = []
    stats = {"good": 0}
    for c in DEFECT_CLASSES:
        stats[c] = 0
    
    for category, subfolders in MVTEC_TO_DEFECT.items():
        category_path = os.path.join(DATASET_PATH, category)
        if not os.path.exists(category_path):
            continue
        
        # Training data is usually in 'train/good'
        train_good = os.path.join(category_path, "train", "good")
        if os.path.exists(train_good):
            for img in os.listdir(train_good):
                if img.lower().endswith(('.png', '.jpg', '.jpeg')):
                    data.append((os.path.join(train_good, img), "good"))
                    stats["good"] += 1
        
        # Test data has defects
        test_path = os.path.join(category_path, "test")
        if os.path.exists(test_path):
            for defect_folder in os.listdir(test_path):
                defect_path = os.path.join(test_path, defect_folder)
                if not os.path.isdir(defect_path):
                    continue
                
                defect_class = subfolders.get(defect_folder)
                if defect_class is None:
                    # It's a "good" test image
                    for img in os.listdir(defect_path):
                        if img.lower().endswith(('.png', '.jpg', '.jpeg')):
                            data.append((os.path.join(defect_path, img), "good"))
                            stats["good"] += 1
                else:
                    for img in os.listdir(defect_path):
                        if img.lower().endswith(('.png', '.jpg', '.jpeg')):
                            data.append((os.path.join(defect_path, img), defect_class))
                            stats[defect_class] += 1
    
    print(f"  Total samples: {len(data)}")
    for cls, count in stats.items():
        print(f"    {cls}: {count}")
    
    return data


def split_dataset(data, train_ratio=0.7, val_ratio=0.15):
    """Split data into train/val/test"""
    np.random.seed(42)
    np.random.shuffle(data)
    
    n = len(data)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    return data[:train_end], data[train_end:val_end], data[val_end:]


def create_dataframe_like(data, base_dir):
    """Create a pandas-like structure for ImageDataGenerator"""
    import pandas as pd
    df = pd.DataFrame(data, columns=['filename', 'class'])
    return df


def build_model(num_classes):
    """Build MobileNetV2-based classifier"""
    print(f"\n[3/6] Building model for {num_classes} classes...")
    
    base_model = MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights='imagenet'
    )
    
    # Freeze base layers initially
    for layer in base_model.layers:
        layer.trainable = False
    
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.5)(x)
    x = Dense(128, activation='relu')(x)
    x = Dropout(0.3)(x)
    outputs = Dense(num_classes, activation='softmax')(x)
    
    model = Model(inputs=base_model.input, outputs=outputs)
    model.compile(
        optimizer=Adam(learning_rate=LEARNING_RATE),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model, base_model


def train():
    """Main training function"""
    
    print("=" * 60)
    print("VisionInspect AI - CNN Training")
    print("=" * 60)
    
    # Step 1: Build dataset
    data = build_dataset_index()
    if len(data) < 100:
        print("\n❌ Not enough data! Need at least 100 images.")
        return
    
    # Step 2: Split
    print("\n[2/6] Splitting dataset...")
    train_data, val_data, test_data = split_dataset(data)
    print(f"  Train: {len(train_data)}")
    print(f"  Val: {len(val_data)}")
    print(f"  Test: {len(test_data)}")
    
    # Create class list
    all_classes = ["good"] + DEFECT_CLASSES
    class_to_idx = {c: i for i, c in enumerate(all_classes)}
    num_classes = len(all_classes)
    
    print(f"  Classes: {all_classes}")
    
    # Save classes
    os.makedirs(os.path.dirname(CLASSES_FILE), exist_ok=True)
    with open(CLASSES_FILE, 'w') as f:
        json.dump(all_classes, f)
    
    # Step 3: Build model
    model, base_model = build_model(num_classes)
    print(f"  Total params: {model.count_params():,}")
    
    # Step 4: Data generators
    print("\n[4/6] Creating data generators...")
    
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.15,
        height_shift_range=0.15,
        horizontal_flip=True,
        zoom_range=0.15,
        brightness_range=[0.8, 1.2],
        fill_mode='nearest'
    )
    
    val_datagen = ImageDataGenerator(rescale=1./255)
    test_datagen = ImageDataGenerator(rescale=1./255)
    
    def make_generator(data_list, datagen, shuffle=True):
        """Custom generator from list"""
        def gen():
            while True:
                if shuffle:
                    np.random.shuffle(data_list)
                for path, cls in data_list:
                    try:
                        from tensorflow.keras.preprocessing.image import load_img, img_to_array
                        img = load_img(path, target_size=(IMG_SIZE, IMG_SIZE))
                        arr = img_to_array(img)
                        arr = datagen.random_transform(arr) if shuffle else arr
                        arr = datagen.standardize(arr)
                        yield arr, tf.keras.utils.to_categorical(class_to_idx[cls], num_classes)
                    except Exception as e:
                        continue
        return gen
    
    train_gen = make_generator(train_data, train_datagen, True)()
    val_gen = make_generator(val_data, val_datagen, False)()
    test_gen = make_generator(test_data, test_datagen, False)()
    
    # Step 5: Train
    print("\n[5/6] Training model...")
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    
    callbacks = [
        EarlyStopping(patience=5, restore_best_weights=True, monitor='val_accuracy'),
        ModelCheckpoint(MODEL_SAVE_PATH, save_best_only=True, monitor='val_accuracy'),
        ReduceLROnPlateau(factor=0.5, patience=3, min_lr=1e-6)
    ]
    
    history = model.fit(
        train_gen,
        steps_per_epoch=len(train_data) // BATCH_SIZE,
        validation_data=val_gen,
        validation_steps=len(val_data) // BATCH_SIZE,
        epochs=EPOCHS,
        callbacks=callbacks,
        verbose=1
    )
    
    # Step 6: Fine-tune (unfreeze last 30 layers)
    print("\n[6/6] Fine-tuning...")
    for layer in base_model.layers[-30:]:
        layer.trainable = True
    
    model.compile(
        optimizer=Adam(learning_rate=LEARNING_RATE / 10),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    history2 = model.fit(
        train_gen,
        steps_per_epoch=len(train_data) // BATCH_SIZE,
        validation_data=val_gen,
        validation_steps=len(val_data) // BATCH_SIZE,
        epochs=10,
        callbacks=callbacks,
        verbose=1
    )
    
    # Save final model
    model.save(MODEL_SAVE_PATH)
    print(f"\n✅ Model saved to: {MODEL_SAVE_PATH}")
    print(f"✅ Classes saved to: {CLASSES_FILE}")
    
    # Evaluate on test set
    print("\n" + "=" * 60)
    print("EVALUATION ON TEST SET")
    print("=" * 60)
    
    test_gen_eval = make_generator(test_data, test_datagen, False)()
    results = model.evaluate(
        test_gen_eval,
        steps=len(test_data) // BATCH_SIZE,
        verbose=0
    )
    print(f"Test Loss: {results[0]:.4f}")
    print(f"Test Accuracy: {results[1]:.4f}")
    
    # Save metrics
    metrics = {
        "test_loss": float(results[0]),
        "test_accuracy": float(results[1]),
        "train_samples": len(train_data),
        "val_samples": len(val_data),
        "test_samples": len(test_data),
        "num_classes": num_classes,
        "classes": all_classes
    }
    with open("models/metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print("\n✅ Training complete!")


if __name__ == "__main__":
    train()
