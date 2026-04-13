# Explanation
I tried using python to call MitTex to compile the latex paper.
this kept failing, and was not as easy to use as https://www.overleaf.com/.
So I chose to edit the latex paper in overleaf, but store versions of it here, along with a scraps file that i use to add/remove content from the various .tex files.

# TODO
1-try Cellpose
2-try SnapCyte

# Draft paper outline

## introduction
1-This study performs benchmark testing of various AI models on the task of detecting cytopathic effect (CPE) in cell culture microscope images.
2-One goal of this study is to determine whether domain-specific or multi-model AI tools can serve as objective analysis tools for detecting and/or classifying CPE in previously unseen cell culture images. 
3-This study selected 1 purposed-trained, and 4 multi-model AI tools for benchmarking. The domain-specific tool is AIRVIC, a ResNet-based classifier that was specifically trained and fine-tuned on labeled cell-culture microscope images for CPE detection and virus identification. The general-purpose multi-model tools are: ChatGPT, Claude, Gemini, Grok.
3-The ground truth for CPE presence and type in the images are image descriptions provided by the contract research organization (CRO) which conducted the cell culture experiment. The CRO was instructed to provide decriptions of cell culture images as follows. 
	"Any image which could be made more informative by an accompanying description should be accompanied by a description. Such descriptions should be provided in a document in which the descriptions are labeled by the image file name to remove any ambiguity as to which image the description applies to."
	The CRO was not intructured to search for CPE, classify CPE, or measure any quantity related to CPE. Any mention of CPE terminology is chosen by the CRO to best describe their interpretation of the images.
4-AIRVIC analysis
	https://www.nature.com/articles/s41598-025-89639-0
	https://airvic.turkai.com/
	All png files were uploaded to AIRVIC for processing. All images were uploaded with 'Cell line" set to "Vero", and "Virus" set to "Unknown". 
5-multi-model AI image analysis:
	To process the images, the AI tools are called via API. Processing instructions are captured in a python script which includes a prompt that details how the AI should approach the processing task. The scripts and prompts were iterated on by each AI tool as part of a circular process to mold the processing instructions and prompt to the unique capabilities of each. Put another way, each AI tool was a co-author of the script and prompt used to guide and execute the image processing task. All AIs were offered two images with ground truth for zero-shot learning assistance, not all chose to use that infdormation.

## methods

### common methods
1-split image set into two subsets: images with descriptions, and images without. 
2-determine CPE classes from CLSI-m41 Table 7.
3-use CPE classification and images descriptions to infer CRO detection of CPE types in images. this becomes the ground truth for assessing the other CPE detection tools.
	The CRO did not provide comments for all images. This produces a split in the image set from a ground truth perspective. The full set, the subset with descriptions, and the subset without descriptions. There are 101 images total, 22 have descriptions, 83 do not. Give the name 'descroption set' to the 22 images woith descriptions. 
4-encode CRO CPE detection in json format to be used in quantitative analyses. images without descriptions do not have ground truth, and are excluded from quantitative analyses.
5-convert dataset images to png
6-perform the tool specific methods below
7-aggregate the results to present as summary table.

### AIRVIC methods
1-upload all images 'Cell line" set to "Vero", and "Virus" set to "Unknown"
2-Due to limitations of the web based tool, results data were extracted manually. extract results manually, and store in csv for automatic processing.
3-The description set results are tabulated against the CRO ground truth. 

### multi-model AI methods
3-use AI tools to co-author the python script that executes the image analysis process by calling the AI tool API. some reuest a few zero shot learning exmaples.
4-execute AI image analysis process, output is json formatted results
5-post process the results to compute False Positive, False Negative, True Positive, True Negative results for each image in the description set.


## results
1-airvic cpe detection results
2-multi-modal AI cpe classification confusion table
3-Macro-averaged performance metrics

## discussion

### AIRVIC
1-Note that AIRVIC did not perform well. 
2-list the ways in which the images from this dataset could have been inappropriately captured for use with AIRVIC. create a table of what AIRVIC expects, and how the image were captured/processed that could shed light on why the tool did not work. 
3-The entire set results for the 101 images are sumarized by the fact that AIRVIC detected CPE in all but one image: EXP_path1_passage4_201.png. 
4-From this we can conclude that AIRVIC is not a useful tool for objectively assessing the presence of CPE in this image set. Given the images are of Vero cell cultures, and images captured almost ideally; it is surprizing that AIRVIC performed so poorly. 

### Multi-model AI tools
1-the AI tools appear to produce many false positive or many false negatives. 
2-the accuracy is too low to consider the tools acceptable as an objective second assement of CPE in the culture images.
3-future work. expand to large dataset with more ground truth. expand AI tool set.

### Other tools considered
1-the author also considered standard image processing tools: Fiji/ImageJ, CellProfiler
2- Fiji/ImageJ. these apply basic filtering functions, and extracting features  like CPE morphology means tuning the filters to find what you're looking for. Unless this has been configured previously on a 'training set', then it cannot serve as an objective analysis tool in this case. the reason is that would be tuning the process based on the CRO CPE indentification in the descriptions. CRO descriptions->CPE detection->Filter Tuning->CPE detetcion, this is circular reasoning.
3-CellProfiler. tried ExampleHuman.zip pipeline from https://cellprofiler-examples.s3.amazonaws.com/ExampleHuman.zip. Could not get it to work for my images. ccreating a pipeline risks circular reasining.
4-Snapcyte- could not create account. repeated attempts to contact failed. i think the company is no longer operational.
5-

references
1-source zenodo dataset
2-each AI tool. 
3-grok for paper drafting and post processing python code

