#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv('/opt/glava/.env')
print(os.environ.get('ASSEMBLYAI_API_KEY', ''))
