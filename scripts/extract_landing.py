import zipfile
import os
import shutil

zip_path = r'C:\Users\user\Downloads\Глава — семейные истории.zip'
landing_dir = r'C:\Users\user\Dropbox\Public\Cursor\GLAVA\landing'
extract_tmp = r'C:\Users\user\Downloads\glava_extracted_tmp'

# Extract to temp
if os.path.exists(extract_tmp):
    shutil.rmtree(extract_tmp)
os.makedirs(extract_tmp)

with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(extract_tmp)

# Show what was extracted
for root, dirs, files in os.walk(extract_tmp):
    for f in files:
        full = os.path.join(root, f)
        print(full)
