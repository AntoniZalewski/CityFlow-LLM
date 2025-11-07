FROM cityflowproject/cityflow:latest

WORKDIR /app

COPY services/cityflow-sim/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --upgrade pip
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services/cityflow-sim /app

EXPOSE 7001

CMD ["python3", "-m", "cityflow_sim"]
