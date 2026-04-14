# Explanation
I tried using python to call MitTex to compile the latex paper.
this kept failing, and was not as easy to use as https://www.overleaf.com/.
So I chose to edit the latex paper in overleaf, but store versions of it here, along with a scraps file that i use to add/remove content from the various .tex files.

# TODO
1-try Cellpose
2-try SnapCyte

# Draft paper outline

## introduction
This study performs benchmark testing of various AI models on the task of detecting cytopathic effect (CPE) in cell culture microscope images.
One goal of this study is to determine whether domain-specific or multi-model AI tools can serve as objective analysis tools for detecting and/or classifying CPE in previously unseen cell culture images. 
This study selected 2 domain-specific, and 4 multi-model AI tools for benchmarking. The domain-specific tools are:
1-AIRVIC, a ResNet-based classifier that was specifically trained and fine-tuned on labeled cell-culture microscope images for CPE detection and virus identification. 
2-Cellpose, <enter short description including python post processing>
The general-purpose multi-model tools are: ChatGPT, Claude, Gemini, Grok.
The ground truth for CPE presence and type in the images is sourced from image descriptions provided by the contract research organization (CRO) which conducted the cell culture experiment. The CRO was instructed to provide decriptions of cell culture images as follows. 
	"Any image which could be made more informative by an accompanying description should be accompanied by a description. Such descriptions should be provided in a document in which the descriptions are labeled by the image file name to remove any ambiguity as to which image the description applies to."
	The CRO was not intructured to search for CPE, classify CPE, or measure any quantity related to CPE. Any mention of CPE terminology is chosen by the CRO to best describe their interpretation of the images.
	The CRO images descriptions were crossreferenced with CPE terms from CLSI-M41 Table 7
The results from each attempt are tabulated for the reader, and tabulated results are summaerized with statistical overview.


## methods

### Identification of standard CPE descriptors
Characteristic cytopathic effect (CPE) descriptors were extracted from CLSI M41 Table 7 through an iterative peer-review process conducted between the author and Grok, an AI research assistant. The full raw text of Table 7 was read and analyzed multiple times to systematically identify recurring qualitative descriptors used to characterize CPE morphology for each virus (e.g., rounded, ballooned/enlarged, syncytia, vacuolation, detachment, granularity, refractile, cytoplasmic strands, and nonspecific degeneration). These descriptors were mapped into categorical columns, and instances of the descriptors for each virus are captuerd in the table.
<insert clsi-m41-table7-terms.tex>
use CPE descriptors and images descriptions to infer CRO detection of CPE types in images. This becomes the ground truth for assessing the other tools on the CPE detection/classification task.
	The CRO did not provide comments for all images. This produces a split in the image set from a ground truth perspective. There are 101 images total, 22 have descriptions, 83 do not. The subset of 22 are given the name 'descroption set' from here on. the subset of 83 without descriptions are excluded from accuracy analyses.
	the list of M41 table 7 CPE descriptors, and the document of CRO image decriptions were provied to multi-model AI to extract presence of CPE type per image. This results was verified manually and corrected where needed.

### AIRVIC analysis methods
https://www.nature.com/articles/s41598-025-89639-0
https://airvic.turkai.com/
1-upload all images 'Cell line" set to "Vero", and "Virus" set to "Unknown"
2-Due to limitations of the web based tool, results data were extracted manually. extract results manually, and store in csv for automatic processing.
3-The description set results are tabulated against the CRO ground truth. 

### Cellpose methods
1-Grok drafted a script that automatically processed the 101 images with Cellpose as the first layer. 
2-Cellpose is used to produce the mask images, and Groks script was used to post process the mask images to detect features suggestive of CPE presence
3-<insert cellpose-cpe-proxy-metric>

### multi-model AI methods
1-To process the images, the AI tools are called via API. Processing instructions are captured in a python script which includes a prompt that details how the AI should approach the processing task. The scripts and prompts were iterated on by each AI tool as part of a circular process to mold the processing instructions and prompt to the unique capabilities of each. Put another way, each AI tool was a co-author of the script and prompt used to guide and execute the image processing task. All AIs were offered two images with ground truth for zero-shot learning assistance, not all chose to use that infdormation.
2-execute AI image analysis process, output is json formatted results
3-post process the results to compute False Positive, False Negative, True Positive, True Negative results for each image in the description set.

## results
Results for eahc tool or group of tools are presented in tabular form below.

### AIRVIC
<insert airvic-results.tex>

### Cellpose
TODO: compile results
<no results tex table>

### Multi-modeal AI
<insert cpe_confusion_table.tex>

### Accuracy Summary
Macro-averaged performance metrics
TODO: need to use the grok chat "Rates Comparison: AI Model Confusion matrix" to update compute_confusion_results.py to include cellpose results. 

## discussion

### AIRVIC
1-Note that AIRVIC did not perform well. 
2-the image-processing-vs-airvic-expectation-table.tex provide a breakdown of the AIRVIC training set images vs the dataset images. although not identical, they are quite similar. not much can be done at this point to improve AIRVIC performance. 
3-Results for all 101 images are sumarized by the fact that AIRVIC detected CPE in all but one image: EXP_path1_passage4_201.png. 
4-From this we can conclude that AIRVIC is not a useful tool for objectively assessing the presence of CPE in this image set. Given the images are of Vero cell cultures, and images captured almost ideally; it is dissapointing that AIRVIC performed so poorly.

### Cellpose


### Multi-model AI tools
1-the AI tools appear to produce many false positive or many false negatives. 
2-the accuracy is too low to consider the them useful as objective CPE detection/classification tools for this image set.

### Other tools considered
1-the author also considered standard image processing tools: Fiji/ImageJ, CellProfiler
2- Fiji/ImageJ. these apply basic filtering functions, and extracting features  like CPE morphology means tuning the filters to find what you're looking for. Unless this has been configured previously on a 'training set', then it cannot serve as an objective analysis tool in this case. the reason is that would be tuning the process based on the CRO CPE indentification in the descriptions. CRO descriptions->CPE detection->Filter Tuning->CPE detetcion, this is circular reasoning.
3-CellProfiler. tried ExampleHuman.zip pipeline from https://cellprofiler-examples.s3.amazonaws.com/ExampleHuman.zip. Pipeline processing is rigid with expected inputs. the dataset . ccreating a pipeline risks circular reasining.
4-Snapcyte- could not create account. repeated attempts to contact failed. i think the company is no longer operational.
5-

references
-source zenodo dataset
-AIRVIC paper
-Cellpose
-each AI tool: ChatGPT, Claude, Gemini, Grok. 
-grok for paper drafting and post processing python code

