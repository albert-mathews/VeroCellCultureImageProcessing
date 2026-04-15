Comments legend:
@AlbertN -> the beginning of comment N, where N=1,2,3,4,5,...
@end -> the end of the comment.
When responding, please refer to the comments by number when appropriate. 

# Draft paper

## Introduction
This study benchmarks the performance of two domain-specific computer-vision tools (AIRVIC and Cellpose) and four general-purpose multimodal large language models (ChatGPT, Claude, Gemini, and Grok) on the task of detecting and classifying cytopathic effect (CPE) in Vero-cell culture microscope images. The objective is to evaluate whether any of these AI approaches can serve as objective, reproducible analysis tools for CPE detection in previously unseen images. Ground-truth CPE status and morphological types were derived exclusively from the image descriptions supplied by the contract research organization (CRO) that performed the cell-culture experiments. These descriptions were cross-referenced against the standardized CPE descriptors listed in CLSI M41 Table 7. Only the 22 images that received CRO descriptions were used for quantitative accuracy assessment; the remaining 83 images lacked descriptions and were therefore excluded from performance calculations.

## Methods

### Image dataset and ground truth
The study used the publicly available Vero Cell Culture Image Dataset (Mathews, A., 2025. Zenodo. https://doi.org/10.5281/zenodo.17928456). This dataset comprises 101 microscope images (two experimental paths, multiple passages) captured under standardized conditions. The CRO was instructed to provide descriptive captions for any image that would benefit from accompanying text; no specific directive was given to search for, classify, or quantify CPE. Consequently, 22 images contain CRO descriptions (hereafter “description set”) while 83 do not. Only the description set was employed for accuracy analyses.

### Standard CPE descriptors
Characteristic CPE descriptors were extracted from CLSI M41 Table 7 through iterative review. The descriptors (rounded, ballooned/enlarged, syncytia, vacuolation, detachment, granularity, refractile, cytoplasmic strands, nonspecific degeneration) were mapped to the six binary categories used for evaluation: Dy (Dying), Ro (rounded), V (vacuolation), D (detached), G (granularity), Re (refractile). The full CLSI M41 Table 7 is reproduced for reference.
@Albert1: that's not accurate. here is the process:
1-review table 7 to extract diecriptors: rounded, ballooned/enlarged, syncytia, vacuolation, detachment, granularity, refractile, cytoplasmic strands, nonspecific degeneration, no CPE. there are 10 in total.
2-repass table 7 to identify matching words and wording that closely correlates to a descriptor to produce clsi-table7-descriptors.tex showing the reader the instances of each descriptor for each virus in table 7. a sort of summary of table 7. maybe called a 'hit table' for descriptor_set+table7_text.
3-with the descriptors in hand, read through the images descriptions looking for word matches, or close correlates,..etc. same/similar process as step 2 above. this time producing a 'hit table' for the descriptor_set+image_description.
4-the result of step 3 meant that only 5 of the 10 table7 descriptors appeared in the images descriptions. the descriptor_set+image_description hit table had no entries for: ballooned/enlarged, syncytia, cytoplasmic strands, nonspecific degeneration, no CPE descriptors. 
5-a second result of step 3 was thta a new descriptor, "Dying Cells" was introduced. maybe this could have been classified as nonspecific degeneration, but it wasn't clear, so i kept the two seperate. 
6-so the descriptor set used for CRO image decriptions CPE detection hit table is: Dying cells (Dy), Rounded (Ro), Vacuolation (V), Detached (D), Granularity (G), Refractile (Re). call this the evaluation_descriptor_set.
7-obviously, the evaluation_descriptor_set is what was used in the LLM prompts since that is the only descriptor set for which ground truth was available.

Question: would it be better practice to map 'Dying Cells' to 'nonspecific degeneration', or are those two semantically different in the context of cell culture terminology such thta the differntiation in this paper is valid?
@end

<insert clsi-table7-descriptors.tex>

CRO image descriptions were cross-referenced with these descriptors to establish ground-truth CPE presence and type for each image in the description set. The resulting ground-truth labels were verified manually.

@Albert2: i figure it would be good to present the descriptor_set+image_description hit table.
<insert cro_cpe_detections.tex>
i have a csv for the above table.
@end

### AIRVIC analysis
AIRVIC (Turk et al., 2025) is a ResNet-based classifier trained specifically for CPE detection and virus identification in cell-culture images. All 101 images were uploaded to the web interface[](https://airvic.turkai.com/) with cell line set to “Vero” and virus set to “Unknown”. Because the interface does not support batch export, results were extracted manually and stored in CSV format. AIRVIC outputs a binary CPE decision (present/absent) and a predicted virus identity; no morphological subtype information is provided.
@Albert3: maybe we should say something about how the predicted virus identity is not important for this paper. 
@end

<insert airvic-results.tex>

### Cellpose analysis
Cellpose (Stringer et al., 2021) was used as the primary segmentation engine. A custom Python script (co-developed with Grok) processed all 101 images to generate instance masks. Post-processing metrics were then computed on the masks to derive a proxy for CPE presence. The two retained metrics—circularity (4π·area/perimeter²) and eccentricity—quantify the transition from spread polygonal to rounded morphology, a hallmark of CPE that is independent of serum-driven growth-rate changes.
@Albert4: previously you provided these references to justify the choice of circularity and eccentricity as proxies for CPE. these are listed below:
https://pmc.ncbi.nlm.nih.gov/articles/PMC11180103/ (Vero-cell CPE quantification confirming circularity and eccentricity as independent of growth-rate effects).
https://www.revvity.com/ask/cytopathic-effects (label-free CPE analysis in Vero cultures highlighting rounding morphology as the key proxy).
I think it is good practice to back up those decisions with references. we dont want to be seen as making up ways to infer CPE from basic morphology. this paper is massively under powered to achieve that.
@end

<insert cellpose-cpe-proxy-metrics.tex>

Binary CPE detection was obtained by converting the combined metrics into a probability score; values > 0.5 were classified as positive. No morphological subtype information was generated.
@Albert5: should equations used to computescore and probability beincluded? or is refernce to the github repo sufficient?
@end

<insert cellpose-results.tex>

### Multimodal AI analysis
Four multimodal large language models (ChatGPT, Claude, Gemini, Grok) were evaluated under identical conditions. For each model a dedicated Python script was written that (1) loads the PNG images, (2) supplies a standardized prompt describing the CPE classification task, and (3) requests JSON-formatted output. Each model was offered two example images with known ground truth for optional in-context learning. Prompt @Albert 'and processing script' @end engineering was performed collaboratively with the respective model. Model outputs were post-processed to produce per-image, per-morphology-type binary decisions that were compared against CRO ground truth.
@Albert6. that last sentence suggest that the models outputs were not somehow predictions of the presence of evaluation_descriptor_set CPE morphologies, when tis is eactly what the output. 
i think that should be reworded so it is clear to the reader the process was:
1-promt+images requesting detetcion of evaluation_descriptor_set
2-results from each LLM
3-scipt to aggregate result from each LLM
@end

<insert cpe_confusion_table.tex>

### Statistical evaluation
Performance was quantified using false-positive rate, false-negative rate, true-positive rate, true-negative rate, and overall accuracy. For the multimodal models these metrics were first computed separately for each of the six CPE morphological types and then macro-averaged. For AIRVIC and Cellpose the metrics were calculated directly on the binary CPE detection task. All calculations were performed on the 22-image description set only. Results are summarized in the aggregate performance table.
@Albert8. somewhere here we need to say thta we included always_true and always_false models results for comparison agains the computer-vision and LLM tools.
this is a critical part of the paper because this comparison highlights that even the best performing tool was outperformed by the always_false model.
@end

<insert aggregate-results.tex>

## Results
Results for each tool are presented in the tables referenced above. Key observations are noted in the Discussion.
@Albert9: this makes no sense. why have a results section, only to say the results are in the methods section. 
I think the way i had it before made more sense. 
Methods->describe methods for each tool
Results-> present tables
if you think we can mix the Methods and results in this paper, fine, but lets not call the section Methods, and then have an emoty Results section.
maybe call the section 'Methods and Results'?
@end

## Discussion

### Domain-specific tools
AIRVIC detected CPE in 21 of the 22 description-set images and in 100 of the 101 total images, producing a high false-positive rate (0.909) and overall accuracy of only 0.545. Although the test images are visually similar to the Vero-cell images used in AIRVIC’s original training set, the model failed to generalize effectively to the present dataset. 
@Albert10. here we need to justify our claim that the present image set is similar to the training image set.
<insert image-processing-vs-airvic-expectation-table.tex> is the meat of that argument.
please include this table and provide some discussion around it
@end

Cellpose similarly classified nearly all images as CPE-positive (accuracy 0.500), again driven by an extremely high false-positive rate. The morphological-proxy approach therefore did not provide useful discrimination in this dataset.

### Multimodal AI tools
The four general-purpose multimodal models exhibited macro-averaged accuracies between 0.542 and 0.709. Gemini achieved the highest overall accuracy (0.709) but at the cost of a very high false-negative rate, effectively behaving like a conservative “no-CPE” classifier. @Albert11. say something about how it was outperformed by the always_false model. this conclusion effectively invalidates the entire LLM approach on its own. @end. ChatGPT, Claude, and Grok showed balanced but still modest performance (accuracies 0.549–0.559) with substantial rates of both false positives and false negatives. None of the multimodal models reached a level of reliability that would support their use as objective CPE detection tools for this image set.

### Limitations
The ground-truth labels rest on CRO narrative descriptions that were not generated under a CPE-specific protocol. The description set is small (n = 22), and the remaining 83 images could not be evaluated quantitatively. Domain-specific tools were tested exactly as publicly available; no retraining or fine-tuning was performed. Prompt engineering for the multimodal models, while extensive, remains inherently model-dependent.

### Implications
None of the evaluated AI tools demonstrated sufficient accuracy or robustness to replace @Albert12 'or act as an objective second opinion' @end human expert interpretation of CPE in Vero-cell cultures under the conditions tested. Future work may benefit from larger, prospectively labeled datasets and from domain-specific fine-tuning of multimodal models.

## References
- Mathews, A. (2025). Vero Cell Culture Image Dataset [Data set]. Zenodo. https://doi.org/10.5281/zenodo.17928456
- CLSI M41 (latest edition). Table 7 – Characteristic CPE in Inoculated Tube Cultures.
@Albert13.
CLSI M41 Viral Culture (https://clsi.org/shop/standards/m41/)
@end
- Turk et al. (2025). AIRVIC: ... *Scientific Reports* (or appropriate citation once published).
@Albert14. 
Akkutay-Yoldar, Z., Yoldar, M.T., Akkaş, Y.B. et al. A web-based artificial intelligence system for label-free virus classification and detection of cytopathic effects. Sci Rep 15, 5904 (2025). https://doi.org/10.1038/s41598-025-89639-0
@end

- Stringer, C. et al. (2021). Cellpose: a generalist algorithm for cellular segmentation. *Nature Methods*.
- ChatGPT (OpenAI), Claude (Anthropic), Gemini (Google), Grok (xAI) – model versions used in 2025–2026.
- Revvity Signals Image Artist documentation[](https://www.revvity.com/...).
- Additional references for metric justification: PMC11180103 and Revvity CPE analysis notes.


@Albert15.
why did you elave out the part about other tools that were attempted?
is it not releveant that satndard bio field image processing tools like Fiji.ImageJ are potentially risking circular reasoning? i think we'll get criticism for not trying these standard tools. 
similar for CellProfiler, this is a powerful image processing tool, but due to risk of circular reasoning, it was excluded.
for Snapcyte, the tool was not available
for ImageAArtist, the tool was not available to the researcher.

I think if we do not address these points, then any reader/reviewer will quickly go to some LLM and ask for a,ist of tools that can process cell culture images and detect CPE. they will get a similar list i got when i asked thta question. when the LLM says "use Fiji/ImageJ, Cellprofiler Snapcyte, AIRVIC, Cellpose, ImageArtist, etc. the reader/reviewer will think I was lazy and not exhaustive in my work. that doesn't insttill confidence in the work, it instill a sense of low quality, and immediate skepticism. we should strive to be full transparent about our successes and our failures, revealing all our attempts to achieve our goals, and answer our questions. please make that last senstence sink in, and use it as your overall theme for helping me draft this paper.

we need to state why they were not included. maybe a subsection in methods for "tools exlcuded".
@end
