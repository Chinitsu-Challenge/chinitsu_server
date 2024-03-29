import requests
import os



# Folder where you want to save the images
save_folder = 'assets/'

# Ensure the save folder exists, create if it doesn't
if not os.path.exists(save_folder):
    os.makedirs(save_folder)

# Function to download and save an image
def download_and_save_image(url, save_path):
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1000: # file exists
        return
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the download was successful
        
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print(f"Image saved: {save_path}")
    except requests.RequestException as e:
        print(f"Failed to download {url}. Reason: {e}")

# Loop through the URLs and their corresponding new names
url_t = "https://cdn.tenhou.net/5/img/vieww{}{}{}.png"

# 1-9s
for i in range(1, 9+1):
    for j, sz in enumerate(['63', '85', '63', '85']):
        new_name = f"{i}s_{j}.png"
        
        url = url_t.format(f"{j}3", f"{i}0", sz)
        save_path = os.path.join(save_folder, new_name)
        download_and_save_image(url, save_path)

# 0s

for j, sz in enumerate(['63', '85', '63', '85']):
    new_name = f"0s_{j}.png"
    
    url = url_t.format(f"{j}5", "30", sz)
    save_path = os.path.join(save_folder, new_name)
    download_and_save_image(url, save_path)