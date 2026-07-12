import httpx
import logging
from app.config import AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID

logger = logging.getLogger(__name__)


async def get_entra_users():
    """
    Fetch all users from Azure Entra ID who have been assigned the app.
    Returns: list of {'id': oid, 'displayName': name, 'mail': email}
    """
    if not AZURE_CLIENT_ID or not AZURE_CLIENT_SECRET:
        logger.warning("Missing AZURE_CLIENT_ID or AZURE_CLIENT_SECRET")
        return []

    try:
        # Get access token
        token_url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
        token_data = {
            "client_id": AZURE_CLIENT_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(token_url, data=token_data)
            if token_resp.status_code != 200:
                logger.error(f"Token request failed: {token_resp.status_code} - {token_resp.text}")
                return []

            access_token = token_resp.json().get("access_token")
            if not access_token:
                logger.error("No access token in response")
                return []

            logger.info("✓ Got access token")

            # Fetch app users
            headers = {"Authorization": f"Bearer {access_token}"}

            # Get app object ID first
            app_url = f"https://graph.microsoft.com/v1.0/applications?$filter=appId eq '{AZURE_CLIENT_ID}'"
            app_resp = await client.get(app_url, headers=headers)
            if app_resp.status_code != 200:
                logger.error(f"App lookup failed: {app_resp.status_code} - {app_resp.text}")
                return []

            apps = app_resp.json().get("value", [])
            if not apps:
                logger.warning(f"No app found with client_id: {AZURE_CLIENT_ID}")
                return []

            app_id = apps[0]["id"]
            logger.info(f"✓ Found app with ID: {app_id}")

            # Get app role assignments
            assignments_url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{app_id}/appRoleAssignedTo"
            assignments_resp = await client.get(assignments_url, headers=headers)
            if assignments_resp.status_code != 200:
                logger.error(f"Assignments lookup failed: {assignments_resp.status_code} - {assignments_resp.text}")
                return []

            assignments = assignments_resp.json().get("value", [])
            logger.info(f"✓ Found {len(assignments)} app role assignments")

        users = []
        for assignment in assignments:
            principal_id = assignment.get("principalId")
            principal_type = assignment.get("principalType")

            if principal_type != "User" or not principal_id:
                continue

            # Get user details
            user_url = f"https://graph.microsoft.com/v1.0/directoryObjects/{principal_id}"
            user_resp = await client.get(user_url, headers=headers)
            if user_resp.status_code == 200:
                user_data = user_resp.json()
                users.append({
                    "id": user_data.get("id"),  # object ID
                    "displayName": user_data.get("displayName", ""),
                    "mail": user_data.get("mail", ""),
                })
            else:
                logger.warning(f"Failed to get user details for {principal_id}: {user_resp.status_code}")

        logger.info(f"✓ Returning {len(users)} Entra ID users")
        return users

    except Exception as e:
        logger.error(f"Error fetching Entra ID users: {e}", exc_info=True)
        return []
