import cv2
import numpy as np
from skimage.morphology import skeletonize

# ---------------- Image Pipeline ----------------

def keep_largest_component(skeleton):
    # Convert to binary 0/1
    binary = skeleton > 0

    # Label connected components
    num_labels, labels = cv2.connectedComponents(binary.astype(np.uint8))

    if num_labels <= 1:
        return skeleton  # nothing to filter

    # Count pixels in each label
    counts = np.bincount(labels.flatten())

    # Ignore label 0 (background)
    counts[0] = 0

    # Find largest component
    largest_label = np.argmax(counts)

    # Keep only largest
    filtered = (labels == largest_label).astype(np.uint8) * 255

    return filtered

def process_image(self, path):
    original = cv2.imread(path)
    if original is None:
        raise FileNotFoundError(path)

    original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
    self.stages.append(original_rgb)

    # Grayscale
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    self.stages.append(gray)

    # Threshold
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY)
    self.stages.append(thresh)

    # Invert for skeleton (black track becomes foreground)
    binary = thresh == 0

    skeleton = skeletonize(binary)
    skeleton = (skeleton * 255).astype(np.uint8)
    self.stages.append(skeleton)

    # Keep only longest connected skeleton
    self.filtered = keep_largest_component(skeleton)
    self.stages.append(self.filtered)

    self.stage_slider.setMaximum(len(self.stages) )
    self.stage_slider.setValue(1)  # Start at "Original"
