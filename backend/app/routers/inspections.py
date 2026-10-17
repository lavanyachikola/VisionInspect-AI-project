from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
import os, shutil, uuid, cv2, io, csv
from datetime import datetime, timedelta
from app.database import inspections_collection, products_collection
from app.preprocessing import advanced_preprocess_image
from app.quality_analysis import analyze_image_quality
from app.ai_model import detect_defects, draw_defect_result, MODEL_INFO
from app.pdf_report import generate_pdf_report
from bson import ObjectId

router = APIRouter(prefix="/inspections", tags=["Inspections"])

UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
RESULTS_DIR = "results"
REPORTS_DIR = "reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


def get_final_decision(severity_level: str, defect_detected: bool):
    if not defect_detected:
        return "PASS", "Product meets quality standards."
    decisions = {
        "Critical": ("REJECT", "Reject product immediately. Trigger quality inspection."),
        "High": ("REWORK", "Repair/Rework the product. Re-inspect after rework."),
        "Medium": ("REWORK", "Manual inspection required. Consider rework."),
        "Low": ("PASS", "Minor defect. Product acceptable with monitoring.")
    }
    return decisions.get(severity_level, ("REWORK", "Manual inspection required."))


def validate_image(file_path: str):
    try:
        img = cv2.imread(file_path)
        if img is None:
            return False, "Could not read image file"
        h, w = img.shape[:2]
        if h < 10 or w < 10:
            return False, "Image dimensions too small"
        if h > 10000 or w > 10000:
            return False, "Image dimensions too large"
        return True, "Image valid"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


