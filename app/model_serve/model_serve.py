import os
import json
import glob
from src.models.run_detection_cpu import load_model, run_detection
from src.visualization.visu import merge_images, visualise_model_out

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

WEIGHTS_PATH = "models/detr_noneg_100q_bs20_r50dc5"
TEST_FILE_PATH = "inference/Turdus_merlula.wav"


class ModelServer:
    def __init__(self, weights_path, bird_dict) -> None:
        self.weights_path = weights_path
        logger.info("Weights path: {self.weights_path}")

        self.bird_dict = bird_dict
        self.bird_dict["Non bird sound"] = 0
        self.reverse_bird_dict = {
            id: bird_name for bird_name, id in self.bird_dict.items()
        }
        logger.info("Reversed birds dict: {self.reverse_bird_dict}")

        self.model = None
        self.config = None
        self.model_loaded = False

    def load(self) -> None:
        logger.info("Loading model...")
        self.model, self.config = load_model(self.weights_path)
        logger.info("Model loaded successfully")
        self.model_loaded = True

    def run_detection(self, file_path, return_spectrogram=False):
        spectrogram = None

        if not self.model_loaded:
            self.load()

        logger.info(f"Starting run_detection on {file_path.split('/')[-1]}...")
        fp, outputs, spectrogram = run_detection(
            self.model, self.config, file_path, return_spectrogram=return_spectrogram
        )
        logger.info(f"[fp]: \n{fp}\n\n")
        logger.info(f"[outputs]: \n{outputs}\n\n")
        self.detection_ready = True

        return fp, outputs, spectrogram

    def get_classification(self, file_path, return_spectrogram=False):
        fp, outputs, spectrogram = self.run_detection(file_path, return_spectrogram)

        class_bbox = merge_images(fp, outputs, self.config.num_classes)
        output = {
            self.reverse_bird_dict[idx]: {
                key: value.cpu().numpy().tolist()
                for key, value in class_bbox[str(idx)].items()
            }
            for idx in range(1, len(class_bbox) + 1)
            if len(class_bbox[str(idx)]["bbox_coord"]) > 0
        }

        logger.info(f"[output]: \n{output}")
        if return_spectrogram:
            visualise_model_out(output, fp, spectrogram, self.reverse_bird_dict)
            # TODO: enregistrer le spectrogram
        return output
