FROM irid/fasttask

# set up your docker env here if necessary
# ---

# ---
WORKDIR /fasttask
COPY req.txt req.txt
RUN pip install -r req.txt
COPY setting.py setting.py
RUN rm -rf tasks
COPY tasks tasks