git clone https://github.com/Harshukallur/nl_api_agent.git

cd nl_api_agent

python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install -r requirements.txt

python -m app.server