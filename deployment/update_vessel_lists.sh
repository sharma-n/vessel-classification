echo "Starting Update"
nohup sudo docker run --rm -v ~/.ssh:/root/.ssh -v ~/vessel-classification/logs:/app/logs update_vessel_lists python deployment/update_vessel_lists.py > ~/vessel-classification/logs/last_run.txt 2>&1 &