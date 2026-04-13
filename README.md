# Description
This repo has code and partial results used to produce the research paper:
<enter zenodo link>
Note: /paper/ contains the source latex file for the paper.

The original source images and image descriptions are from:
https://zenodo.org/records/16619228

## To reproduce the results
1. download the dataset from zenodo. extract all and copy the 'EXP stage' folder to the root of this repo clone.
2. create the converted_pngs dir from the source images. use convert_images_to_png.py
3. create AIRVIC account at https://airvic.turkai.com/, and upload images to view results.
4. run each individual_image_<ai>.py, you'll need subscriptions to each, and API keys in a .env file for this. you can skip this step and use the cpe_detection_results_<ai>.json files.
5. run compare-results.py FIXME, this is stale instructions

## .env file example
In order to execute step 3 above, you'll need API keys for each of the AI models. your keys are stored in a .env file that is not comitted to git.

Make a file named ".env", place it in the root of the repo clone. 
Copy code below, and add your API keys.
```
GOOGLE_API_KEY=<your key>
OPENAI_API_KEY=sk-proj-<rest of your key>
ANTHROPIC_API_KEY=sk-ant-<rest of your key>
XAI_API_KEY=xai-<rest of your key>
```

# Next steps.

1-improve the accuracy bar charts, and limit them to the updated cro results
2-do same for confusion matrix.
3-remove the isolation_historgrams.py and google sheets key. move to other repo.

# Scraps

## result presentation prompt
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



## next attempt at the tablular overview
i want a csv with following column names
path,id,CRO_Dy,CRO_Ro,CRO_V,CRO_D,CRO_G,CRO_Re,GPT_Dy,GPT_Ro,GPT_V,GPT_D,GPT_G,GPT_Re,CLD_Dy,CLD_Ro,CLD_V,CLD_D,CLD_G,CLD_Re,Gem_Dy,Gem_Ro,Gem_V,Gem_D,Gem_G,Gem_Re,GRK_Dy,GRK_Ro,GRK_V,GRK_D,GRK_G,GRK_Re

each row is for image path (1,2) and id. e.g.
path,id,...
1,201,...
1,503,...
2,101,...
2,405,...
...
etc.

columns: CRO_Dy,CRO_Ro,CRO_V,CRO_D,CRO_G,CRO_Re
if CRO json asserted Dying cells for an image, then column CRO_Dy is 1, else 0
if CRO json asserted Rounding for an image, then column CRO_Ro is 0, else 0
etc
CRO_V for vacuolation
CRO_D for Detached
CRO_G for Granularity, or Granular
CRO_Re for Refractile

then we have columsn for the AI results. <ai>_Dy,<ai>_Ro,<ai>_V,<ai>_D,<ai>_G,<ai>_Re
this is more complicated because we're sort of trying to encode the confusion martix in large table
if <ai> json asserted Dying cells for an image AND CRO did as well, then column <ai>_Dy is 1
if <ai> json asserted Dying cells for an image AND CRO did NOT, then column <ai>_Dy is -2
if <ai> json did NOT assert Dying cells for an image BUT CRO did assert, then column <ai>_Dy is -1
if <ai> json did NOT assert Dying cells for an image AND CRO did NOT, then column <ai>_Dy is 0

and so on for:
<ai>_V for vacuolation
<ai>_D for Detached
<ai>_G for Granularity, or Granular
<ai>_Re for Refractile

name the csv: cpe_confusion_table.csv








