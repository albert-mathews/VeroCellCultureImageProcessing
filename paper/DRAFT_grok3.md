# Draft paper

## Introduction
This study benchmarks the performance of two domain-specific computer-vision tools (AIRVIC and Cellpose) and four general-purpose multimodal large language models (ChatGPT, Claude, Gemini, and Grok) on the task of detecting and classifying cytopathic effect (CPE) in Vero-cell culture microscope images. The objective is to evaluate whether any of these AI approaches can serve as objective, reproducible analysis tools for CPE detection in previously unseen images. Ground-truth CPE status and morphological types were derived exclusively from the image descriptions supplied by the contract research organization (CRO) that performed the cell-culture experiments. These descriptions were cross-referenced against the standardized CPE descriptors listed in CLSI M41 Table 7. Only the 22 images that received CRO descriptions were used for quantitative accuracy assessment; the remaining 83 images lacked descriptions and were therefore excluded from performance calculations.

## Methods

### Image dataset and ground truth
The study used the publicly available Vero Cell Culture Image Dataset (Mathews, A., 2025. Zenodo. https://doi.org/10.5281/zenodo.17928456). This dataset comprises 101 microscope images (two experimental paths, multiple passages) captured under standardized conditions. The CRO was instructed to provide descriptive captions for any image that would benefit from accompanying text; no specific directive was given to search for, classify, or quantify CPE. Consequently, 22 images contain CRO descriptions (hereafter “description set”) while 83 do not. Only the description set was employed for accuracy analyses.

### Standard CPE descriptors
Characteristic CPE descriptors were extracted from CLSI M41 Table 7 through an iterative review process. First, the full table was examined to identify the complete set of ten descriptors: rounded, ballooned/enlarged, syncytia, vacuolation, detachment, granularity, refractile, cytoplasmic strands, nonspecific degeneration, and no CPE. A CPE descriptor incidence table was then constructed by mapping every instance of these terms (or close semantic correlates) to each entry in the “Appearance” column of Table 7. The CLSI M41 Table 7 incidence table is reproduced below for reference.

<insert clsi-table7-descriptors.tex>

Next, the same mapping procedure was applied to the CRO image descriptions to generate a second incidence table (descriptor_set + image_description). Only five of the original ten CLSI descriptors appeared in the CRO descriptions. A sixth term, “Dying Cells”, emerged directly from the CRO text and was retained as a distinct category (Dy) rather than being forced into the CLSI “nonspecific degeneration” bin. The resulting evaluation_descriptor_set used for ground truth and all subsequent analyses therefore consisted of: Dying cells (Dy), Rounded (Ro), Vacuolation (V), Detached (D), Granularity (G), and Refractile (Re). CRO image descriptions were cross-referenced with the evaluation_descriptor_set to establish ground-truth CPE presence and type for each image in the description set. The CRO incidence table is provided as supplementary information to illustrate the exact word-matching logic used to establish ground truth.

<insert cro_cpe_detections.tex>

### AIRVIC analysis
AIRVIC (Akkutay-Yoldar et al., 2025) is a ResNet-based classifier trained specifically for CPE detection and virus identification in cell-culture images. All 101 images were uploaded to the web interface[](https://airvic.turkai.com/) with cell line set to “Vero” and virus set to “Unknown”. Because the interface does not support batch export, results were extracted manually and stored in CSV format. AIRVIC outputs a binary CPE decision (present/absent) and a predicted virus identity; the virus predictions are not used in this study, which focuses exclusively on CPE detection.

### Cellpose analysis
Cellpose (Stringer et al., 2021) was used as the primary segmentation engine. A custom Python script (co-developed with Grok) processed all 101 images to generate instance masks—binary images in which each individual cell is delineated as a separate labeled region. Post-processing metrics were then computed on the masks to derive a proxy for CPE presence. The two retained metrics—circularity \((4\pi \cdot \text{area} / \text{perimeter}^2)\) and eccentricity—quantify the transition from spread polygonal to rounded morphology, a hallmark of CPE that is independent of serum-driven growth-rate changes (e.g., PMC11180103; Revvity, 2024).
@Albert1. i want the references to be supporting of text that explains why the two metrics were believed to be good proxies for CPE presence.
when developing this method with you, you chose these metrics, and justified your choices to me by provinding these refernces:
https://pmc.ncbi.nlm.nih.gov/articles/PMC11180103/ (Vero-cell CPE quantification confirming circularity and eccentricity as independent of growth-rate effects).
https://www.revvity.com/ask/cytopathic-effects (label-free CPE analysis in Vero cultures highlighting rounding morphology as the key proxy).
please extend the above text to include discussion of how the final process was developed. we need to be transfparent about our rationale. 
dont just list the refs. say things like " this metric was selected because this refernce showed good correlation between the metric and CPE presnece, etc."
@end

<insert cellpose-cpe-proxy-metrics.tex>

Binary CPE detection was obtained by converting the combined metrics into a probability score; values > 0.5 were classified as positive. No morphological subtype information was generated. The exact probability formula and post-processing code are available in the project GitHub repository.

### Multimodal AI analysis
Four multimodal large language models (ChatGPT, Claude, Gemini, Grok) were evaluated under identical conditions. For each model a dedicated Python script was written that (1) loads the PNG images, (2) supplies a standardized prompt requesting detection of the six evaluation_descriptor_set morphologies, and (3) requests JSON-formatted output. Each model was offered two example images with known ground truth for optional in-context learning. Prompt and processing-script engineering was performed collaboratively with the respective model. Model outputs were post-processed by a script to produce per-image, per-morphology-type binary decisions that were compared against CRO ground truth.

### Other tools considered and excluded
Standard image-processing tools commonly used in cell-culture analysis were evaluated but excluded for the following reasons. Fiji/ImageJ requires manual filter tuning or macro development that would necessarily incorporate knowledge of the CRO descriptions, introducing circular reasoning and violating the requirement for an objective, a-priori tool. CellProfiler was tested with the official “ExampleHuman” pipeline; however, the pipeline proved too rigid for the present image set, and any custom pipeline development would again risk circular reasoning. Snapcyte could not be accessed after repeated failed account-creation attempts and lack of response from the vendor. Revvity Signals Image Artist was discussed with the manufacturer but commercial and technical setup barriers prevented its inclusion. These exclusions are reported for transparency; the tools ultimately benchmarked represent the most readily available and least biased options that could be applied without post-hoc tuning to the ground truth.
@Albert2. this is well done. thanks
@end

### Statistical evaluation
Performance was quantified using false-positive rate, false-negative rate, true-positive rate, true-negative rate, and overall accuracy. For the multimodal models these metrics were first computed separately for each of the six CPE morphological types and then macro-averaged. For AIRVIC and Cellpose the metrics were calculated directly on the binary CPE detection task. Baseline “always-positive” and “always-negative” classifiers were also evaluated for comparison. All calculations were performed on the 22-image description set only.

## Results
Performance results for each tool are presented below.

### AIRVIC
<insert airvic-results.tex>

### Cellpose
<insert cellpose-results.tex>

### Multimodal AI models
<insert cpe_confusion_table.tex>

### Aggregate performance summary
<insert aggregate-results.tex>

## Discussion

### Domain-specific tools
AIRVIC detected CPE in 21 of the 22 description-set images and in 100 of the 101 total images, producing a high false-positive rate (0.909) and overall accuracy of only 0.545. The test images are visually similar to the Vero-cell images used in AIRVIC’s original training set, as demonstrated by the table below.

<insert image-processing-vs-airvic-expectation-table.tex>

Despite this similarity, the model failed to generalize effectively to the present dataset. 

Cellpose similarly classified nearly all images as CPE-positive (accuracy 0.500), again driven by an extremely high false-positive rate. The morphological-proxy approach therefore did not provide useful discrimination in this dataset.

### Multimodal AI tools
The four general-purpose multimodal models exhibited macro-averaged accuracies between 0.542 and 0.709. Gemini achieved the highest overall accuracy (0.709) but at the cost of a very high false-negative rate, effectively behaving like a conservative “no-CPE” classifier; this performance was still lower than that of the simple always-negative baseline model. ChatGPT, Claude, and Grok showed poor performance (accuracies 0.549–0.559) with substantial rates of both false positives and false negatives. None of the multimodal models reached a level of reliability that would support their use as objective CPE detection tools for this image set.

### Limitations
The ground-truth labels rest on CRO narrative descriptions that were not generated under a CPE-specific protocol. The description set is small (n = 22), and the remaining 83 images could not be evaluated quantitatively. Domain-specific tools were tested exactly as publicly available; no retraining or fine-tuning was performed. Prompt engineering for the multimodal models, while extensive, remains inherently model-dependent.

### Implications
None of the evaluated AI tools demonstrated sufficient accuracy or robustness to replace or act as an objective second opinion for human expert interpretation of CPE in Vero-cell cultures under the conditions tested. Future work may benefit from larger, prospectively labeled datasets and from domain-specific fine-tuning of multimodal models.

## References
- Mathews, A. (2025). Vero Cell Culture Image Dataset [Data set]. Zenodo. https://doi.org/10.5281/zenodo.17928456
- CLSI M41. Viral Culture. Clinical and Laboratory Standards Institute. https://clsi.org/shop/standards/m41/
- Akkutay-Yoldar, Z., Yoldar, M.T., Akkaş, Y.B. et al. (2025). A web-based artificial intelligence system for label-free virus classification and detection of cytopathic effects. *Sci Rep* 15, 5904. https://doi.org/10.1038/s41598-025-89639-0
- Stringer, C. et al. (2021). Cellpose: a generalist algorithm for cellular segmentation. *Nature Methods*.
- PMC11180103. Vero-cell CPE quantification reference. https://pmc.ncbi.nlm.nih.gov/articles/PMC11180103/
- Revvity. Cytopathic effects analysis notes. https://www.revvity.com/ask/cytopathic-effects
- ChatGPT (OpenAI), Claude (Anthropic), Gemini (Google), Grok (xAI) – model versions used in 2025–2026.