# sandbox

Python 3.12 + JupyterLab (numpy, pandas, matplotlib, scipy, scikit-learn, seaborn).

1. On a machine with Docker and internet: `./build.sh` -> creates `sandbox.tar.gz`
2. Copy `sandbox.tar.gz` and `run.sh` to the VM (e.g. `scp sandbox.tar.gz run.sh user@vm:~/sandbox/`)
3. On the VM: `./run.sh` -> open http://<vm-ip>:8888 (or tunnel: `ssh -L 8888:localhost:8888 user@vm`)

Notebooks are saved in `./work` on the VM (mounted into the container).
Jupyter has no token/password: don't expose port 8888 publicly; use the SSH tunnel.
Add packages by editing the `pip install` line in the Dockerfile and rebuilding.