@router.post("/upload")
async def upload_and_inspect(
    product_id: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        file_ext = os.path.splitext(image.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, "File type not allowed")

        product = None
        try:
            if ObjectId.is_valid(product_id):
                product = products_collection.find_one({"_id": ObjectId(product_id)})
        except:
            pass
        if not product:
            product = products_collection.find_one({"product_code": product_id})
        if not product:
            product = products_collection.find_one({})
        if not product:
            raise HTTPException(404, "No products found")

        unique_filename = f"{uuid.uuid4()}_{image.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        is_valid, message = validate_image(file_path)
        if not is_valid:
            os.remove(file_path)
            raise HTTPException(400, message)

        quality_analysis = analyze_image_quality(file_path)
        processed_info = advanced_preprocess_image(file_path, PROCESSED_DIR)
        detection_result = detect_defects(file_path, product.get("product_code", ""))

        result_image_filename = f"result_{uuid.uuid4().hex[:8]}.jpg"
        result_image_path = os.path.join(RESULTS_DIR, result_image_filename)

        if detection_result.get("defect_detected"):
            primary_defect = {
                "type": detection_result["defect_type"],
                "confidence": detection_result["confidence"],
                "location": detection_result["location"]
            }
            draw_defect_result(file_path, primary_defect, result_image_path,
                             detection_result["severity_level"])
        else:
            shutil.copy(file_path, result_image_path)

        decision, recommendation = get_final_decision(
            detection_result.get("severity_level", "None"),
            detection_result.get("defect_detected", False)
        )

        inspection_data = {
            "product_id": str(product["_id"]),
            "product_name": product.get("product_name", "Unknown"),
            "product_code": product.get("product_code", "Unknown"),
            "image_path": file_path,
            "processed_image_path": processed_info["processed_path"],
            "result_image_path": result_image_path,
            "image_filename": image.filename,
            "status": "completed",
            "image_width": processed_info["original_width"],
            "image_height": processed_info["original_height"],
            "file_size": processed_info["file_size"],
            "quality_analysis": quality_analysis,
            "preprocessing_steps": processed_info["steps"],
            "defect_detected": detection_result.get("defect_detected", False),
            "defect_type": detection_result.get("defect_type"),
            "confidence": detection_result.get("confidence", 0),
            "defect_location": detection_result.get("location"),
            "all_defects": detection_result.get("all_defects", []),
            "severity_score": detection_result.get("severity_score", 0),
            "severity_level": detection_result.get("severity_level", "None"),
            "decision": decision,
            "recommendation": recommendation,
            "timing": detection_result.get("timing", {}),
            "model_info": detection_result.get("model_info", MODEL_INFO),
            "created_at": datetime.utcnow(),
            "completed_at": datetime.utcnow()
        }

        result = inspections_collection.insert_one(inspection_data)
        inspection_data["id"] = str(result.inserted_id)

        return {
            "message": "Inspection completed",
            "inspection": {
                "id": inspection_data["id"],
                "product_name": inspection_data["product_name"],
                "product_code": inspection_data["product_code"],
                "image_filename": inspection_data["image_filename"],
                "status": inspection_data["status"],
                "created_at": inspection_data["created_at"].isoformat()
            },
            "validation": {"status": "passed", "message": message},
            "preprocessing": {
                "original_size": f"{processed_info['original_width']}x{processed_info['original_height']}",
                "processed_size": "224x224",
                "steps": processed_info["steps"]
            },
            "quality_analysis": quality_analysis,
            "ai_detection": {
                "defect_detected": detection_result.get("defect_detected"),
                "defect_type": detection_result.get("defect_type"),
                "confidence": detection_result.get("confidence"),
                "location": detection_result.get("location"),
                "all_defects": detection_result.get("all_defects", []),
                "severity_score": detection_result.get("severity_score"),
                "severity_level": detection_result.get("severity_level"),
                "decision": decision,
                "recommendation": recommendation,
                "timing": detection_result.get("timing", {}),
                "model_info": detection_result.get("model_info", {})
            },
            "result_image_url": f"http://127.0.0.1:8000/results/{result_image_filename}",
            "processed_image_url": f"http://127.0.0.1:8000/processed/{os.path.basename(processed_info['processed_path'])}"
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Inspection error: {str(e)}")


@router.get("/")
def get_inspections():
    inspections = list(inspections_collection.find().sort("created_at", -1))
    for inspection in inspections:
        inspection["id"] = str(inspection["_id"])
        inspection.pop("_id", None)
    return inspections


@router.get("/stats")
def get_stats():
    total = inspections_collection.count_documents({})
    defective = inspections_collection.count_documents({"defect_detected": True})
    passed = inspections_collection.count_documents({"decision": "PASS"})
    reworked = inspections_collection.count_documents({"decision": "REWORK"})
    rejected = inspections_collection.count_documents({"decision": "REJECT"})

    defect_rate = (defective / total * 100) if total > 0 else 0
    pass_rate = (passed / total * 100) if total > 0 else 0

    return {
        "total": total,
        "defective": defective,
        "passed": passed,
        "reworked": reworked,
        "rejected": rejected,
        "defect_rate": round(defect_rate, 2),
        "pass_rate": round(pass_rate, 2),
        "by_severity": {
            "Critical": inspections_collection.count_documents({"severity_level": "Critical"}),
            "High": inspections_collection.count_documents({"severity_level": "High"}),
            "Medium": inspections_collection.count_documents({"severity_level": "Medium"}),
            "Low": inspections_collection.count_documents({"severity_level": "Low"})
        }
    }


@router.get("/analytics/summary")
def get_analytics_summary():
    total = inspections_collection.count_documents({})
    defective = inspections_collection.count_documents({"defect_detected": True})
    passed = inspections_collection.count_documents({"decision": "PASS"})
    reworked = inspections_collection.count_documents({"decision": "REWORK"})
    rejected = inspections_collection.count_documents({"decision": "REJECT"})

    defect_types = ["Crack", "Dent", "Contamination", "Scratch", "Surface Defect"]
    defect_distribution = {dt: inspections_collection.count_documents({"defect_type": dt}) for dt in defect_types}

    severity_distribution = {
        "Critical": inspections_collection.count_documents({"severity_level": "Critical"}),
        "High": inspections_collection.count_documents({"severity_level": "High"}),
        "Medium": inspections_collection.count_documents({"severity_level": "Medium"}),
        "Low": inspections_collection.count_documents({"severity_level": "Low"})
    }

    defect_rate = (defective / total * 100) if total > 0 else 0
    pass_rate = (passed / total * 100) if total > 0 else 0

    avg_sev = list(inspections_collection.aggregate([
        {"$match": {"defect_detected": True}},
        {"$group": {"_id": None, "v": {"$avg": "$severity_score"}}}
    ]))
    avg_severity = round(avg_sev[0]["v"], 2) if avg_sev else 0

    avg_conf = list(inspections_collection.aggregate([
        {"$match": {"defect_detected": True}},
        {"$group": {"_id": None, "v": {"$avg": "$confidence"}}}
    ]))
    avg_confidence = round(avg_conf[0]["v"] * 100, 2) if avg_conf else 0

    daily_trend = []
    today = datetime.utcnow()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        s = day.replace(hour=0, minute=0, second=0, microsecond=0)
        e = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        daily_trend.append({
            "date": day.strftime("%b %d"),
            "total": inspections_collection.count_documents({"created_at": {"$gte": s, "$lte": e}}),
            "defective": inspections_collection.count_documents({"created_at": {"$gte": s, "$lte": e}, "defect_detected": True})
        })

    product_stats = []
    for item in inspections_collection.aggregate([
        {"$group": {
            "_id": "$product_name",
            "total": {"$sum": 1},
            "defective": {"$sum": {"$cond": ["$defect_detected", 1, 0]}}
        }},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]):
        if item["_id"]:
            pr = ((item["total"] - item["defective"]) / item["total"] * 100) if item["total"] > 0 else 0
            product_stats.append({
                "product": item["_id"],
                "total": item["total"],
                "defective": item["defective"],
                "pass_rate": round(pr, 2)
            })

    return {
        "total": total,
        "defective": defective,
        "passed": passed,
        "reworked": reworked,
        "rejected": rejected,
        "defect_rate": round(defect_rate, 2),
        "pass_rate": round(pass_rate, 2),
        "avg_severity": avg_severity,
        "avg_confidence": avg_confidence,
        "defect_distribution": defect_distribution,
        "severity_distribution": severity_distribution,
        "daily_trend": daily_trend,
        "product_stats": product_stats
    }


@router.get("/model-performance")
def get_model_performance():
    """Compute model metrics from stored inspections"""
    tp = tn = fp = fn = 0
    total_classified = 0

    for insp in inspections_collection.find({}):
        img_path = (insp.get("image_path") or insp.get("image_filename") or "").lower()
        is_defect = insp.get("defect_detected", False)

        is_actual_defect = any(k in img_path for k in [
            "broken", "contamination", "crack", "scratch",
            "dent", "hole", "damaged", "faulty", "defect",
            "bent", "cut", "missing", "glue", "poke"
        ])
        is_actual_good = "good" in img_path

        if not is_actual_defect and not is_actual_good:
            continue

        total_classified += 1

        if is_actual_defect:
            if is_defect: tp += 1
            else: fn += 1
        elif is_actual_good:
            if is_defect: fp += 1
            else: tn += 1

    total = tp + tn + fp + fn
    accuracy = ((tp + tn) / total * 100) if total > 0 else 0
    precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0
    recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    total_inspections = inspections_collection.count_documents({})
    defective_found = inspections_collection.count_documents({"defect_detected": True})
    passed = inspections_collection.count_documents({"decision": "PASS"})

    return {
        "total_tested": total_classified,
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "accuracy": round(accuracy, 2),
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1_score": round(f1, 2),
        "total_inspections": total_inspections,
        "defective_found": defective_found,
        "passed": passed
    }


@router.get("/export/csv")
def export_csv():
    """Export all inspections as CSV"""
    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Product", "Image", "Defect Type", "Confidence",
                        "Severity Score", "Severity Level", "Decision", "Date"])
        output.seek(0)
        yield output.read()
        output.seek(0)
        output.truncate(0)

        for insp in inspections_collection.find({}).sort("created_at", -1):
            writer.writerow([
                str(insp["_id"])[-4:],
                insp.get("product_name", ""),
                insp.get("image_filename", ""),
                insp.get("defect_type", "None") or "None",
                f"{int((insp.get('confidence') or 0) * 100)}%",
                insp.get("severity_score", 0),
                insp.get("severity_level", "None"),
                insp.get("decision", ""),
                insp.get("created_at", "").strftime("%Y-%m-%d %H:%M") if insp.get("created_at") else ""
            ])
            output.seek(0)
            yield output.read()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inspections.csv"}
    )


