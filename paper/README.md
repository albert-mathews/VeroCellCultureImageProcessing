# Explanation
I tried using python to call MitTex to compile the latex paper.
this kept failing, and was not as easy to use as https://www.overleaf.com/.
So I chose to edit the latex paper in overleaf, but store versions of it here, along with a scraps file that i use to add/remove content from paper.tex.



# Draft text for AI prompt to draft paper

introduction
1-The study benchmarks the performance of four AI models on the task of detecting cytopathic effects (CPE) in Vero cell culture images. In alphabetical order, the AI tools are: ChatGPT, Claude, Gemini, Grok.
2-The analysis leverages the multi-modal capabilities if the AI tools
3-The ground truth for CPE presence and type in the images are images descriptions provided by contract research organization whihc conducted the cell culture experiment.
4- To process the images, the AI tools are called via API. Processing instructions are captured in a python script which includes prompt thta details how the AI should approach the processing task. The scripts and prompts were iterated on by each AI tool as part of a circular process to mold the processing instructions and prompt to the unique capabilities oif each. i.e. each AI tool was a co-author of the script and prompt used to guide and execute the image processing task. All AIs were offer two images with ground truth for zero short assistance, not all chose to use that infdormation.
5-The goal of this study is to determine whether these multi-model AI tools can serve as objective analysis tools for detecting CPE in cell cultures images they have not seen before. 


methods
1-use python to preprocess the image set to PNG format of specific size.
2-encode CRO ground truth in json format.
3-use AI tools to co-author the python script that executes the image analysis process by calling the AI tool API
4-execute AI image analysis process
5-post process AI image analysis results to produce benchmarking visualizations


results
1-cpe comparison table
2-accuracy bar charts
3-confusion matrix


discussion
1-the AI tools appear to produce many false positive or many false negatives. 
2-the accuracy is too low to consider the tools acceptable as an objective second assement of CPE in the culture images.
3-future work. expand to large dataset with more ground truth. expand AI tool set.

references
1-source zenodo dataset
2-each AI tool. 
3-grok for paper drafting and post processing python code

