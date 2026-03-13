## code for automating the processing of images from https://zenodo.org/records/16619228

## Gemini Results
individual_images_gemini.py does the following for each image sequentially. there is no memory retained between images.
upload image
process image alone with prompt
assess image for CPE and confluency
store results in dict

once done for all images, store dict in json file.

### Trials
trial 1. the first time i ran it, it detected much more CPE for path2 relative to path 1.
see the gemini_results.png, which shows the screenshot of the output.
the version of the json file can be found at 7518b9fb0fa33ebebccb76b16aa4e590979189b5

trial 2. I added the confluency request. that was it. this time it detected very little CPE, maybe 1 in path 1, and 3 in path2.
see 05450ebecc1d93d8cbe7b567e77a479879ae490f

trial 3. i changed the script to save the google AI studio uploaded image file ID to the json, so that if i want to re-run, i dont need to re-upload the image files.
like trial 2. this detected very little CPE.
see 5a3bb3e262af8c99ec96f8dac7a6a96d4d7122ea

Gemini did not seem to be very consistent. graphical review of the json output should better express this.


## ChatGPT Results
<need to extract the actualy results form the "full_response_text" fields since only that field and confluency were populated in the dict.



## Next steps.

1. try chat gpt a few more times. but have it correct populate the dict.
2. try other LLMs
3. write up results comparing to CRO results. 
4. repeat but request searching for VLPs in the TEM images.


# result presentation prompt
i want to expand compare_cpe_results.py to also produce the four following results presentations. do not undo anything the script does presently. 

first, we'll need to pick a plotting color for each AI. it would be best if we can pick a color that somewhat aligns with their company logos or color scheme. we'll use this color repeated in visuals for consistency for the reader. 



1] tabular plot of CPE type per image

this is one table, please make csv with out coloring, and html with coloring, and please add lines to export table to latex with coloring if possible.

the first column is the portion of the file name path Number, e.g. file name EXP_path1_...., the column is 1, EXP_path2_..., the column is 2. this column should be grouped, so col1 has two cells, "1" at top, and "2" at bottom

the second column is the images file names image identifier, e.g. EXP_path1_passage4_303, col2 is 303, EXP_path2_passage4_502, col2 is 502.



for each results.json, 6 more columns. the six columns have the headings "Dying Cells","Rounding","Vacuolation","Detached","Granularity","Refractile", but to kep the table dense and fitting a page, these will be shortened to "C","Ro","V","D","G","Re".

the first set of 6 columns is for the CRO result. we'll identify a specific cell by set,subcol,row,subrow, e.g. CRO,Ro,1,303, CRO,V,2,502, using the first second column examples above. the CRO set cells will be filled with "soft dark blue checkmarks" (BCM for short) when the CRO json indicates that the CRO assert the CPE for that image.



then, for each AI result json, when the AI asserted the same CPE type to the image, the cell is filled with BCM, when both CRO and AI asserted the CPE type not present, the cell is empty, when the AI asserted a CPE type but the CRO did not, the cell is filled with red X. 



this means the first row has grouped cells, for two cells are "Image ID", the next 6 are CRO, then the AI set appear in alphabetical order, ChatGPT, Claude, Gemini, Grok. 

the second row has Path, ID, "C","Ro","V","D","G","Re", "C","Ro","V","D","G","Re", ...



each AI column set should have its first two row headings color filled using the color scheme we chose



2] AI accuracy bar chart

then i want to show the AI accuracy using a grouped bar chart. the vertical axis is accuracy 0-100% (or limited if no AI achieved close to 100). the horizontal main axis is CPE type, "Dying Cells","Rounding","Vacuolation","Detached","Granularity","Refractile" as above. then, for each CPE type, there are 4 bars, one for each AI showing it accuracy for that CPE type. this means there are 6 groups of 4 bars.

the bar groups should have the AI accuracy results in the same alphabetical order, ChatGPT, Claude, Gemini, Grok. the bar color for each AI should be the same as we chose above.



3] AI accuracy spider chart

i also want to show the AI-per-CPE-type-accuracy as a superimposed spider plot, the spokes are the CPE type, and radial axis is accuracy 0-100% (or limited if no AI achieved close to 100). then 4 line spider plots for each AI, superimposed on each. the order should be so that the legend appears in the same alphabetical order, ChatGPT, Claude, Gemini, Grok. the line color should be the same as we chose above.



4] i want you to propose some confusion matrix graphics so i can see what those look like. if the coloring, ordering, and formatting scheme from the tables and plots above can be leaned on to format/color confusion matrix, do this as much as possible. 