@router.get("/{inspection_id}/pdf")
def download_pdf(inspection_id: str):
    """Download inspection report as PDF"""
    try:
        inspection = inspections_collection.find_one({"_id": ObjectId(inspection_id)})
    except:
        inspection = inspections_collection.find_one({"_id": inspection_id})

    if not inspection:
        raise HTTPException(404, "Inspection not found")

    inspection["id"] = str(inspection["_id"])
    inspection.pop("_id", None)

    pdf_path = os.path.join(REPORTS_DIR, f"report_{inspection_id}.pdf")

    try:
        generate_pdf_report(inspection, pdf_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"inspection_report_{str(inspection_id)[-8:]}.pdf"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"PDF generation failed: {str(e)}")



@router.post("/batch-upload")
async def batch_upload_and_inspect(
    product_id: str = Form(...),
    images: list[UploadFile] = File(...)
):
    """Upload and inspect multiple images at once"""
    results = []
    errors = []
    
    for image in images:
        try:
            file_ext = os.path.splitext(image.filename)[1].lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                errors.append({"file": image.filename, "error": "File type not allowed"})
                continue
            
            product = None
            try:
                if ObjectId.is_valid(product_id):
                    product = products_collection.find_one({"_id": ObjectId(product_id)})
            except:
                pass
            if not product:
                product = products_collection.find_one({"product_code": product_id})
            if not product:
                product = products_collection.find_one({})
            if not product:
                errors.append({"file": image.filename, "error": "No product found"})
                continue
            
            unique_filename = f"{uuid.uuid4()}_{image.filename}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            is_valid, message = validate_image(file_path)
            if not is_valid:
                os.remove(file_path)
                errors.append({"file": image.filename, "error": message})
                continue
            
            quality_analysis = analyze_image_quality(file_path)
            processed_info = advanced_preprocess_image(file_path, PROCESSED_DIR)
            detection_result = detect_defects(file_path, product.get("product_code", ""))
            
            result_image_filename = f"result_{uuid.uuid4().hex[:8]}.jpg"
            result_image_path = os.path.join(RESULTS_DIR, result_image_filename)
            
            if detection_result.get("defect_detected"):
                primary_defect = {
                    "type": detection_result["defect_type"],
                    "confidence": detection_result["confidence"],
                    "location": detection_result["location"]
                }
                draw_defect_result(file_path, primary_defect, result_image_path,
                                 detection_result["severity_level"])
            else:
                shutil.copy(file_path, result_image_path)
            
            decision, recommendation = get_final_decision(
                detection_result.get("severity_level", "None"),
                detection_result.get("defect_detected", False)
            )
            
            inspection_data = {
                "product_id": str(product["_id"]),
                "product_name": product.get("product_name", "Unknown"),
                "product_code": product.get("product_code", "Unknown"),
                "image_path": file_path,
                "processed_image_path": processed_info["processed_path"],
                "result_image_path": result_image_path,
                "image_filename": image.filename,
                "status": "completed",
                "image_width": processed_info["original_width"],
                "image_height": processed_info["original_height"],
                "file_size": processed_info["file_size"],
                "quality_analysis": quality_analysis,
                "preprocessing_steps": processed_info["steps"],
                "defect_detected": detection_result.get("defect_detected", False),
                "defect_type": detection_result.get("defect_type"),
                "confidence": detection_result.get("confidence", 0),
                "defect_location": detection_result.get("location"),
                "all_defects": detection_result.get("all_defects", []),
                "severity_score": detection_result.get("severity_score", 0),
                "severity_level": detection_result.get("severity_level", "None"),
                "decision": decision,
                "recommendation": recommendation,
                "timing": detection_result.get("timing", {}),
                "model_info": detection_result.get("model_info", MODEL_INFO),
                "created_at": datetime.utcnow(),
                "completed_at": datetime.utcnow()
            }
            
            result = inspections_collection.insert_one(inspection_data)
            inspection_data["id"] = str(result.inserted_id)
            
            results.append({
                "id": inspection_data["id"],
                "filename": image.filename,
                "decision": decision,
                "defect_type": detection_result.get("defect_type"),
                "confidence": detection_result.get("confidence", 0)
            })
        except Exception as e:
            errors.append({"file": image.filename, "error": str(e)})
    
    return {
        "total": len(images),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.get("/{inspection_id}")
def get_inspection(inspection_id: str):
    try:
        inspection = inspections_collection.find_one({"_id": ObjectId(inspection_id)})
    except:
        inspection = inspections_collection.find_one({"_id": inspection_id})
    if not inspection:
        raise HTTPException(404, "Inspection not found")
    inspection["id"] = str(inspection["_id"])
    inspection.pop("_id", None)
    return inspection
