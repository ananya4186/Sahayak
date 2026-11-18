Sahayak

Sahayak is a web app that helps people in India find government schemes that may suit them. A user picks the kind of support they want, enters a few details, and sees a preliminary, explainable rule match for the scheme in that category. Each result shows which conditions are matched, which have failed, and which information is missing. It also lists the benefits, the documents to keep ready, the application steps and the official source.

Important: Sahayak gives a preliminary rule match, not an official eligibility decision. It does not submit applications and does not guarantee eligibility or approval. Always confirm the requirements on the official scheme portal.

Features
Choose a goal first (education, business, skills, or pension). Only that category's scheme is evaluated.
Clear statuses: Eligible, Potential Match, Not Eligible, and Not Assessed.
A missing answer is never treated as a failure. It shows as "Information needed", and a failed condition always shows as failed.
For each scheme: benefits, documents (needed for everyone and needed only in some cases), application steps, and links to the official portal and sources.
A catalog of all schemes, grouped by category, with a "source checked" date.
No profile data is stored. The backend only evaluates the details in each request.
Schemes covered
Scheme	Category	Eligibility check
PM-USP CSSS	Education	Assessed
PM-DAKSH	Skill development	Assessed
PM-SYM	Pension and social security	Assessed
PMEGP	Employment and enterprise	Not assessed. Information only, because the current rules need confirmation on the official portal.
Tech stack
Backend: Python, FastAPI, Pydantic, Uvicorn
Frontend: HTML, CSS, JavaScript (no framework)
Scheme data and rules: JSON (backend/schemes.json)
Tests: pytest
Project structure
sahayak/
├── backend/
│   ├── main.py          # FastAPI app, profile model, rule engine
│   └── schemes.json     # scheme details and eligibility rules
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── docs/
│   └── SCHEME_SOURCES.md
├── tests/
│   ├── test_profile.py
│   └── test_engine.py
├── requirements.txt
└── README.md
How to run

You need Python 3 and VS Code with the Live Server extension.

Open the project folder in a terminal.
Create the virtual environment (first time only):
python -m venv .venv
Activate it (PowerShell):
.venv\Scripts\Activate.ps1
Install the packages (first time only):
pip install -r requirements.txt
Start the backend:
uvicorn backend.main:app --reload

The API runs at http://127.0.0.1:8000, and the interactive API docs are at http://127.0.0.1:8000/docs. 6. Start the frontend: in VS Code, right-click frontend/index.html and choose Open with Live Server. The page opens at http://127.0.0.1:5500/frontend/index.html.

Keep the backend terminal running while you use the page.

API endpoints
Method	Endpoint	What it does
GET	/	Health check
GET	/api/schemes	List all schemes
GET	/api/schemes/{scheme_id}	Get one scheme, or 404
POST	/api/profile/validate	Validate a profile (does not store it)
POST	/api/schemes/recommend	Evaluate a profile for the chosen goal and return the result
How eligibility rules work

Every scheme's rules live in backend/schemes.json. One evaluator in backend/main.py reads them, so changing a rule means editing the JSON, not the Python code.

Each rule names a profile field, an operator, a value and a label. The supported operators are gt, gte, lt, lte, between, is_true, is_false and in. A rule can also carry applies_when, for example "only for OBC or EWS applicants".

For each scheme the engine sorts the rules into matched, failed and missing, then decides the status:

Any failed rule gives Not Eligible.
No failed rules but some missing answers gives Potential Match.
All rules matched gives Eligible.
A scheme marked "assessable": false gives Not Assessed.

To add or update a scheme:

Read the official guideline and note the source link.
Edit its entry in backend/schemes.json, including the last_verified date.
Run the tests.
Run the tests

With the virtual environment active, run this from the project folder:

pip install pytest
pytest

The tests cover the rule engine for each scheme, goal filtering, and the structure of schemes.json.

Limitations
Only four schemes are covered. This is not a complete catalogue of Indian government schemes.
Results are preliminary and based on the rules in schemes.json. They are not an official decision, and approval is never guaranteed.
Sahayak does not submit applications and cannot verify an applicant with any government database.
Scheme rules can change. The "source checked" date shows when a source was last checked, not when the rules were issued.
PMEGP is shown for information only. Its current rules need confirmation on the official portal.
This is a local development setup. Before deploying, replace allow_origins=["*"] in backend/main.py with the real address of the frontend.
Sources

Official sources for each scheme are listed in docs/SCHEME_SOURCES.md and shown on each result card in the app.

Author

Ananya Jantli, BCA final-year project.