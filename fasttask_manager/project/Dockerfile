FROM irid/fasttask:latest

# set up your docker env here if necessary
# ---

# ---
WORKDIR /fasttask
COPY setting.py setting.py
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN rm -rf tasks
COPY tasks tasks