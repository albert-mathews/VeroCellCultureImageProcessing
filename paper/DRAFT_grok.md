# Draft paper

## Introduction
This study benchmarks the performance of two domain-specific computer-vision tools (AIRVIC and Cellpose) and four general-purpose multimodal large language models (ChatGPT, Claude, Gemini, and Grok) on the task of detecting and classifying cytopathic effect (CPE) in Vero-cell culture microscope images. The objective is to evaluate whether any of these AI approaches can serve as objective, reproducible analysis tools for CPE detection in previously unseen images. Ground-truth CPE status and morphological types were derived exclusively from the image descriptions supplied by the contract research organization (CRO) that performed the cell-culture experiments. These descriptions were cross-referenced against the standardized CPE descriptors listed in CLSI M41 Table 7. Only the 22 images that received CRO descriptions were used for quantitative accuracy assessment; the remaining 83 images lacked descriptions and were therefore excluded from performance calculations.

## Methods

### Image dataset and ground truth
The study used the publicly available Vero Cell Culture Image Dataset (Mathews, A., 2025. Zenodo. https://doi.org/10.5281/zenodo.17928456). This dataset comprises 101 microscope images (two experimental paths, multiple passages) captured under standardized conditions. The CRO was instructed to provide descriptive captions for any image that would benefit from accompanying text; no specific directive was given to search for, classify, or quantify CPE. Consequently, 22 images contain CRO descriptions (hereafter “description set”) while 83 do not. Only the description set was employed for accuracy analyses.

### Standard CPE descriptors
Characteristic CPE descriptors were extracted from CLSI M41 Table 7 through iterative review. The descriptors (rounded, ballooned/enlarged, syncytia, vacuolation, detachment, granularity, refractile, cytoplasmic strands, nonspecific degeneration) were mapped to the six binary categories used for evaluation: Dy (detachment), Ro (rounded), V (vacuolation), D (degeneration/nonspecific), G (granularity), Re (refractile). The full CLSI M41 Table 7 is reproduced for reference.

<insert clsi-table7-descriptors.tex>

CRO image descriptions were cross-referenced with these descriptors to establish ground-truth CPE presence and type for each image in the description set. The resulting ground-truth labels were verified manually.

### AIRVIC analysis
AIRVIC (Turk et al., 2025) is a ResNet-based classifier trained specifically for CPE detection and virus identification in cell-culture images. All 101 images were uploaded to the web interface[](https://airvic.turkai.com/) with cell line set to “Vero” and virus set to “Unknown”. Because the interface does not support batch export, results were extracted manually and stored in CSV format. AIRVIC outputs a binary CPE decision (present/absent) and a predicted virus identity; no morphological subtype information is provided.

<insert airvic-results.tex>

### Cellpose analysis
Cellpose (Stringer et al., 2021) was used as the primary segmentation engine. A custom Python script (co-developed with Grok) processed all 101 images to generate instance masks. Post-processing metrics were then computed on the masks to derive a proxy for CPE presence. The two retained metrics—circularity (4π·area/perimeter²) and eccentricity—quantify the transition from spread polygonal to rounded morphology, a hallmark of CPE that is independent of serum-driven growth-rate changes.

<insert cellpose-cpe-proxy-metrics.tex>

Binary CPE detection was obtained by converting the combined metrics into a probability score; values > 0.5 were classified as positive. No morphological subtype information was generated.

<insert cellpose-results.tex>

### Multimodal AI analysis
Four multimodal large language models (ChatGPT, Claude, Gemini, Grok) were evaluated under identical conditions. For each model a dedicated Python script was written that (1) loads the PNG images, (2) supplies a standardized prompt describing the CPE classification task, and (3) requests JSON-formatted output. Each model was offered two example images with known ground truth for optional in-context learning. Prompt engineering was performed collaboratively with the respective model. Model outputs were post-processed to produce per-image, per-morphology-type binary decisions that were compared against CRO ground truth.

<insert cpe_confusion_table.tex>

### Statistical evaluation
Performance was quantified using false-positive rate, false-negative rate, true-positive rate, true-negative rate, and overall accuracy. For the multimodal models these metrics were first computed separately for each of the six CPE morphological types and then macro-averaged. For AIRVIC and Cellpose the metrics were calculated directly on the binary CPE detection task. All calculations were performed on the 22-image description set only. Results are summarized in the aggregate performance table.

<insert aggregate-results.tex>

## Results
Results for each tool are presented in the tables referenced above. Key observations are noted in the Discussion.

## Discussion

### Domain-specific tools
AIRVIC detected CPE in 21 of the 22 description-set images and in 100 of the 101 total images, producing a high false-positive rate (0.909) and overall accuracy of only 0.545. Although the test images are visually similar to the Vero-cell images used in AIRVIC’s original training set, the model failed to generalize effectively to the present dataset. Cellpose similarly classified nearly all images as CPE-positive (accuracy 0.500), again driven by an extremely high false-positive rate. The morphological-proxy approach therefore did not provide useful discrimination in this dataset.

### Multimodal AI tools
The four general-purpose multimodal models exhibited macro-averaged accuracies between 0.542 and 0.709. Gemini achieved the highest overall accuracy (0.709) but at the cost of a very high false-negative rate, effectively behaving like a conservative “no-CPE” classifier. ChatGPT, Claude, and Grok showed balanced but still modest performance (accuracies 0.549–0.559) with substantial rates of both false positives and false negatives. None of the multimodal models reached a level of reliability that would support their use as objective CPE detection tools for this image set.

### Limitations
The ground-truth labels rest on CRO narrative descriptions that were not generated under a CPE-specific protocol. The description set is small (n = 22), and the remaining 83 images could not be evaluated quantitatively. Domain-specific tools were tested exactly as publicly available; no retraining or fine-tuning was performed. Prompt engineering for the multimodal models, while extensive, remains inherently model-dependent.

### Implications
None of the evaluated AI tools demonstrated sufficient accuracy or robustness to replace human expert interpretation of CPE in Vero-cell cultures under the conditions tested. Future work may benefit from larger, prospectively labeled datasets and from domain-specific fine-tuning of multimodal models.

## References
- Mathews, A. (2025). Vero Cell Culture Image Dataset [Data set]. Zenodo. https://doi.org/10.5281/zenodo.17928456
- CLSI M41 (latest edition). Table 7 – Characteristic CPE in Inoculated Tube Cultures.
- Turk et al. (2025). AIRVIC: ... *Scientific Reports* (or appropriate citation once published).
- Stringer, C. et al. (2021). Cellpose: a generalist algorithm for cellular segmentation. *Nature Methods*.
- ChatGPT (OpenAI), Claude (Anthropic), Gemini (Google), Grok (xAI) – model versions used in 2025–2026.
- Revvity Signals Image Artist documentation[](https://www.revvity.com/...).
- Additional references for metric justification: PMC11180103 and Revvity CPE analysis notes.
