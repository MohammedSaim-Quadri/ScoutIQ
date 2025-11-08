import firebase_admin
from firebase_admin import credentials, auth

# --- Configuration ---
ADMIN_EMAIL_TO_SET = "interviewscoutiq@gmail.com"
SERVICE_KEY_PATH = "firebase-service-key.json"
# ---------------------

try:
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate(SERVICE_KEY_PATH)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized.")

    # Get the user by email
    print(f"Fetching user for email: {ADMIN_EMAIL_TO_SET}...")
    user = auth.get_user_by_email(ADMIN_EMAIL_TO_SET)
    print(f"Successfully found user: {user.uid}")

    # Set the custom claim
    # This embeds {'admin': True} into the user's token data
    auth.set_custom_user_claims(user.uid, {'admin': True})
    
    print("\n✅ SUCCESS!")
    print(f"Custom claim {'admin': True} has been set for {ADMIN_EMAIL_TO_SET}.")
    print("The user must log out and log back in for this change to take effect.")

except FileNotFoundError:
    print(f"❌ ERROR: Could not find the service key file.")
    print(f"Please make sure '{SERVICE_KEY_PATH}' is in the same directory as this script.")
except Exception as e:
    print(f"❌ An error occurred: {e}")