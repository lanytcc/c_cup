
# Install Scoop
if (!(Test-Path $env:USERPROFILE\scoop)) {
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser # Optional: Needed to run a remote script the first time
    irm get.scoop.sh | iex
}

# Install Scoop packages
if (!(Test-Path $env:USERPROFILE\scoop\apps\miniconda3)) {
    scoop bucket add extras
    scoop install miniconda3
    conda init powershell
}

# Install Conda packages
if (!(Test-Path $env:USERPROFILE\scoop\apps\miniconda3\current\envs\pi)) {
    conda create -n pi python=3.9
}

# Activate Conda environment
conda activate pi

# Install Python packages
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
