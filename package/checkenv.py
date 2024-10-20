import os

# Load the TG_TOKEN environment variable
tg_token = os.getenv('TG_TOKEN')

# Check if the token is found
if tg_token:
    print(f"TG_TOKEN: {tg_token}")
else:
    print("TG_TOKEN environment variable is not set.")