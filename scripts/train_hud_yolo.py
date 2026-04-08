from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    dataset_yaml = project_root / "datasets" / "hud_bars" / "dataset.yaml"
    model_path = project_root / "yolov8n.pt"
    output_dir = project_root / "runs" / "hud_bars"

    model = YOLO(str(model_path))
    model.train(
        data=str(dataset_yaml),
        epochs=100,
        imgsz=256,
        batch=4,
        device="cpu",
        project=str(output_dir.parent),
        name=output_dir.name,
        exist_ok=True,
    )


if __name__ == "__main__":
    main()
