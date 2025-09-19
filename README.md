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


