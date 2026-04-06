# 🚀 CrewAI Data Analysis Agent (100% Local — No API Key)

An intelligent **AI-powered data analysis system** built using **CrewAI + Ollama (local LLMs)** that automatically analyzes datasets and generates a professional **business-ready report**.

⚡ Runs fully **offline**
💰 **Zero cost (no API key required)**
📊 Supports CSV, Excel, JSON

---

## 🧠 What This Project Does

This system uses multiple AI agents to:

1. Load dataset
2. Perform statistical analysis
3. Detect correlations
4. Identify outliers
5. Generate a **complete executive report**

---

## 🏗️ Architecture

```
Input File → Loader Agent → Analysis Agent → Report Agent → Output Report
```

### 👇 Agents Used

* **Data Ingestion Specialist**
* **Senior Data Analyst**
* **Chief Data Insights Officer**

---

## 📁 Project Structure

```
crewai-data-analyst/
│
├── data_analyst_agent.py   # Main application
├── requirements.txt        # Dependencies
├── README.md               # Documentation
└── sample_data/            # Optional sample datasets
```

---

## ⚙️ Setup Instructions

### 1️⃣ Install Ollama (Local LLM)

Download & install:

👉 https://ollama.com

Then pull a model:

```bash
ollama pull mistral
```

OR

```bash
ollama pull llama3
```

---

### 2️⃣ Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ How to Run

```bash
python data_analyst_agent.py <data_file>
```

### Example:

```bash
python data_analyst_agent.py sales.csv
```

OR with output file:

```bash
python data_analyst_agent.py sales.csv report.md
```

---

## 📊 Output

The system generates:

✔ Dataset summary
✔ Statistics
✔ Correlation analysis
✔ Outlier detection
✔ Business insights
✔ Recommendations

👉 Output saved as:

```
analysis_report.md
```

---

## 🔍 Features

* ✅ Works with CSV, Excel, JSON
* ✅ Fully automated analysis
* ✅ Multi-agent architecture
* ✅ Local LLM (privacy-safe)
* ✅ Business-ready report generation
* ✅ No API cost

---

## 🧰 Technologies Used

* Python
* CrewAI
* Pandas
* Ollama (Local LLM)

---

## 💡 Example Use Cases

* Data analysis automation
* Business insights generation
* E-commerce data analysis
* Exploratory data analysis (EDA)
* Data engineering pipelines

---

## 🚀 Future Improvements

* Add visualization (Matplotlib / Power BI)
* Add Streamlit UI
* Support real-time data
* Integrate with Azure / AWS

---

## 🙌 Author

**Ramiz**

