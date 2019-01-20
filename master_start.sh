cd ~
mkdir data
mkdir data/db
mkdir data/sunbeam
mkdir data/sunbeam/ml
chmod 777 data/sunbeam/ml

sudo apt-get update
sudo apt-get install -y docker-ce
sudo usermod -aG docker $USER

