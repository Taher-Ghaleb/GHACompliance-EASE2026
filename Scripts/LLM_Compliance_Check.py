import os
import sys
import json
import re
import random
import zipfile
import yaml
from ollama import chat, ChatResponse
from openai import OpenAI

OPENAI_API_KEY = "<your_openai_api_key_here>"  
Compliance_json_path = os.path.join(".", "Data", "compliance_questions.json")
with open(Compliance_json_path, "r", encoding="utf-8") as f:
    Compliance_checklist = json.load(f)

def Ask_LLM(model_name, input_yml, compliance_checklist=Compliance_checklist):
    # Validate and clean model_name
    if not model_name:
        raise ValueError("model_name cannot be None or empty")
    
    model_name = model_name.strip()
    if not model_name:
        raise ValueError("model_name cannot be empty after stripping whitespace")
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior DevOps expert specialized in secure, efficient, and standardized CI/CD pipeline practices. "
                "Your task is to rigorously audit GitHub Actions (GHA) YAML workflow files for compliance with industry-recognized best practices. "
                "You understand both functional correctness and structural/organizational quality of CI workflows. "
                "You have a structured compliance checklist divided into 30 questions."
                "For **each question**, return one of:\n"
                "- 'YES'\n"
                "- 'NO: <reason>. Reference the related YAML key if applicable (e.g., 'jobs.<job_id>.name').'\n\n"
                "- 'NOT APPLICABLE'\n\n"
                "Do not summarize or return a flat list. Use a **JSON format** matching the checklist structure.\n\n"
                "Here is the compliance checklist:\n\n" +  
                json.dumps(compliance_checklist, indent=2)
                
            )
        },
        {
            "role": "user",
            "content": (
                "Audit the following GitHub Actions YAML workflow using the compliance checklist provided. "
                "Return your results as a **structured JSON** matching the question layout from the checklist. "
                "For each question, answer either:\n"
                "- 'YES'\n"
                "- 'NO: <short explanation and YAML key>'\n\n"
                "- 'NOT APPLICABLE'\n\n"
                "Return only valid JSON, with no commentary or markdown. Here is the workflow content:\n\n"
                f"{input_yml}\n\n# Unique ID: {hash(input_yml)}"
            )
        }
    ]

    if model_name.lower().startswith("gpt"):
        response = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
            model=model_name,
            temperature=0,
            messages=messages
        )
        output=response.choices[0].message.content or ""
    else:
        print(f"      --> Now prompting {model_name}")
        if not model_name or not model_name.strip():
            raise ValueError(f"Invalid model_name: '{model_name}'")
        response: ChatResponse = chat(
            model=model_name,
            messages=messages,
            options={"temperature": 0.3, 'num_ctx': 16384}
        )
        print(f"<---- Done prompting {model_name}")
        output = response.message.content or ""
        
    return output

def extract_json_from_raw(raw_output):
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        match = re.search(r"\{.*?\}", raw_output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                print("❌ Error parsing JSON from raw output.")
                return None

if __name__ == "__main__":
    root_path = "."
    zip_path = os.path.join(root_path, "Data", "java_yml_files.zip")
    output_json_path = os.path.join(root_path, "Results", "java_gha_compliance_llm_check_results.json")

    print(f" Output path: {output_json_path}")
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)

    if os.path.exists(output_json_path):
        with open(output_json_path, "r", encoding="utf-8") as f:
            all_results = json.load(f)
    else:
        all_results = []

    model_names = ["llama3.1:8b", "gemma3:12b", "mistral:7b", "phi4:14b", "gpt-5"]

    for model_name in model_names:
        print(f"Processing {model_name}...")
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            all_yml_files = [f for f in zipf.namelist() if f.endswith(".yml")]
            random.shuffle(all_yml_files)
            selected_files = all_yml_files[:95]
            for i, filename in enumerate(selected_files):
                with zipf.open(filename) as yml_file:
                    input_yml = yml_file.read().decode("utf-8")

                print(f"[{i+1}/95] Processing: {filename} ...")

                line_count = len([
                    line for line in input_yml.splitlines()
                    if line.strip() and not line.strip().startswith('#') and line.strip() != '-'
                ])

                try:
                    data = yaml.safe_load(input_yml)
                except Exception:
                    print(f"❌ Error parsing YAML in {filename}. Skipping...")
                    data = {}

                job_count = 0
                step_count = 0
                if isinstance(data, dict) and isinstance(data.get('jobs'), dict):
                    for job in data['jobs'].values():
                        job_count += 1
                        if isinstance(job, dict):
                            if 'steps' in job and isinstance(job['steps'], list):
                                step_count += len(job['steps'])
                            elif 'uses' in job:
                                step_count += 1

                print(f"   --> Compliance check for {filename} with model {model_name}...")
                raw_output = Ask_LLM(model_name, input_yml)
                result_json = extract_json_from_raw(raw_output)

                if not result_json:
                    result_json = {
                        "error": "No valid JSON parsed",
                        "raw_output": raw_output
                    }

                result_json.update({
                    "filename": filename,
                    "model": model_name,
                    "line_count": line_count,
                    "job_count": job_count,
                    "step_count": step_count
                })

                all_results.append(result_json)

                print(f"   --> Writing partial results after {i+1} files...")
                with open(output_json_path, "w", encoding="utf-8") as f:
                    json.dump(all_results, f, indent=2)

    print(f"\n Finished processing. Final output saved to: {output_json_path}")
