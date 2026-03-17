# -*- coding: utf-8 -*-
"""Копирует фавиконки в landing/assets/ с правильными именами."""
import shutil, os

assets_dir = r'c:\Users\user\Dropbox\Public\Cursor\GLAVA\landing\assets'
src_dir = r'C:\Users\user\.cursor\projects\c-Users-user-Dropbox-Public-Cursor-GLAVA\assets'

files = [
    ('c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_f1730dfeb8c064a9df2eec55b412d2a7_images_favicon-16-bc4882d2-7084-44b2-a023-c183b9707177.png',  'favicon-16.png'),
    ('c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_f1730dfeb8c064a9df2eec55b412d2a7_images_favicon-32-f84f79fa-2ebd-4d6b-a2e7-125ebf6cef4b.png',  'favicon-32.png'),
    ('c__Users_user_AppData_Roaming_Cursor_User_workspaceStorage_f1730dfeb8c064a9df2eec55b412d2a7_images_favicon-df699f9f-e62c-4066-ab5b-6ff78ff59785.png',     'apple-touch-icon.png'),
]

for src_name, dst_name in files:
    src = os.path.join(src_dir, src_name)
    dst = os.path.join(assets_dir, dst_name)
    shutil.copy2(src, dst)
    print(f'Copied: {dst_name}')

# Also create favicon.ico from 32px version using PIL if available, else just copy png as ico
try:
    from PIL import Image
    img = Image.open(os.path.join(assets_dir, 'favicon-32.png'))
    img.save(os.path.join(assets_dir, 'favicon.ico'), format='ICO', sizes=[(16,16),(32,32),(48,48)])
    print('Created: favicon.ico (ICO format, 16/32/48px)')
except ImportError:
    shutil.copy2(os.path.join(assets_dir, 'favicon-32.png'), os.path.join(assets_dir, 'favicon.ico'))
    print('Copied: favicon.ico (PNG fallback, Pillow not available)')
