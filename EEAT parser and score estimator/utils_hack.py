import requests
import pandas as pd
import json

API_BASE_URL = "https://api.pgcloud.com/consumer/pampers/bricksadmin/v1"
URL_API = 'https://api.pgcloud.com/consumer/pampers/bricksadmin/v1/de/api/prompt/chain?code=zLaQq-b3ROtDrFSkm1RIJC6TC-v7Px2HJd6qfRHsDjo_AzFufmAqcg%3D%3D'
HEADERS_API =  {
    'Content-Type': 'application/json',
    'Ocp-Apim-Subscription-Key': '14f838fc30e84117bf6f5c109ef796b1',
    'project-name': 'Stellantis',
    'request-type': 'single'
}
USER_ID = "bocci.l@pg.com"
COST_CENTER = "8040400417"

API_KEY =  "14f838fc30e84117bf6f5c109ef796b1"


def get_eeat_prompts(tag_name: str = "EEAT",
                    api_base_url:str = API_BASE_URL,
                    api_key:str = API_KEY) -> dict:
    """Fetch all available EEAT prompt templates from the PRAaS API.

    Makes a GET request to the search-prompts endpoint to retrieve
    prompt definitions filtered by tag. Each prompt contains the
    template text, required variables, model config, and metadata.

    Args:
        tag_name: Tag to filter prompts by (default: "EEAT").

    Returns:
        dict with 'totalCount' and 'data' (list of prompt definitions).
    """
    response = requests.get(
        f"{api_base_url}/praas/search-prompts",
        params={"tagName": tag_name},
        headers={
            "accept": "application/json",
            "ocp-apim-subscription-key": api_key,
        },
    verify=False)
    response.raise_for_status()
    return response.json()


def parse_results(res_dict:dict,
                  prompt_type:str) -> dict:

    # extract main parts
    input_asses = res_dict['assistant'][0]['input']
    metadata_asses = res_dict['assistant'][0]['response_metadata']
    output_asses = res_dict['assistant'][0][prompt_type]
    
    if prompt_type in ['author_info_m',"author_info","page_purpose_m","page_purpose",
                       "contributor_author",
                      "content_angle_m",
                      "expertise_m",
                      "content_quality_m",
                       "title_quality_m",
                       "author_info_url",
                       "product_page_optimization_url",
                        "trust","expertise","experience",
                       "expertise_talent_skill","expertise_effort"
                      ]:
        
        # most have a specific prompt already parsed 
        final_output = json.loads(output_asses)
        

    # these start with the multiple sections and the answers aand rating are latet in " ```json:  ... ``` " 
    elif prompt_type in ['trust_m']:
        # these have a bit of ugly ones
        split_out = output_asses.split("###")
        main_asses = split_out[2]
        supl_asses = split_out[3]
        final_out = json.loads(split_out[-1].split("```json")[-1].replace("```",""))
        
        final_output = {"main_assesment":main_asses,
                        "suplimentary_assesment": supl_asses,
                        "question_ratings":final_out}    

    # these start with the keyword "json: ... " 
    elif prompt_type=='experience_m':
        final_output = json.loads(output_asses.split("```json")[-1].replace("```",""))    


    # these start with the keyword "output: ... "    
    elif prompt_type in ['multimedia_content_m',
                         'multimedia_content_html']:
        final_output = json.loads(output_asses.lower().split("output:")[-1].replace("```",""))


    # YMYL has a bad formatting
    elif prompt_type=='ymyl':
        # questions
        answers_list = output_asses.split("Output:")[-1].split("question_")
        answer_clean = '{"'
        for ans in answers_list[1:]:
            if ("answer" in ans) &("spectrum" not in ans):
                answer_clean =  answer_clean + "question_" + ans
        answer_clean =  json.loads(answer_clean + "question_" + ans[:ans.index("rating")+20])
        
        # explanations
        explanations = json.loads('{"spectrum'+output_asses.split("spectrum")[-1].replace("```",""))

        final_output = {"task 1":answer_clean,
                        "task 2":explanations}

    # The prompt does generate correct json format for parsing 
    elif prompt_type =='title_quality':
        title_quality = output_asses.split('"title_quality": ' )[-1].split(",")[0]
        explanation = output_asses.split('"explanation": ')[-1].replace("}","")
        final_output = { "title_quality":title_quality,
                        "explanation":explanation } 

        

    else:
        final_output = {}
        print("\033[91m[INFO]: No output, please select or update to different configs ...\033[0m")
        
    return {"input": input_asses,
            "output":final_output,
            "metadata":metadata_asses}       

    


def run_assessment(
    input_value: str,
    input_type: str,
    prompt_type: str,
    title: str = '',
    url_api: str = URL_API,
    user_id :str = USER_ID,
    cost_center :str = COST_CENTER,
    request_headers: dict = HEADERS_API,
    ) -> dict:
    """Run an assessment with the given parameters for the EEAT evaluation prompts.

    Args:
        input_value (str): The value for the assessment input.
        input_type (str): The type of the input.
        prompt_type (str): The type of the prompt.
        title (str, optional): Title for the assessment. Defaults to ''.
        url_api (str, optional): API URL. Defaults to URL_API.
        headers (dict, optional): API headers. Defaults to HEADERS_API.
    Return: 
        dictionary with information related to 
    
    """
    # Define the data payload
    payload = {
        input_type: input_value,
        "prompt": prompt_type,
        "userid": user_id,
        "costCenterCode": cost_center}
    if title:  payload['title'] = title 

    # Make the POST request with SSL verification disabled
    response = requests.post(url_api,
                             headers = request_headers, 
                             json = payload, 
                             verify=False)
    
    # Print the response
    print(f"[INFO]: LLM API response: {prompt_type} -> {response.status_code}")  # Print the status code
    result = response.json()     # Print the response JSON (if applicable)

    return parse_results(result,prompt_type)


def prompt_api(
    input_value: str,
    input_type: str,
    prompt_type: str,
    title: str = '',
    url_api: str = URL_API,
    user_id :str = USER_ID,
    cost_center :str = COST_CENTER,
    request_headers: dict = HEADERS_API,
    ) -> dict:
    """Run an assessment with the given parameters for the EEAT evaluation prompts.

    Args:
        input_value (str): The value for the assessment input.
        input_type (str): The type of the input.
        prompt_type (str): The type of the prompt.
        title (str, optional): Title for the assessment. Defaults to ''.
        url_api (str, optional): API URL. Defaults to URL_API.
        headers (dict, optional): API headers. Defaults to HEADERS_API.
    Return: 
        dictionary with information related to 
    
    """
    # Define the data payload
    payload = {
        input_type: input_value,
        "prompt": prompt_type,
        "userid": user_id,
        "costCenterCode": cost_center}
    if title:  payload['title'] = title 

    # Make the POST request with SSL verification disabled
    response = requests.post(url_api,
                             headers = request_headers, 
                             json = payload, 
                             verify=False)
    
    # Print the response
    print(f"[INFO]: LLM API response: {prompt_type} -> {response.status_code}")  # Print the status code
    result = response.json()     # Print the response JSON (if applicable)

    return result

