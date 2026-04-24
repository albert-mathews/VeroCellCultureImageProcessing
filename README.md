# Description
This repo has code and partial results used to produce the research paper:
https://zenodo.org/records/19631281
Note: /paper/ contains the source latex file for the paper.

The original source images and image descriptions are from:
https://zenodo.org/records/16619228

## TODO
verify revity eccentricity reference.
PLOS version landscape tables

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

# Disclaimer
This work was quite iterative. Many paths were started, and only few succeeded. Not all files still in the repo are used to produce the final results.