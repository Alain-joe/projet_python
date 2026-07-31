import os
import traceback
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


def get_brevo_client():
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
    return sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )


def send_mfa_email(email, code):
    api_instance = get_brevo_client()

    sender = {
        "name": "Cimetière Connect",
        "email": os.getenv("BREVO_SENDER_EMAIL")
    }

    recipient = [{"email": email}]

    email_data = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=recipient,
        subject="Votre code MFA Cimetière Connect",
        text_content=(
            f"Votre code de connexion est :\n\n"
            f"{code}\n\n"
            f"Ce code expire dans 10 minutes."
        ),
    )

    try:
        api_instance.send_transac_email(email_data)
        print("EMAIL MFA ENVOYE PAR BREVO")
        return True
    except ApiException as e:
        print(f"ERREUR BREVO MFA (ApiException) : {e}")
        return False
    except Exception as e:
        print(f"ERREUR BREVO MFA (AUTRE EXCEPTION) : {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def send_credentials_email_brevo(email, prenom, username, password):
    api_instance = get_brevo_client()

    sender = {
        "name": "Cimetière Connect",
        "email": os.getenv("BREVO_SENDER_EMAIL")
    }

    recipient = [{"email": email}]

    email_data = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=recipient,
        subject="Vos identifiants Cimetière Connect",
        text_content=(
            f"Bonjour {prenom},\n\n"
            f"Votre compte Cimetière Connect a été créé.\n\n"
            f"Nom utilisateur : {username}\n"
            f"Mot de passe temporaire : {password}\n\n"
            f"Veuillez modifier votre mot de passe après votre première connexion.\n\n"
            f"Cordialement,\nL'équipe Cimetière Connect"
        ),
    )

    try:
        api_instance.send_transac_email(email_data)
        print("EMAIL IDENTIFIANTS ENVOYE PAR BREVO")
        return True
    except ApiException as e:
        print(f"ERREUR BREVO IDENTIFIANTS (ApiException) : {e}")
        return False
    except Exception as e:
        print(f"ERREUR BREVO IDENTIFIANTS (AUTRE EXCEPTION) : {type(e).__name__}: {e}")
        traceback.print_exc()
        return False