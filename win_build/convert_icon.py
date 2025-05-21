from PIL import Image
import os

project_root = os.path.join(os.path.dirname(__file__), '..')
png = os.path.join(project_root, 'original_icon.png')
ico = os.path.join(project_root, 'original_icon.ico')

img = Image.open(png)
img.save(ico, sizes=[(256,256), (128,128), (64,64), (32,32), (16,16)])
