import pathlib
import textwrap
import google.generativeai as genai

import pandas as pd
import os
from pathlib import Path
import hashlib
from io import StringIO
import glob
import streamlit as st
import time



# 1.3 Retieve Google API key

api_key = st.secrets["G_Key"]
os.environ["G_Key"] = st.secrets["G_Key"]
api_key = os.getenv("G_Key")
genai.configure(api_key=api_key)

# Section 2: AI Generate Blueprint
#def AI_Generate_Blueprint(user_company_business, user_job_role, user_task, api_key, progress):
def AI_Generate_Blueprint(user_company_business, user_job_role, user_task, pbar):

  # Set up the model
  generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    #"max_output_tokens": 8192,
  }

  safety_settings = [
    {
      "category": "HARM_CATEGORY_HARASSMENT",
      "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
      "category": "HARM_CATEGORY_HATE_SPEECH",
      "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
      "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
      "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
      "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
      "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
  ]

  # Setting up the Gemini Pro Model
  #genai.configure(api_key=api_key)
  pbar.progress(10, text="Set up Gemini...")
  model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

  # 1st Prompt: Following Gemini Prompt Engineering: Persona, Task, Context and Format
  pbar.progress(20, text="1st prompt...")
  prompt = """You are a proficient {0} company trainer.  You are designing an on-job-training curriculum for job role {1} for the main task of {2}.  Please come out the training curriculum with the following headers for each subtask. Please display in a Markdown table format.
  1. Subtask name
  2. Task elements
  3. Key Points
  4. Task Standards
  5. Skills & Knowledge
  6. Training Guidelines
  """.format(user_company_business, user_job_role, user_task)

  # 1st Prompt send to Gemini
  part1_ojt = []

  convo = model.start_chat(history=[
  ])

  convo.send_message(prompt)
  #print(convo.last.text)
  part1_ojt.append(convo.last.text)

  pbar.progress(30, text="Pause for 10sec to fulfil free RPM...")
  #time.sleep(10)

  # 2nd prompt
  pbar.progress(40, text="2nd prompt...")
  prompt2 = """With the above curriculum, determine the set-up requirements and the resources you will need for this on-job-training.  Please generate the following headers for the above curriculum.  Within the “()” are the description of the header.  Please display in a Markdown table format.
  1. Set-up Requirement & Facilities (Describe the environment for the OJT to take place)
  2. Resources (List the materials required for the OJT. For example, Organisational procedures, guideline and forms; Documents, Tools; and Equipment and stationery, etc.)
  3. Quantity (Quantity to each resource)
  """

  # 2nd Prompt send Gemini
  part2_ojt = []
  convo.send_message(prompt2)
  #print(convo.last.text)
  part2_ojt.append(convo.last.text)

  tokens_count = model.count_tokens(convo.history)

  return part1_ojt, part2_ojt, tokens_count

# Section 3: Markdown Table to Dataframe
def Markdown2Dataframe(markdown):
  # Remove title and bold markers
  mk = markdown.split('|')
  markdown = markdown.replace(mk[0], '')  # Remove the title (e.g. '## Associate AI Engineer On-Job Training: Data Preparation Curriculum\n\n')
  markdown = markdown.replace('**', '') # Remove the Markdown '**' bold markers

  # Get the title of the table
  excel_name = mk[0].replace('##', '') # remove markdown '##' title marker
  excel_name = excel_name.replace('\n', '') # remove next line
  excel_name = excel_name.replace(':', '-') # remove ':' as file names do not allow to have ':'
  excel_name = excel_name.lstrip().rstrip()

  # Taken from https://stackoverflow.com/questions/77068488/how-to-efficiently-convert-a-markdown-table-to-a-dataframe-in-python
  # Use StringIO to create a file-like object from the text
  text_file = StringIO(markdown)

  # Read the table using pandas read_csv with '|' as the separator
  df = pd.read_csv(text_file, sep='|', skipinitialspace=True)

  # Remove leading/trailing whitespace from column names
  df.columns = df.columns.str.strip()

  # Remove the index column
  df = df.iloc[:, 1:]

  # Formatting in df
  header = list(df)
  df = df[df[header[0]].notna()] # Drop columns which is all NaN
  df = df.dropna(axis = 1) # Drop rows which is NaN
  df = df[1:] # drop the row with '---'
  df = df.reset_index() # reset index after dropping row with '---'

  header = list(df)
  # Replace Markdown bullet marker '*' with next line with '- '
  for hd in header:
    if 'index' in hd:
      continue

    for i in range(len(df)):
      s = df.loc[i, hd]
      s = s.replace('* ', '\n- ')
      s = s.replace('<br> -', '\n- ')
      if hd != header[1]:
        df.loc[i, hd] = s[1:]   # Remove 1st next line

  # Remove 1st column numbering in the wordings
  for i in range(len(df)):
    if any(char.isdigit() for char in df.loc[i, header[1]]):  # in case there is no numbering bullet
      s = df.loc[i, header[1]]
      s = s[1:]   # Remove 1st next line
      s = s.replace('. ', '')     # remove after number '. '
      df.loc[i, header[1]] = s   # remove '. ' after previous step remove the numbering

  # Remove 1st column '*' bullets in the wordings
  for i in range(len(df)):
    s = df.loc[i, header[1]]
    s = s.replace('* ', '\n- ')     # remove '*' with next line with dash
    if s[0] == '\n':
      s = s[1:]
    df.loc[i, header[1]] = s

  return excel_name, df


# Section 4: Putting everything together
## 4.1 Run button function
#def COJTC_Generator(Company_Business, Job_Role, Tasks, api_key, progress=gr.Progress(track_tqdm=True)):
def COJTC_Generator(Company_Business, Job_Role, Tasks, pbar):

  pbar.progress(5, text="Deleting previous outputs...")
  # Remove all previous spreadsheet
  for f in glob.glob("*.xlsx"):
    os.remove(f)

  pbar.progress(6, text="Generating Blueprints...")
  #task_analysis, set_up_requirement = AI_Generate_Blueprint(Company_Business, Job_Role, Tasks, api_key, progress)
  task_analysis, set_up_requirement, tokens = AI_Generate_Blueprint(Company_Business, Job_Role, Tasks, pbar)
  #print('task_analysis: ', task_analysis)
  #print('set_up_requirement: ', set_up_requirement)
  

  #task_analysis = "## Data Preparation Training Curriculum for Associate AI Engineers \n\n| **Subtask Name** | **Task Elements** | **Key Points** | **Task Standards** | **Skills & Knowledge** | **Training Guidelines** |\n|---|---|---|---|---|---|\n| **1. Data Collection and Ingestion** | * Identify data sources based on project requirements. * Extract data from various sources (databases, APIs, files). * Implement data ingestion pipelines using tools like Apache Kafka or Airflow. | * Data quality and relevance. * Efficient data extraction techniques. * Scalability and reliability of ingestion pipelines. | * Data completeness and accuracy verified. * Efficient data ingestion process with minimal errors. * Pipelines handle data volume fluctuations effectively. | * SQL, Python scripting, understanding of data structures, familiarity with data ingestion tools. | * Hands-on exercises with different data sources and ingestion tools. * Case studies of real-world data collection scenarios. * Code reviews and best practices for efficient data pipelines. | \n| **2. Data Cleaning and Preprocessing** | * Identify and handle missing values. * Detect and remove outliers and inconsistencies. * Perform data normalization and standardization. * Address data imbalances and biases. | * Impact of missing data on model performance. * Outlier detection techniques. * Feature scaling methods (e.g., min-max scaling, standardization). * Bias mitigation strategies. | * Missing values handled appropriately (e.g., imputation, removal). * Outliers identified and addressed. * Features scaled appropriately for the chosen model. * Data biases minimized or documented. | * Statistical analysis, data cleaning libraries (e.g., Pandas, NumPy), understanding of bias and fairness in AI. | * Practical exercises on real-world datasets with missing values, outliers, and biases. * Training on data cleaning tools and techniques. * Discussions on ethical considerations in data preprocessing. |\n| **3. Data Transformation and Feature Engineering** | * Convert data into suitable formats for AI models. * Create new features from existing data. * Encode categorical variables (e.g., one-hot encoding, label encoding). * Apply dimensionality reduction techniques (e.g., PCA). | * Feature engineering techniques for different data types. * Impact of feature engineering on model performance. * Understanding of dimensionality reduction methods. | * Data transformed into formats compatible with chosen AI models. * New features created enhance model accuracy. * Categorical variables encoded effectively. * Dimensionality reduction applied appropriately. | * Data manipulation skills, feature engineering libraries (e.g., Scikit-learn), understanding of different encoding and dimensionality reduction techniques. | * Guided projects on feature engineering for specific AI tasks. * Exploration of various feature engineering techniques and their impact. * Best practices for creating informative and relevant features. | \n| **4. Data Validation and Quality Control** | * Establish data quality metrics. * Implement data validation checks. * Monitor data drift and concept drift over time. * Ensure data lineage and traceability. | * Data quality dimensions (e.g., accuracy, completeness, consistency). * Data validation techniques. * Concept drift detection methods. * Importance of data lineage for debugging and auditing. | * Data quality metrics meet project requirements. * Data validation checks implemented effectively. * Data drift and concept drift monitored and addressed. * Clear data lineage established. | * Understanding of data quality principles, experience with data validation tools, familiarity with data lineage tracking methods. | * Training on data quality frameworks and tools. * Case studies of data quality issues in AI projects. * Best practices for maintaining data quality throughout the AI lifecycle. |\n\n**Additional Notes:**\n\n* The specific tools and techniques covered may vary depending on the company's technology stack and project requirements.\n* Ongoing evaluation and feedback are crucial for ensuring the effectiveness of the training program. \n* Encourage continuous learning and exploration of new data preparation tools and techniques. \n"
  #set_up_requirement = "## On-the-Job Training Setup and Resource Requirements\n\n| **Set-up Requirement & Facilities (Description)** | **Resources (Materials Required)** | **Quantity** |\n|---|---|---| \n| **1. Training Room/Workspace:** A dedicated space for training sessions with sufficient seating and a projector or large display screen.  | * Whiteboard or flip chart * Markers/pens * Projector and screen (or large display) * Comfortable seating * Training laptops with relevant software (e.g., Jupyter Notebook, Python IDEs, data processing tools) | * As needed based on trainee group size * 1 * 1 * As needed based on trainee group size * As needed based on trainee group size  |\n| **2. Access to Development Environment:** Trainees should have access to a cloud-based or local development environment with the necessary tools and libraries for data preparation tasks. | * Cloud computing platform (e.g., AWS, Azure, GCP) or local server * Data storage solutions (e.g., databases, data lakes) * Data preparation libraries (e.g., Pandas, NumPy) * Data ingestion tools (e.g., Apache Kafka, Airflow) * Version control system (e.g., Git)  | * As per company infrastructure * As per company infrastructure * Installed on training laptops * Access provided as needed * Access provided as needed |\n| **3. Real-world Datasets:**  Access to diverse datasets relevant to the company's AI projects for hands-on practice.  | * Company-specific datasets * Publicly available datasets (e.g., Kaggle) * Synthetic datasets for specific training scenarios | * As per project requirements and data access policies * As needed * As needed |\n| **4. Training Materials:** Comprehensive training materials covering each subtask, including presentations, hands-on exercises, and reference guides.  | * Presentation slides * Hands-on lab guides * Jupyter Notebooks with code examples * Reference sheets for key concepts and tools * Case studies of real-world data preparation scenarios | * 1 set per training module * 1 set per training module * 1 set per training module * 1 set per training module * As needed | \n| **5. Mentorship and Support:** Experienced AI engineers or data scientists available to provide guidance and support to trainees. | * Assigned mentors for each trainee or group of trainees * Regular feedback sessions * Access to online forums or communication channels for questions and support | * As needed based on trainee group size * Scheduled as per training plan * As needed | \n"
  pbar.progress(70, text="Process 1st Markdown...")

  name, df = Markdown2Dataframe(task_analysis[0])
  pbar.progress(80, text="Process 2nd Markdown...")

  name2, df2 = Markdown2Dataframe(set_up_requirement[0])

  # Taken from https://www.geeksforgeeks.org/how-to-write-pandas-dataframes-to-multiple-excel-sheets/
  pbar.progress(90, text="Writing to Excel...")

  # create a excel writer object
  with pd.ExcelWriter(name+'.xlsx') as writer:

      # use to_excel function and specify the sheet_name and index
      # to store the dataframe in specified sheet
      df.to_excel(writer, sheet_name="Task Analysis", index=False)
      df2.to_excel(writer, sheet_name="Set-up & Resources Checklist", index=False)

  pbar.progress(100, text="Completed")

  return tokens


## 4.2 Refresh Button Function
def ReturnFileName():
  items = os.listdir()

  file_name = ""
  #current_file_path = Path(__file__).resolve()

  current_dir = os.getcwd()

  #print('os items:', items)
  #print('current path:', current_file_path)
  #print('current dir:', current_dir)

  for each_fn in items:
    if each_fn.endswith(".xlsx"):
        file_name = each_fn
        break
  if file_name != '':
    #print('file_name:', file_name)
    file_path_name = current_dir + '/' + file_name
    #print('file path name: ', file_path_name)
  else:
    #print('file not generated')
    return "", ""

  return file_path_name, file_name # https://github.com/gradio-app/gradio/issues/2975#issuecomment-1385602531


# Streamlit Interface
# -------------------
coy_biz = ""
job_role= ""
job_task= ""

if "tokens_count_key" not in st.session_state:
    st.session_state["tokens_count_key"] = 0

st.title("COJTC Blueprint Generator")
st.write('Tokens used: ', st.session_state["tokens_count_key"]) 

col1, col2, col3 = st.columns(3)

with col1:
    coy_biz = st.text_input("Company Business:", "AI")
    #st.write("Company Business: ", coy_biz)

with col2:
    job_role = st.text_input("Job Role:", "Associate AI Engineer")
    #st.write("Job Role: ", job_role)

with col3:
    job_task = st.text_input("Job Task:", "Data Preparation")
    #st.write("Job Task: ", job_task)

placeholder = st.empty()

if st.button("Start Generating"):
    placeholder.empty()
    progress_text = "Operation in progress. Please wait."
    my_bar = st.progress(0, text=progress_text)

    tokens = COJTC_Generator(coy_biz, job_role, job_task, my_bar)
    st.session_state["tokens_count_key"] += tokens.total_tokens
    
    my_bar.empty()

    download_filepath, download_filename = ReturnFileName()
    if download_filepath != "":
        placeholder.text("Completed and click [Download] to download the Generated Spreadsheet.")
        with open(download_filepath, 'rb') as f:
            st.download_button('Download Generated Spreadsheet', f, file_name=download_filename)
    else:
       placeholder.text("Completed and error in generating the spreadsheet.")



