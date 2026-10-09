FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN pip install jupyterlab numpy pandas matplotlib scipy scikit-learn seaborn

WORKDIR /work
EXPOSE 8888

# Token-less access: only expose the port on the VM's localhost / trusted network.
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", \
     "--ServerApp.token=", "--ServerApp.password="]
