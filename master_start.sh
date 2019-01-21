sudo mkdir /data
sudo mkdir /data/db
sudo chown $USER:$USER /data/db

sudo mkdir /data/sunbeam
sudo chown $USER:$USER /data/sunbeam
sudo mkdir /data/sunbeam/ml
sudo chmod 777 /data/sunbeam/ml

# for Ubuntu 18.04
sudo apt-get update
sudo apt install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
sudo apt update
apt-cache policy docker-ce
sudo apt install docker-ce
sudo systemctl status docker
sudo usermod -aG docker $USER
